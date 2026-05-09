"""
AppForge Pipeline - Natural Language → Working App Config Compiler
Multi-stage generation: Intent → Architecture → Schema → Refinement → Validation
"""

# ── IMPORTS ───────────────────────────────────────────────────────────────────

import json
import os
import time
import re
import hashlib
import urllib.request
import urllib.error
from typing import Any, Tuple, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global Config
# Key pooling for rate limit mitigation
API_KEYS = []
i = 1
while True:
    key = os.getenv(f"GROQ_API_KEY_{i}")
    if not key:
        # Check if just GROQ_API_KEY exists (legacy support)
        if i == 1 and os.getenv("GROQ_API_KEY"):
            API_KEYS.append(os.getenv("GROQ_API_KEY"))
        break
    API_KEYS.append(key)
    i += 1

# Filter out empty keys
API_KEYS = [k for k in API_KEYS if k.strip()]
CURRENT_KEY_INDEX = 0

if API_KEYS:
    print(f"[CONFIG] {len(API_KEYS)} API keys loaded for pooling.")
else:
    print("[CONFIG] WARNING: No GROQ_API_KEYS found in environment.")

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

from runtime_simulator import simulate_execution

# ── STAGE SYSTEM PROMPTS ─────────────────────────────────────────────────────

INTENT_SYSTEM = """You are an intent extraction engine. Your job is to parse user app descriptions into a structured intermediate representation.

Output ONLY valid JSON with this exact schema:
{
  "app_name": string,
  "app_type": string,            // e.g. "CRM", "E-commerce", "Dashboard", "SaaS"
  "core_entities": [             // main data objects
    { "name": string, "description": string }
  ],
  "features": [string],          // list of distinct features
  "roles": [string],             // user roles
  "auth_required": boolean,
  "payment_required": boolean,
  "premium_features": [string],  // features only for paid users
  "admin_features": [string],    // features only for admins
  "ambiguities": [string],       // things that are unclear
  "assumptions": [string]        // reasonable assumptions made
}

Be precise. Do not invent features not implied. Flag anything unclear in ambiguities."""

ARCHITECTURE_SYSTEM = """You are a system architect. Given an intent extraction, design the full application architecture.

Output ONLY valid JSON with this exact schema:
{
  "pages": [
    {
      "name": string,
      "route": string,
      "auth_required": boolean,
      "roles_allowed": [string],
      "description": string,
      "components": [string]
    }
  ],
  "api_groups": [
    {
      "resource": string,
      "base_path": string,
      "operations": [string]     // e.g. ["list", "get", "create", "update", "delete"]
    }
  ],
  "data_entities": [
    {
      "name": string,
      "fields": [
        { "name": string, "type": string, "required": boolean, "unique": boolean }
      ],
      "relations": [
        { "type": string, "target": string, "field": string }
      ]
    }
  ],
  "auth_model": {
    "strategy": string,           // "jwt", "session", "oauth"
    "roles": [string],
    "permissions": {
      "<role>": [string]          // list of allowed operations
    }
  },
  "business_rules": [string]      // e.g. "premium users can access analytics"
}"""

SCHEMA_SYSTEM = """You are a schema generation engine. Given an architecture, produce full UI, API, DB, and Auth schemas.

Output ONLY valid JSON with this exact schema:
{
  "ui_schema": {
    "pages": [
      {
        "id": string,
        "name": string,
        "route": string,
        "layout": string,       // "sidebar", "centered", "dashboard", "split"
        "auth_required": boolean,
        "roles_allowed": [string],
        "components": [
          {
            "id": string,
            "type": string,     // "table", "form", "card", "chart", "nav", "modal", "button"
            "label": string,
            "props": {},
            "data_source": string,   // which API endpoint feeds this
            "actions": [string]      // e.g. ["create", "edit", "delete"]
          }
        ]
      }
    ],
    "global_components": ["navbar", "sidebar", "footer"]
  },
  "api_schema": {
    "base_url": "/api/v1",
    "auth_header": "Authorization: Bearer <token>",
    "endpoints": [
      {
        "id": string,
        "method": string,
        "path": string,
        "auth_required": boolean,
        "roles_allowed": [string],
        "request_body": {},
        "response_body": {},
        "query_params": [string],
        "description": string
      }
    ]
  },
  "db_schema": {
    "tables": [
      {
        "name": string,
        "columns": [
          {
            "name": string,
            "type": string,     // "uuid", "varchar", "text", "int", "bool", "timestamp", "decimal", "jsonb"
            "primary_key": boolean,
            "nullable": boolean,
            "unique": boolean,
            "default": string,
            "foreign_key": { "table": string, "column": string } | null
          }
        ],
        "indexes": [string]
      }
    ]
  },
  "auth_schema": {
    "strategy": string,
    "token_expiry": string,
    "refresh_token": boolean,
    "roles": [
      {
        "name": string,
        "permissions": [string],
        "is_premium": boolean
      }
    ],
    "middleware_rules": [
      { "path_pattern": string, "roles_required": [string] }
    ]
  }
}"""

REFINEMENT_SYSTEM = """You are a schema consistency enforcer. Your job is to find and fix ALL inconsistencies in the generated schema.

Check for:
1. Every UI component's data_source must match an existing API endpoint. 
   IMPORTANT: Remember to prepend the api_schema.base_url to the endpoint path when checking data_source!
2. Every API endpoint's request/response fields must exist in DB tables.
3. Every role referenced in UI/API must exist in auth_schema.roles.
4. Every DB foreign key must reference an existing table and column.
5. Premium/admin-gated UI components must have matching auth middleware rules.

Output ONLY valid JSON with this exact schema:
{
  "issues_found": [string],
  "fixes_applied": [string],
  "schema": { /* the complete corrected schema, same structure as input */ }
}

If no issues found, still output with empty arrays and the original schema."""

VALIDATION_SYSTEM = """You are a schema validator. Given a complete app schema, validate it is production-ready.

Output ONLY valid JSON:
{
  "valid": boolean,
  "score": number,              // 0-100 quality score
  "errors": [                   // blocking issues
    { "layer": string, "field": string, "message": string }
  ],
  "warnings": [                 // non-blocking issues
    { "layer": string, "field": string, "message": string }
  ],
  "repairables": [              // issues that can be auto-repaired
    { "layer": string, "field": string, "fix": string }
  ]
}"""

# ── PIPELINE STAGES ───────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_message: str, stage_name: str, model: str = "llama-3.3-70b-versatile") -> dict:
    """Call LLM via urllib with key rotation and retry logic."""
    global CURRENT_KEY_INDEX
    if not API_KEYS:
        raise ValueError("No GROQ_API_KEYS set in environment variables.")

    max_retries = 5
    for attempt in range(max_retries):
        # Rotate key on every attempt
        api_key = API_KEYS[CURRENT_KEY_INDEX % len(API_KEYS)]
        CURRENT_KEY_INDEX += 1
        
        raw = ""
        try:
            body = json.dumps({
                "model": model,
                "max_tokens": 4096,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]
            }).encode("utf-8")

            req = urllib.request.Request(
                GROQ_BASE_URL,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "AppForge/1.0"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                raw = res_data["choices"][0]["message"]["content"].strip()

            # 1. Extract JSON from markdown if present
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw, re.IGNORECASE)
            if json_match:
                raw = json_match.group(1).strip()

            # 2. Find the actual start and end of the JSON object/array
            # This handles cases where the LLM appends text before/after the JSON
            start_idx = -1
            end_idx = -1
            
            # Find first { or [
            for i, char in enumerate(raw):
                if char in '{[':
                    start_idx = i
                    break
            
            # Find last } or ]
            for i, char in enumerate(reversed(raw)):
                if char in '}]':
                    end_idx = len(raw) - i
                    break
            
            if start_idx != -1 and end_idx != -1:
                raw = raw[start_idx:end_idx]

            if not raw:
                raise ValueError("No JSON found in response")

            return json.loads(raw)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                # Rate limit hit - wait longer (Groq free tier is tight)
                wait_time = 5 * (attempt + 1)
                print(f"[{stage_name}] Rate limit (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue

            if attempt == max_retries - 1:
                print(f"[{stage_name}] API Error ({e.code}):\n{error_body}\n---END---")
                raise ValueError(f"[{stage_name}] API Error {e.code}: {error_body}")
            time.sleep(1)
        except (json.JSONDecodeError, Exception) as e:
            if attempt == max_retries - 1:
                print(f"[{stage_name}] Final attempt failed. Raw output:\n{raw}\n---END---")
                raise ValueError(
                    f"[{stage_name}] Failed to parse JSON after {max_retries} attempts: {e}")
            time.sleep(1)
    return {}


def stage_intent(user_prompt: str) -> dict:
    """Stage 1: Extract intent from natural language."""
    return call_llm(
        INTENT_SYSTEM,
        f"Extract intent from this app description:\n\n{user_prompt}",
        "IntentExtraction",
        model="llama-3.1-8b-instant"
    )


def stage_architecture(intent: dict) -> dict:
    """Stage 2: Design system architecture from intent."""
    return call_llm(
        ARCHITECTURE_SYSTEM,
        f"Design the application architecture for this intent:\n\n{json.dumps(intent, indent=2)}",
        "ArchitectureDesign"
    )


def stage_schema(architecture: dict, intent: dict) -> dict:
    """Stage 3: Generate full schemas from architecture."""
    return call_llm(
        SCHEMA_SYSTEM,
        f"Generate complete schemas for:\n\nINTENT:\n{json.dumps(intent, indent=2)}\n\nARCHITECTURE:\n{json.dumps(architecture, indent=2)}",
        "SchemaGeneration"
    )


def stage_refinement(schema: dict) -> Tuple[dict, List[str], List[str]]:
    """Stage 4: Find and fix cross-layer inconsistencies."""
    result = call_llm(
        REFINEMENT_SYSTEM,
        f"Audit and repair this schema for consistency:\n\n{json.dumps(schema, indent=2)}",
        "Refinement"
    )
    return result.get("schema", schema), result.get("issues_found", []), result.get("fixes_applied", [])


def stage_validation(schema: dict) -> dict:
    """Stage 5: Validate the complete schema."""
    return call_llm(
        VALIDATION_SYSTEM,
        f"Validate this application schema:\n\n{json.dumps(schema, indent=2)}",
        "Validation",
        model="llama-3.1-8b-instant"
    )


def auto_repair(schema: dict, validation: dict) -> Tuple[dict, List[str]]:
    """Stage 5.5: Automatically repair validation issues."""
    repair_prompt = f"Fix these issues in the schema:\nIssues: {json.dumps(validation.get('repairables', []), indent=2)}\nSchema: {json.dumps(schema, indent=2)}"
    result = call_llm(REFINEMENT_SYSTEM, repair_prompt, "AutoRepair", model="llama-3.1-8b-instant")
    return result.get("schema", schema), result.get("fixes_applied", [])


# ── MAIN COMPILER ─────────────────────────────────────────────────────────────

def compile_app(user_prompt: str) -> dict:
    """
    Full compilation pipeline: NL → Intent → Architecture → Schema → Refinement → Validation
    Returns complete result with metrics.
    """
    start_time = time.time()
    metrics = {
        "prompt_hash": hashlib.md5(user_prompt.encode()).hexdigest()[:8],
        "stages": {},
        "retries": 0,
        "total_latency_ms": 0
    }

    result = {
        "prompt": user_prompt,
        "success": False,
        "metrics": metrics,
        "pipeline_stages": {}
    }

    try:
        # ── Stage 1: Intent Extraction
        t = time.time()
        intent = stage_intent(user_prompt)
        metrics["stages"]["intent"] = round((time.time() - t) * 1000)
        result["pipeline_stages"]["intent"] = intent

        # Handle vague prompts
        if intent.get("ambiguities") and len(intent["ambiguities"]) > 3:
            result["clarifications_needed"] = intent["ambiguities"]
            result["assumptions_made"] = intent.get("assumptions", [])

        # ── Stage 2: Architecture Design
        t = time.time()
        architecture = stage_architecture(intent)
        metrics["stages"]["architecture"] = round((time.time() - t) * 1000)
        result["pipeline_stages"]["architecture"] = architecture

        # ── Stage 3: Schema Generation
        t = time.time()
        raw_schema = stage_schema(architecture, intent)
        metrics["stages"]["schema_generation"] = round(
            (time.time() - t) * 1000)
        result["pipeline_stages"]["raw_schema"] = raw_schema

        # ── Stage 4: Refinement
        t = time.time()
        refined_schema, issues, fixes = stage_refinement(raw_schema)
        metrics["stages"]["refinement"] = round((time.time() - t) * 1000)
        result["pipeline_stages"]["refinement"] = {
            "issues_found": issues, "fixes_applied": fixes}

        # ── Stage 5: Validation
        t = time.time()
        validation = stage_validation(refined_schema)
        metrics["stages"]["validation"] = round((time.time() - t) * 1000)
        result["pipeline_stages"]["validation"] = validation

        # ── Auto-Repair if needed
        if not validation.get("valid") and validation.get("repairables"):
            repaired_schema, repairs = auto_repair(refined_schema, validation)
            if repairs:
                metrics["retries"] += 1
                # Re-validate after repair
                t = time.time()
                validation = stage_validation(repaired_schema)
                metrics["stages"]["re_validation"] = round(
                    (time.time() - t) * 1000)
                result["pipeline_stages"]["auto_repairs"] = repairs
                refined_schema = repaired_schema

        # ── Stage 6: Runtime Simulation & Code Gen
        t = time.time()
        runtime_result = simulate_execution(refined_schema)
        metrics["stages"]["runtime_simulation"] = round((time.time() - t) * 1000)
        result["runtime"] = runtime_result

        result["schema"] = refined_schema
        result["validation"] = validation
        result["success"] = (validation.get("valid", False) or validation.get("score", 0) >= 70) and runtime_result.get("executable", False)
        result["quality_score"] = validation.get("score", 0)

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

    metrics["total_latency_ms"] = round((time.time() - start_time) * 1000)
    result["metrics"] = metrics
    return result

def stage_refinement(schema: dict) -> Tuple[dict, List[str], List[str]]:
    """Stage 4: Find and fix cross-layer inconsistencies."""
    result = call_llm(
        REFINEMENT_SYSTEM,
        f"Audit and repair this schema for consistency:\n\n{json.dumps(schema, indent=2)}",
        "Refinement",
        model="llama-3.3-70b-versatile"
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

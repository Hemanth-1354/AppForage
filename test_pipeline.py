#!/usr/bin/env python3
"""
Quick smoke test — verifies the pipeline runs end-to-end before submission.
Run from: python test_pipeline.py
"""

import json
import sys
import os

project_root = os.path.abspath(os.path.dirname(__file__))
backend_path = os.path.join(project_root, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from pipeline import compile_app
from runtime_simulator import simulate_execution

TEST_PROMPT = (
    "Build a CRM with login, contacts management, dashboard, "
    "role-based access (admin, sales rep, viewer), and a premium plan with Stripe payments. "
    "Admins can see analytics and manage users. Sales reps can add/edit contacts."
)

def run_test():
    print("=" * 60)
    print("AppForge Pipeline Smoke Test")
    print("=" * 60)
    print(f"\nPrompt: {TEST_PROMPT[:80]}...\n")

    print("Running compilation pipeline...")
    result = compile_app(TEST_PROMPT)

    print(f"\n[OK] Pipeline complete!")
    print(f"   Success: {result.get('success')}")
    print(f"   Quality Score: {result.get('quality_score')}/100")
    print(f"   Total Latency: {result.get('metrics', {}).get('total_latency_ms')}ms")
    print(f"   Retries: {result.get('metrics', {}).get('retries')}")

    stages = result.get("metrics", {}).get("stages", {})
    print(f"\nStage Latencies:")
    for stage, ms in stages.items():
        print(f"   {stage}: {ms}ms")

    schema = result.get("schema")
    if schema:
        print(f"\nSchema layers generated:")
        for layer in ["ui_schema", "api_schema", "db_schema", "auth_schema"]:
            present = "[PASS]" if layer in schema else "[FAIL]"
            print(f"   {present} {layer}")

        print(f"\nRunning execution simulation...")
        sim = simulate_execution(schema)
        print(f"   Executable: {sim.get('executable')}")
        print(f"   Executability Score: {sim.get('executability_score')}/100")
        print(f"\nSimulation steps:")
        for step in sim.get("simulation_steps", []):
            status = "[PASS]" if step.get("success") else "[FAIL]"
            print(f"   {status} {step['step']}: {len(step.get('errors', []))} errors")

        artifacts = sim.get("code_artifacts", {})
        if artifacts:
            print(f"\nGenerated code artifacts: {', '.join(artifacts.keys())}")

    val = result.get("validation", {})
    if val:
        print(f"\nValidation:")
        print(f"   Valid: {val.get('valid')}")
        print(f"   Errors: {len(val.get('errors', []))}")
        print(f"   Warnings: {len(val.get('warnings', []))}")

    refinement = result.get("pipeline_stages", {}).get("refinement", {})
    if refinement:
        print(f"\nRefinement:")
        print(f"   Issues found: {len(refinement.get('issues_found', []))}")
        print(f"   Fixes applied: {len(refinement.get('fixes_applied', []))}")

    print("\n" + "=" * 60)
    print("Test complete. Full output saved to test_output.json")
    with open("test_output.json", "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    run_test()

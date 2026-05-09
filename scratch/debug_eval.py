import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from evaluator import run_evaluation
import json

try:
    print("Starting parallel evaluation test...")
    results = run_evaluation(subset="real", max_workers=2)
    print("Success!")
    print(f"Stats: {results['successful']} successful, {results['failed']} failed")
except Exception as e:
    print(f"FAILED with error: {e}")
    import traceback
    traceback.print_exc()

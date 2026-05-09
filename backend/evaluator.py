"""
AppForge Evaluation Framework
10 real product prompts + 10 edge cases (vague, conflicting, incomplete)
Tracks: success rate, retries, failure types, latency
"""

import json
import time
from typing import Literal
from pipeline import compile_app

EVAL_PROMPTS = {
    "real": [
        {
            "id": "R01",
            "name": "CRM with Payments",
            "prompt": "Build a CRM with login, contacts management, dashboard, role-based access (admin, sales rep, viewer), and a premium plan with Stripe payments. Admins can see analytics and manage users. Sales reps can add/edit contacts. Viewers are read-only."
        },
        {
            "id": "R02",
            "name": "Project Management SaaS",
            "prompt": "Build a project management tool like Jira. Users can create projects, add tasks with status (todo, in-progress, done), assign tasks to team members, set due dates, add comments. Admins manage the workspace. Free plan: 3 projects. Pro plan: unlimited projects + time tracking."
        },
        {
            "id": "R03",
            "name": "E-commerce Platform",
            "prompt": "Build an e-commerce store with product catalog, shopping cart, checkout with Stripe, order history, inventory management for admins, and product reviews. Customers can track orders. Admins manage products and orders."
        },
        {
            "id": "R04",
            "name": "HR Management System",
            "prompt": "Build an HRMS with employee directory, leave management, payroll, performance reviews, and onboarding workflows. HR admins manage everything. Managers can approve leaves and review their team. Employees can view their own data and apply for leave."
        },
        {
            "id": "R05",
            "name": "Learning Management System",
            "prompt": "Build an LMS where instructors create courses with video lessons and quizzes. Students enroll, track progress, and get certificates. Admins manage users and content. Premium students get access to live sessions. Free users get limited courses."
        },
        {
            "id": "R06",
            "name": "Booking/Appointment System",
            "prompt": "Build an appointment scheduling app for clinics. Patients book appointments with doctors. Doctors manage their schedules and patient records. Receptionists can book/cancel on behalf of patients. Admins see all analytics. Email reminders for upcoming appointments."
        },
        {
            "id": "R07",
            "name": "Social Media Dashboard",
            "prompt": "Build a social media analytics dashboard that connects to Twitter and Instagram APIs. Users can schedule posts, track engagement metrics, view follower growth charts. Agency plan allows managing multiple client accounts. Generate weekly PDF reports."
        },
        {
            "id": "R08",
            "name": "Inventory Management",
            "prompt": "Build a warehouse inventory system with product tracking, stock alerts when below threshold, supplier management, purchase orders, and barcode scanning support. Managers approve purchase orders. Workers update stock. Reports for low stock and order history."
        },
        {
            "id": "R09",
            "name": "Real Estate Platform",
            "prompt": "Build a real estate listing platform. Agents can list properties with photos, price, location. Buyers can search, filter, save favorites, and contact agents. Premium agents get featured listings and analytics. Admins verify agents and moderate listings."
        },
        {
            "id": "R10",
            "name": "Support Ticket System",
            "prompt": "Build a customer support system with ticket creation, assignment to agents, priority levels, SLA tracking, canned responses, and customer satisfaction ratings. Team leads see agent performance metrics. Customers track their ticket status via email."
        }
    ],
    "edge": [
        {
            "id": "E01",
            "name": "Ultra Vague",
            "prompt": "Build an app for my business.",
            "expected_behavior": "should_ask_clarification"
        },
        {
            "id": "E02",
            "name": "Conflicting Requirements",
            "prompt": "Build a social network where everything is private and no data is stored, but users can share posts publicly and we need to show their post history.",
            "expected_behavior": "should_flag_conflict"
        },
        {
            "id": "E03",
            "name": "Technically Impossible",
            "prompt": "Build a real-time app with zero latency and unlimited storage for free.",
            "expected_behavior": "should_make_assumptions"
        },
        {
            "id": "E04",
            "name": "Missing Auth Context",
            "prompt": "Build a dashboard with admin panel and user management.",
            "expected_behavior": "should_infer_auth"
        },
        {
            "id": "E05",
            "name": "Contradictory Roles",
            "prompt": "All users are admins. Admins can do everything. Users cannot access admin features. Everyone is equal.",
            "expected_behavior": "should_flag_conflict"
        },
        {
            "id": "E06",
            "name": "Extremely Long / Complex",
            "prompt": "Build a full enterprise ERP with HR, payroll, accounting, CRM, inventory, procurement, manufacturing, logistics, BI reporting, document management, project management, IT ticketing, compliance management, multi-currency support, multi-language, SSO, audit logs, API gateway, mobile apps for iOS and Android, and AI-powered insights.",
            "expected_behavior": "should_handle_gracefully"
        },
        {
            "id": "E07",
            "name": "No Features Specified",
            "prompt": "Build a SaaS platform.",
            "expected_behavior": "should_ask_clarification"
        },
        {
            "id": "E08",
            "name": "Wrong Domain Terms",
            "prompt": "Build an app where zorbits can flagulate the mortex and admins can grumify the plenox dashboard.",
            "expected_behavior": "should_handle_gracefully"
        },
        {
            "id": "E09",
            "name": "Incomplete Auth",
            "prompt": "Build an app where only logged-in users can use it. No signup, just login.",
            "expected_behavior": "should_infer_auth"
        },
        {
            "id": "E10",
            "name": "Payment Without Product",
            "prompt": "Build a payment system with Stripe. Users pay monthly. There's a free tier.",
            "expected_behavior": "should_make_assumptions"
        }
    ]
}


from concurrent.futures import ThreadPoolExecutor
import threading

def run_evaluation(subset: Literal["real", "edge", "all"] = "all", max_workers: int = 4) -> dict:
    """Run evaluation on specified prompt subset in parallel."""
    
    prompts_to_run = []
    if subset == "all":
        prompts_to_run = EVAL_PROMPTS["real"] + EVAL_PROMPTS["edge"]
    else:
        prompts_to_run = EVAL_PROMPTS[subset]
    
    summary = {
        "total": len(prompts_to_run),
        "successful": 0,
        "failed": 0,
        "total_retries": 0,
        "avg_latency_ms": 0,
        "avg_quality_score": 0,
        "failure_types": {},
        "results": []
    }
    
    lock = threading.Lock()
    total_latency = 0
    total_quality = 0
    
    def process_prompt(p):
        nonlocal total_latency, total_quality
        print(f"[EVAL] Starting {p['id']}: {p['name']}...")
        start = time.time()
        try:
            result = compile_app(p["prompt"])
            latency = round((time.time() - start) * 1000)
            
            eval_result = {
                "id": p["id"],
                "name": p["name"],
                "prompt_preview": p["prompt"][:100] + "..." if len(p["prompt"]) > 100 else p["prompt"],
                "success": result.get("success", False),
                "quality_score": result.get("quality_score", 0),
                "latency_ms": latency,
                "retries": result.get("metrics", {}).get("retries", 0),
                "metrics": result.get("metrics", {}),
                "clarifications_needed": "clarifications_needed" in result,
                "assumptions_made": result.get("pipeline_stages", {}).get("intent", {}).get("assumptions", []),
                "issues_found": result.get("pipeline_stages", {}).get("refinement", {}).get("issues_found", []),
                "errors": result.get("validation", {}).get("errors", []),
                "warnings": result.get("validation", {}).get("warnings", [])
            }
            
            with lock:
                if result.get("success"):
                    summary["successful"] += 1
                else:
                    summary["failed"] += 1
                    err_str = str(result.get("error", "")) + str(result.get("validation", {}).get("errors", []))
                    ftype = "validation_failure"
                    if "json" in err_str.lower(): ftype = "json_parse_error"
                    elif "timeout" in err_str.lower(): ftype = "timeout"
                    elif result.get("quality_score", 0) < 50: ftype = "low_quality"
                    summary["failure_types"][ftype] = summary["failure_types"].get(ftype, 0) + 1
                
                summary["total_retries"] += eval_result["retries"]
                total_latency += latency
                total_quality += eval_result["quality_score"]
                summary["results"].append(eval_result)
                print(f"[EVAL] Finished {p['id']} - Success: {eval_result['success']} - {latency}ms")
                
        except Exception as e:
            with lock:
                summary["results"].append({
                    "id": p["id"], "name": p["name"], "success": False, "error": str(e),
                    "latency_ms": round((time.time() - start) * 1000)
                })
                summary["failed"] += 1
                summary["failure_types"]["exception"] = summary["failure_types"].get("exception", 0) + 1

    print(f"Running evaluation suite with {max_workers} parallel workers...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_prompt, prompts_to_run)
    
    # Sort results by ID for consistency
    summary["results"].sort(key=lambda x: x["id"])
    
    summary["avg_latency_ms"] = round(total_latency / max(len(summary["results"]), 1))
    summary["avg_quality_score"] = round(total_quality / max(len(summary["results"]), 1))
    summary["success_rate_pct"] = round(summary["successful"] / max(summary["total"], 1) * 100, 1)
    
    return summary


if __name__ == "__main__":
    print("Running full evaluation suite...")
    results = run_evaluation("real")
    print(json.dumps(results, indent=2))

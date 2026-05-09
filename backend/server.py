"""
AppForge API Server - FastAPI backend exposing the compilation pipeline
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
from pathlib import Path

from pipeline import compile_app
from evaluator import run_evaluation, EVAL_PROMPTS

app = FastAPI(title="AppForge", version="1.0.0", description="NL → App Config Compiler")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompileRequest(BaseModel):
    prompt: str


class EvalRequest(BaseModel):
    subset: str = "all"  # "real", "edge", "all"


@app.post("/api/compile")
def compile_endpoint(req: CompileRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(req.prompt) > 2000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 2000 chars)")
    
    result = compile_app(req.prompt)
    return result


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/eval-prompts")
async def get_eval_prompts():
    return {"prompts": EVAL_PROMPTS}


@app.post("/api/evaluate")
def evaluate(req: EvalRequest):
    results = run_evaluation(subset=req.subset)
    return results


# Mount frontend static files if built
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

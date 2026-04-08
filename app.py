"""FastAPI server exposing the SoftwareLifecycleEnv as an HTTP API.

Endpoints
---------
GET  /       → health check / landing
POST /reset  → reset environment (optional task_id)
POST /step   → execute one action
GET  /state  → current environment state snapshot
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from env.environment import SoftwareLifecycleEnv

# ── app + global env ─────────────────────────────────────────────────────

app = FastAPI(
    title="SoftwareLifecycleEnv",
    description="OpenEnv-compatible benchmark for software engineering tasks.",
    version="1.0.0",
)

env = SoftwareLifecycleEnv()


# ── request / response schemas ───────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action_type: str
    target_file: Optional[str] = None
    patch_content: Optional[str] = None


class StepResponse(BaseModel):
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]


# ── routes ───────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    """Health check."""
    return {
        "environment": "SoftwareLifecycleEnv",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/reset", "/step", "/state"],
    }


@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()) -> dict:
    """Reset the environment, optionally to a specific task."""
    obs = env.reset(task_id=req.task_id)
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest) -> dict:
    """Execute a single action."""
    from env.models import Action

    action = Action(
        action_type=req.action_type,
        target_file=req.target_file,
        patch_content=req.patch_content,
    )
    result = env.step(action)
    return StepResponse(
        observation=result.observation.model_dump(),
        reward=result.reward,
        done=result.done,
        info=result.info,
    ).model_dump()


@app.get("/state")
def state() -> dict:
    """Return current environment state."""
    return env.state()

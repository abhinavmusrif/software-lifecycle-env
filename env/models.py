"""Pydantic typed models for the SoftwareLifecycleEnv OpenEnv interface.

Exports
-------
ActionType   – enum of allowed actions
Action       – agent action payload
Observation  – observation returned after each step
RewardInfo   – reward metadata for a single step
StepResult   – full (observation, reward, done, info) tuple
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """Allowed action types in the environment."""

    INSPECT_FILE = "inspect_file"
    APPLY_PATCH = "apply_patch"
    RUN_TESTS = "run_tests"
    SUBMIT = "submit"


class Action(BaseModel):
    """An action taken by the agent in a single step."""

    action_type: ActionType = Field(
        ..., description="One of: inspect_file, apply_patch, run_tests, submit"
    )
    target_file: Optional[str] = Field(
        None, description="Filename to inspect or patch"
    )
    patch_content: Optional[str] = Field(
        None, description="Full replacement file content (for apply_patch)"
    )


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """Observation returned to the agent after every step or reset."""

    task_id: str = ""
    task_type: str = ""
    task_description: str = ""
    files: Dict[str, str] = Field(default_factory=dict)
    test_output: Optional[str] = None
    last_action_result: Optional[str] = None
    steps_taken: int = 0
    max_steps: int = 10


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------

class RewardInfo(BaseModel):
    """Reward metadata for a single step."""

    reward: float = Field(0.0, ge=-1.0, le=1.0)
    reason: str = ""


# ---------------------------------------------------------------------------
# Step result (the full return type of env.step())
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    """Full result from ``SoftwareLifecycleEnv.step()``."""

    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)

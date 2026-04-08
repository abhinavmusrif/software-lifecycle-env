"""SoftwareLifecycleEnv — core environment implementing the OpenEnv interface.

Public API
----------
reset(task_id)           → Observation
step(action: Action)     → StepResult(observation, reward, done, info)
state()                  → dict
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

from env.graders import grade_task
from env.models import Action, ActionType, Observation, StepResult
from env.tasks import TASKS, get_task, list_task_ids


class SoftwareLifecycleEnv:
    """Deterministic software-engineering benchmark environment."""

    # ── construction ─────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._task: Optional[dict] = None
        self._files: Dict[str, str] = {}
        self._steps_taken: int = 0
        self._max_steps: int = 10
        self._done: bool = True
        self._rewards: List[float] = []
        self._inspected_files: Set[str] = set()
        self._patched_files: Set[str] = set()
        self._tests_passed: bool = False
        self._action_history: List[str] = []
        self._last_action_result: Optional[str] = None

    # ── public interface ─────────────────────────────────────────────────

    def reset(self, task_id: Optional[str] = None) -> Observation:
        """Reset the environment to a fresh task.

        Parameters
        ----------
        task_id : str, optional
            Which task to load.  Defaults to the first task in the list.
        """
        if task_id is None:
            task_id = list_task_ids()[0]

        task = get_task(task_id)
        self._task = task
        self._files = copy.deepcopy(task["files"])
        self._steps_taken = 0
        self._max_steps = task.get("max_steps", 10)
        self._done = False
        self._rewards = []
        self._inspected_files = set()
        self._patched_files = set()
        self._tests_passed = False
        self._action_history = []
        self._last_action_result = None

        return self._build_observation()

    def step(self, action: Action) -> StepResult:
        """Execute one action and return (observation, reward, done, info)."""
        if self._done:
            return StepResult(
                observation=self._build_observation(),
                reward=0.0,
                done=True,
                info={"error": "Episode already done. Call reset()."},
            )

        self._steps_taken += 1
        reward = 0.0
        info: Dict[str, Any] = {}

        # ── penalty: repeated exact action ───────────────────────────────
        action_key = (
            f"{action.action_type.value}|{action.target_file}|"
            f"{hash(action.patch_content)}"
        )
        if action_key in self._action_history:
            reward -= 0.05
            info["penalty"] = "repeated_action"
        self._action_history.append(action_key)

        # ── dispatch ─────────────────────────────────────────────────────
        if action.action_type == ActionType.INSPECT_FILE:
            reward += self._handle_inspect(action, info)
        elif action.action_type == ActionType.APPLY_PATCH:
            reward += self._handle_patch(action, info)
        elif action.action_type == ActionType.RUN_TESTS:
            reward += self._handle_run_tests(info)
        elif action.action_type == ActionType.SUBMIT:
            reward += self._handle_submit(info)

        # ── check step budget ────────────────────────────────────────────
        if self._steps_taken >= self._max_steps and not self._done:
            reward -= 0.20
            info.setdefault("penalty", "")
            info["penalty"] = (info["penalty"] + " exceeded_max_steps").strip()
            self._done = True

        reward = round(reward, 2)
        self._rewards.append(reward)

        return StepResult(
            observation=self._build_observation(),
            reward=reward,
            done=self._done,
            info=info,
        )

    def state(self) -> dict:
        """Return a JSON-serialisable snapshot of the environment."""
        return {
            "task_id": self._task["task_id"] if self._task else None,
            "task_type": self._task["task_type"] if self._task else None,
            "steps_taken": self._steps_taken,
            "max_steps": self._max_steps,
            "done": self._done,
            "rewards": list(self._rewards),
            "inspected_files": sorted(self._inspected_files),
            "patched_files": sorted(self._patched_files),
            "tests_passed": self._tests_passed,
            "files": dict(self._files),
        }

    # ── action handlers ──────────────────────────────────────────────────

    def _handle_inspect(self, action: Action, info: dict) -> float:
        fname = action.target_file or ""
        if fname not in self._files:
            self._last_action_result = f"File not found: {fname}"
            info["error"] = f"File not found: {fname}"
            return -0.05

        self._last_action_result = self._files[fname]
        self._inspected_files.add(fname)

        assert self._task is not None
        if fname == self._task["buggy_file"]:
            info["inspect"] = "correct_file"
            return 0.10
        info["inspect"] = "wrong_file"
        return -0.05

    def _handle_patch(self, action: Action, info: dict) -> float:
        fname = action.target_file or ""
        content = action.patch_content

        if not content:
            self._last_action_result = "No patch content provided."
            info["error"] = "invalid_patch"
            return -0.10

        if fname not in self._files:
            self._last_action_result = f"File not found: {fname}"
            info["error"] = f"File not found: {fname}"
            return -0.10

        # Apply patch
        self._files[fname] = content
        self._patched_files.add(fname)
        self._last_action_result = f"Patched {fname}"

        reward = 0.0
        assert self._task is not None
        buggy = self._task["buggy_file"]
        pattern = self._task["expected_patch_pattern"]

        if fname == buggy:
            reward += 0.20
            info["patch"] = "correct_file"
            if pattern in content:
                reward += 0.30
                info["pattern_match"] = True
        else:
            info["patch"] = "wrong_file"

        return reward

    def _handle_run_tests(self, info: dict) -> float:
        """Simulate tests deterministically: pass iff the expected pattern is present."""
        assert self._task is not None
        buggy = self._task["buggy_file"]
        pattern = self._task["expected_patch_pattern"]
        current = self._files.get(buggy, "")

        if pattern in current:
            self._tests_passed = True
            self._last_action_result = "All tests passed."
            info["tests"] = "passed"
            return 0.40

        self._tests_passed = False
        tid = self._task["task_id"]
        self._last_action_result = (
            f"FAILED — {tid}\n"
            "AssertionError: test output does not match expected.\n"
            "1 failed, 0 passed."
        )
        info["tests"] = "failed"
        return 0.0

    def _handle_submit(self, info: dict) -> float:
        """End episode and return the final grading score as reward."""
        self._done = True
        grading_state = {
            "inspected_files": self._inspected_files,
            "patched_files": self._patched_files,
            "current_files": self._files,
            "tests_passed": self._tests_passed,
        }
        final_score = grade_task(self._task, grading_state)  # type: ignore[arg-type]
        self._last_action_result = f"Submitted. Final score: {final_score:.2f}"
        info["final_score"] = final_score
        return final_score

    # ── helpers ──────────────────────────────────────────────────────────

    def _build_observation(self) -> Observation:
        return Observation(
            task_id=self._task["task_id"] if self._task else "",
            task_type=self._task["task_type"] if self._task else "",
            task_description=self._task["task_description"] if self._task else "",
            files=dict(self._files),
            test_output=self._last_action_result,
            last_action_result=self._last_action_result,
            steps_taken=self._steps_taken,
            max_steps=self._max_steps,
        )

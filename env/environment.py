"""SoftwareLifecycleEnv — core environment implementing the OpenEnv interface.

Public API
----------
reset(task_id)           -> Observation
step(action: Action)     -> StepResult(observation, reward, done, info)
state()                  -> dict
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

from env.graders import clamp_score, grade_task
from env.models import Action, ActionType, Observation, StepResult
from env.tasks import get_task, list_task_ids
from env.validation import ValidationReport, validate_task


class SoftwareLifecycleEnv:
    """Deterministic software-engineering benchmark environment."""

    def __init__(self) -> None:
        self._task: Optional[dict] = None
        self._files: Dict[str, str] = {}
        self._steps_taken: int = 0
        self._max_steps: int = 10
        self._done: bool = True
        self._rewards: List[float] = []
        self._inspected_files: Set[str] = set()
        self._inspected_buckets: Set[str] = set()
        self._patched_files: Set[str] = set()
        self._tests_passed: bool = False
        self._tests_run_count: int = 0
        self._action_history: List[str] = []
        self._coarse_action_history: List[str] = []
        self._repeated_action_count: int = 0
        self._wrong_patch_count: int = 0
        self._patch_attempt_count: int = 0
        self._no_op_patch_count: int = 0
        self._superficial_patch_count: int = 0
        self._regressive_patch_count: int = 0
        self._helpful_patch_count: int = 0
        self._overflowed: bool = False
        self._last_action_result: Optional[str] = None
        self._last_validation_report: Optional[ValidationReport] = None
        self._best_validation_score: float = 0.0
        self._last_test_score: float = 0.0

    def reset(self, task_id: Optional[str] = None) -> Observation:
        """Reset the environment to a fresh task."""
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
        self._inspected_buckets = set()
        self._patched_files = set()
        self._tests_passed = False
        self._tests_run_count = 0
        self._action_history = []
        self._coarse_action_history = []
        self._repeated_action_count = 0
        self._wrong_patch_count = 0
        self._patch_attempt_count = 0
        self._no_op_patch_count = 0
        self._superficial_patch_count = 0
        self._regressive_patch_count = 0
        self._helpful_patch_count = 0
        self._overflowed = False
        self._last_action_result = None
        self._last_validation_report = self._refresh_validation_report()
        self._best_validation_score = self._last_validation_report.overall_score
        self._last_test_score = self._last_validation_report.overall_score

        return self._build_observation()

    def step(self, action: Action) -> StepResult:
        """Execute one action and return (observation, reward, done, info)."""
        if self._done:
            return StepResult(
                observation=self._build_observation(),
                reward=clamp_score(0.0),
                done=True,
                info={"error": "Episode already done. Call reset()."},
            )

        self._steps_taken += 1
        reward = 0.01
        info: Dict[str, Any] = {}

        exact_key = (
            f"{action.action_type.value}|{action.target_file}|"
            f"{(action.patch_content or '').strip()}"
        )
        coarse_key = f"{action.action_type.value}|{action.target_file or ''}"

        repeated_exact = exact_key in self._action_history
        looped_action = len(self._coarse_action_history) >= 2 and all(
            previous == coarse_key for previous in self._coarse_action_history[-2:]
        )
        if repeated_exact or looped_action:
            self._repeated_action_count += 1
            info["penalty"] = "repeated_action"

        self._action_history.append(exact_key)
        self._coarse_action_history.append(coarse_key)

        if action.action_type == ActionType.INSPECT_FILE:
            reward = self._handle_inspect(action, info)
        elif action.action_type == ActionType.APPLY_PATCH:
            reward = self._handle_patch(action, info)
        elif action.action_type == ActionType.RUN_TESTS:
            reward = self._handle_run_tests(info)
        elif action.action_type == ActionType.SUBMIT:
            reward = self._handle_submit(info)

        if repeated_exact:
            reward -= 0.05
        if looped_action:
            reward -= 0.03

        if self._steps_taken >= self._max_steps and not self._done:
            reward -= 0.12
            self._overflowed = True
            self._done = True
            info["penalty"] = (
                f"{info.get('penalty', '')} step_overflow".strip()
                if info.get("penalty")
                else "step_overflow"
            )

        final_reward = clamp_score(reward)
        self._rewards.append(final_reward)

        return StepResult(
            observation=self._build_observation(),
            reward=final_reward,
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
            "inspected_buckets": sorted(self._inspected_buckets),
            "patched_files": sorted(self._patched_files),
            "tests_passed": self._tests_passed,
            "tests_run_count": self._tests_run_count,
            "repeated_action_count": self._repeated_action_count,
            "patch_attempt_count": self._patch_attempt_count,
            "no_op_patch_count": self._no_op_patch_count,
            "superficial_patch_count": self._superficial_patch_count,
            "regressive_patch_count": self._regressive_patch_count,
            "helpful_patch_count": self._helpful_patch_count,
            "overflowed": self._overflowed,
            "files": dict(self._files),
            "validation_report": (
                self._last_validation_report.as_public_dict()
                if self._last_validation_report is not None
                else None
            ),
        }

    def _handle_inspect(self, action: Action, info: dict) -> float:
        assert self._task is not None
        fname = action.target_file or ""
        if fname not in self._files:
            self._last_action_result = f"File not found: {fname}"
            info["error"] = f"File not found: {fname}"
            return 0.01

        self._last_action_result = self._files[fname]
        already_inspected = fname in self._inspected_files
        self._inspected_files.add(fname)
        bucket = self._inspection_bucket_for_file(fname)
        new_bucket = bool(bucket and bucket not in self._inspected_buckets)
        if bucket:
            self._inspected_buckets.add(bucket)

        if fname in self._task.get("patch_targets", []):
            info["inspect"] = "implementation_context"
            info["inspect_bucket"] = bucket or "implementation"
            reward = 0.14 if not already_inspected else 0.04
            if new_bucket and not already_inspected:
                reward += 0.04
            return reward
        if bucket == "symptom":
            info["inspect"] = "symptom_context"
            info["inspect_bucket"] = bucket
            reward = 0.12 if not already_inspected else 0.04
            if new_bucket and not already_inspected:
                reward += 0.04
            return reward
        if bucket in {"flow", "consumers"}:
            info["inspect"] = "execution_path_context"
            info["inspect_bucket"] = bucket
            reward = 0.11 if not already_inspected else 0.04
            if new_bucket and not already_inspected:
                reward += 0.04
            return reward
        if bucket in {"policy", "contracts"}:
            info["inspect"] = "contract_context"
            info["inspect_bucket"] = bucket
            reward = 0.10 if not already_inspected else 0.04
            if new_bucket and not already_inspected:
                reward += 0.04
            return reward
        if bucket == "shared_logic":
            info["inspect"] = "shared_logic_context"
            info["inspect_bucket"] = bucket
            reward = 0.12 if not already_inspected else 0.04
            if new_bucket and not already_inspected:
                reward += 0.04
            return reward
        if fname in self._task.get("relevant_files", []):
            info["inspect"] = "supporting_context"
            if bucket:
                info["inspect_bucket"] = bucket
            return 0.12 if not already_inspected else 0.04

        info["inspect"] = "off_target"
        return 0.02

    def _handle_patch(self, action: Action, info: dict) -> float:
        assert self._task is not None
        fname = action.target_file or ""
        content = action.patch_content

        if not content:
            self._last_action_result = "No patch content provided."
            info["error"] = "invalid_patch"
            return 0.01
        if fname not in self._files:
            self._last_action_result = f"File not found: {fname}"
            info["error"] = f"File not found: {fname}"
            return 0.01

        self._patch_attempt_count += 1
        if self._files[fname] == content:
            self._no_op_patch_count += 1
            self._last_action_result = f"No changes applied to {fname}."
            info["patch"] = "no_op"
            return 0.01

        before_report = self._refresh_validation_report()
        self._files[fname] = content
        self._patched_files.add(fname)
        if fname not in self._task.get("patch_targets", []):
            self._wrong_patch_count += 1

        after_report = self._refresh_validation_report()
        self._best_validation_score = max(self._best_validation_score, after_report.overall_score)

        delta = after_report.overall_score - before_report.overall_score
        behavior_delta = after_report.behavioral_score - before_report.behavioral_score
        regression_delta = after_report.regression_score - before_report.regression_score
        structure_delta = after_report.structure_score - before_report.structure_score
        anti_gaming_delta = after_report.anti_gaming_score - before_report.anti_gaming_score
        is_patch_target = fname in self._task.get("patch_targets", [])
        hidden_failures = after_report.hidden_failure_count

        reward = 0.06 if is_patch_target else 0.03
        if delta > 0:
            self._helpful_patch_count += 1
            reward += 0.32 * delta
            reward += 0.10 * max(0.0, behavior_delta)
            reward += 0.08 * max(0.0, regression_delta)
            reward += 0.06 * max(0.0, structure_delta)
            reward += 0.06 * max(0.0, anti_gaming_delta)
            info["patch"] = "improved_behavior"
            if after_report.behavioral_complete and (
                hidden_failures > 0
                or not after_report.regression_complete
                or not after_report.anti_gaming_complete
            ):
                reward = min(reward, 0.16 if is_patch_target else 0.10)
                info["patch"] = "overfit_progress"
        elif delta == 0:
            self._superficial_patch_count += 1
            reward = 0.02 if is_patch_target else 0.01
            info["patch"] = "superficial_change"
        else:
            self._regressive_patch_count += 1
            reward = 0.01
            info["patch"] = "regressed_behavior"

        if not is_patch_target:
            reward -= 0.03
        else:
            required_bucket = self._required_diagnostic_bucket()
            if required_bucket and required_bucket not in self._inspected_buckets:
                reward -= 0.04
                info["workflow"] = f"patched_before_reviewing_{required_bucket}"
            elif self._task.get("workflow_focus") in {"testing", "debugging"} and "policy" in self._task.get("inspection_buckets", {}) and "policy" not in self._inspected_buckets:
                reward -= 0.02
                info["workflow"] = "patched_before_reviewing_policy"
            elif self._task.get("workflow_focus") == "maintenance" and "contracts" not in self._inspected_buckets:
                reward -= 0.03
                info["workflow"] = "patched_before_reviewing_contracts"

        self._last_action_result = (
            f"Patched {fname}. Validation now {after_report.overall_score:.2f}. "
            f"{after_report.summary}"
        )
        info["validation"] = after_report.as_public_dict()
        return reward

    def _handle_run_tests(self, info: dict) -> float:
        report = self._refresh_validation_report()
        self._tests_run_count += 1
        improvement = report.overall_score - self._last_test_score
        self._last_test_score = report.overall_score
        self._best_validation_score = max(self._best_validation_score, report.overall_score)

        info["validation"] = report.as_public_dict()
        if report.final_success:
            self._tests_passed = True
            self._last_action_result = self._format_test_output(report)
            info["tests"] = "passed"
            return 0.72

        self._tests_passed = False
        self._last_action_result = self._format_test_output(report)
        info["tests"] = "failed"
        reward = 0.05 + (0.24 * report.overall_score) + (0.08 * max(0.0, improvement))
        reward += 0.06 * min(report.regression_score, report.anti_gaming_score)
        if report.behavioral_complete and (
            report.hidden_failure_count > 0 or not report.anti_gaming_complete
        ):
            reward = min(reward, 0.16)
        return reward

    def _handle_submit(self, info: dict) -> float:
        assert self._task is not None
        self._done = True
        report = self._refresh_validation_report()
        grading_state = {
            "inspected_files": self._inspected_files,
            "inspected_buckets": self._inspected_buckets,
            "patched_files": self._patched_files,
            "tests_run_count": self._tests_run_count,
            "steps_taken": self._steps_taken,
            "repeated_action_count": self._repeated_action_count,
            "patch_attempt_count": self._patch_attempt_count,
            "no_op_patch_count": self._no_op_patch_count,
            "superficial_patch_count": self._superficial_patch_count,
            "regressive_patch_count": self._regressive_patch_count,
            "helpful_patch_count": self._helpful_patch_count,
            "overflowed": self._overflowed,
            "validation_report": report,
        }
        final_score = grade_task(self._task, grading_state)
        self._last_action_result = (
            f"Submitted. Final score: {final_score:.2f}. "
            f"Validation summary: {report.summary}"
        )
        info["final_score"] = final_score
        info["validation"] = report.as_public_dict()
        return final_score

    def _refresh_validation_report(self) -> ValidationReport:
        assert self._task is not None
        self._last_validation_report = validate_task(self._task, self._files)
        return self._last_validation_report

    def _inspection_bucket_for_file(self, filename: str) -> Optional[str]:
        assert self._task is not None
        for bucket, bucket_files in self._task.get("inspection_buckets", {}).items():
            if filename in bucket_files:
                return bucket
        return None

    def _required_diagnostic_bucket(self) -> Optional[str]:
        assert self._task is not None
        workflow_focus = self._task.get("workflow_focus")
        if workflow_focus in {"testing", "debugging"}:
            return "symptom"
        if workflow_focus == "maintenance":
            return "contracts"
        return None

    def _format_test_output(self, report: ValidationReport) -> str:
        if report.final_success:
            return (
                "============================== test session ==============================\n"
                "collected deterministic checks\n"
                f"{report.passed_checks} passed, 0 failed\n"
                f"summary: {report.summary}"
            )

        failures = report.visible_failure_messages[:2]
        hidden_failures = len(report.hidden_failure_messages)
        if hidden_failures:
            failures.append(
                f"{hidden_failures} hidden regression or anti-gaming check(s) still failing."
            )
        failure_lines = "\n".join(f"- {message}" for message in failures)
        remaining = report.total_checks - report.passed_checks
        return (
            "============================== FAILURES ==============================\n"
            f"{failure_lines}\n"
            f"{remaining} failed, {report.passed_checks} passed\n"
            f"summary: {report.summary}"
        )

    def _build_observation(self) -> Observation:
        return Observation(
            task_id=self._task["task_id"] if self._task else "",
            task_type=self._task["task_type"] if self._task else "",
            workflow_focus=self._task.get("workflow_focus", "") if self._task else "",
            task_description=self._task["task_description"] if self._task else "",
            repo_summary=self._task.get("repo_summary", "") if self._task else "",
            important_files=list(self._task.get("important_files", [])) if self._task else [],
            failing_checks=list(self._task.get("failing_checks", [])) if self._task else [],
            constraints=list(self._task.get("constraints", [])) if self._task else [],
            files=dict(self._files),
            test_output=self._last_action_result,
            last_action_result=self._last_action_result,
            recent_actions=self._coarse_action_history[-5:],
            steps_taken=self._steps_taken,
            max_steps=self._max_steps,
        )

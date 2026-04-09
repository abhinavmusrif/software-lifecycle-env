#!/usr/bin/env python3
"""Diagnostic sweep for true task scores and hidden numeric boundary leaks.

This script intentionally distinguishes between:
* task outputs that are real scores/rewards and must satisfy 0 < x < 1
* internal validation progress ratios, which are not task scores

It fails if:
* any real task score/reward hits 0 or 1
* any validation payload still exposes internal score/progress/ratio fields
* any raw validation-report tree still contains float leaves at the boundaries
"""

from __future__ import annotations

import pathlib
import runpy
import sys
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.environment import SoftwareLifecycleEnv
from env.graders import grade_task, normalize_score
from env.models import Action, ActionType
from env.tasks import TASKS
from env.validation import validate_task


def load_quality_fixtures() -> Tuple[Dict[str, List[Action]], Dict[str, List[Action]]]:
    namespace = runpy.run_path(str(ROOT / "scripts" / "check_benchmark_quality.py"))
    return namespace["REFERENCE_SOLUTIONS"], namespace["ANTI_GAMING_ATTEMPTS"]


def grading_state_from_env(env: SoftwareLifecycleEnv) -> Dict[str, Any]:
    return {
        "inspected_files": env._inspected_files,
        "inspected_buckets": env._inspected_buckets,
        "patched_files": env._patched_files,
        "tests_run_count": env._tests_run_count,
        "steps_taken": env._steps_taken,
        "repeated_action_count": env._repeated_action_count,
        "patch_attempt_count": env._patch_attempt_count,
        "no_op_patch_count": env._no_op_patch_count,
        "superficial_patch_count": env._superficial_patch_count,
        "regressive_patch_count": env._regressive_patch_count,
        "helpful_patch_count": env._helpful_patch_count,
        "overflowed": env._overflowed,
        "validation_report": env._last_validation_report,
    }


def record_violation(
    violations: List[Dict[str, Any]],
    *,
    task_id: str,
    path: str,
    field: str,
    value: Any,
) -> None:
    normalized = (
        normalize_score(float(value))
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else value
    )
    violations.append(
        {
            "task_id": task_id,
            "path": path,
            "field": field,
            "raw_value": value,
            "normalized_value": normalized,
        }
    )


def inspect_real_score(
    violations: List[Dict[str, Any]],
    collected_scores: List[float],
    *,
    task_id: str,
    path: str,
    field: str,
    value: float,
) -> None:
    collected_scores.append(value)
    if not (0 < value < 1):
        record_violation(
            violations,
            task_id=task_id,
            path=path,
            field=field,
            value=value,
        )


def inspect_real_reward(
    violations: List[Dict[str, Any]],
    collected_rewards: List[float],
    *,
    task_id: str,
    path: str,
    value: float,
) -> None:
    collected_rewards.append(value)
    if not (0 < value < 1):
        record_violation(
            violations,
            task_id=task_id,
            path=path,
            field="reward",
            value=value,
        )


def walk_payload(obj: Any, prefix: str = "") -> Iterable[Tuple[str, str, Any]]:
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield child_prefix, key, value
            yield from walk_payload(value, child_prefix)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            child_prefix = f"{prefix}[{index}]"
            yield from walk_payload(value, child_prefix)


def inspect_no_internal_metric_keys(
    violations: List[Dict[str, Any]],
    *,
    task_id: str,
    path: str,
    payload: Any,
) -> None:
    for value_path, key, value in walk_payload(payload, path):
        if (
            key != "final_score"
            and (
                key.endswith("_score")
                or key.endswith("_ratio")
                or key.endswith("_progress")
            )
        ):
            record_violation(
                violations,
                task_id=task_id,
                path=value_path,
                field=key,
                value=value,
            )
        if isinstance(value, float) and value in {0.0, 1.0}:
            record_violation(
                violations,
                task_id=task_id,
                path=value_path,
                field=key,
                value=value,
            )


def run_actions(task_id: str, actions: Iterable[Action]) -> Tuple[SoftwareLifecycleEnv, Any]:
    env = SoftwareLifecycleEnv()
    env.reset(task_id)
    last_result = None
    for action in actions:
        last_result = env.step(action)
    return env, last_result


def main() -> None:
    reference_solutions, anti_gaming_attempts = load_quality_fixtures()
    violations: List[Dict[str, Any]] = []
    collected_scores: List[float] = []
    collected_rewards: List[float] = []

    for task in TASKS:
        task_id = task["task_id"]

        initial_report = validate_task(task, task["files"])
        inspect_no_internal_metric_keys(
            violations,
            task_id=task_id,
            path="validate_task.initial.raw_report",
            payload=initial_report,
        )
        inspect_no_internal_metric_keys(
            violations,
            task_id=task_id,
            path="validate_task.initial.as_public_dict",
            payload=initial_report.as_public_dict(),
        )

        env = SoftwareLifecycleEnv()
        env.reset(task_id)
        inspect_no_internal_metric_keys(
            violations,
            task_id=task_id,
            path="env.state.after_reset.validation_report",
            payload=env.state().get("validation_report", {}),
        )
        inspect_real_score(
            violations,
            collected_scores,
            task_id=task_id,
            path="grade_task.initial",
            field="final_score",
            value=float(grade_task(task, grading_state_from_env(env))),
        )

        submit_result = env.step(Action(action_type=ActionType.SUBMIT))
        inspect_real_reward(
            violations,
            collected_rewards,
            task_id=task_id,
            path="env.step.submit.reward",
            value=float(submit_result.reward),
        )
        inspect_real_score(
            violations,
            collected_scores,
            task_id=task_id,
            path="env.step.submit.info.final_score",
            field="final_score",
            value=float(submit_result.info["final_score"]),
        )
        inspect_no_internal_metric_keys(
            violations,
            task_id=task_id,
            path="env.step.submit.info.validation",
            payload=submit_result.info.get("validation", {}),
        )

        for label, actions in (
            ("cheat", anti_gaming_attempts[task_id]),
            ("solve", reference_solutions[task_id]),
        ):
            episode_env, last_result = run_actions(task_id, actions)
            if last_result is None:
                continue

            for index, reward in enumerate(episode_env.state()["rewards"]):
                inspect_real_reward(
                    violations,
                    collected_rewards,
                    task_id=task_id,
                    path=f"{label}.episode.rewards[{index}]",
                    value=float(reward),
                )
            inspect_real_score(
                violations,
                collected_scores,
                task_id=task_id,
                path=f"{label}.episode.final_score",
                field="final_score",
                value=float(last_result.info["final_score"]),
            )
            report = validate_task(task, episode_env.state()["files"])
            inspect_no_internal_metric_keys(
                violations,
                task_id=task_id,
                path=f"{label}.validate_task.raw_report",
                payload=report,
            )
            inspect_no_internal_metric_keys(
                violations,
                task_id=task_id,
                path=f"{label}.validate_task.as_public_dict",
                payload=report.as_public_dict(),
            )

    for violation in violations:
        print(
            "[SCORE-CONTRACT-VIOLATION]",
            f"task_id={violation['task_id']}",
            f"path={violation['path']}",
            f"field={violation['field']}",
            f"raw_value={violation['raw_value']}",
            f"normalized_value={violation['normalized_value']}",
        )

    print(
        "[STRICT-BOUND-SUMMARY]",
        f"score_min={min(collected_scores):.6f}",
        f"score_max={max(collected_scores):.6f}",
        f"reward_min={min(collected_rewards):.6f}",
        f"reward_max={max(collected_rewards):.6f}",
        f"score_count={len(collected_scores)}",
        f"reward_count={len(collected_rewards)}",
    )

    if violations:
        print(f"[STRICT-BOUND-SUMMARY] violations={len(violations)}")
        raise SystemExit(1)

    print("ZERO STRICT-BOUND VIOLATIONS FOUND")


if __name__ == "__main__":
    main()

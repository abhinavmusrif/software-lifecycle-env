#!/usr/bin/env python3
"""Strict-bound diagnostic sweep for task scores and rewards.

Enumerates all tasks and inspects:
* direct validation report objects
* validation report serialization helpers
* direct grade_task execution
* environment submit-path final scores and rewards
* cheat and strong-solve trajectories

Any exact 0 or 1 score-like value is reported with the path that produced it.
"""

from __future__ import annotations

import pathlib
import runpy
import sys
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.environment import SoftwareLifecycleEnv
from env.graders import grade_task, normalize_score
from env.models import Action, ActionType
from env.tasks import TASKS
from env.validation import validate_task

SCORE_FIELDS = (
    "behavioral_score",
    "regression_score",
    "structure_score",
    "anti_gaming_score",
    "overall_score",
)


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


def collect_score(payload: Dict[str, Any], field: str) -> float | None:
    value = payload.get(field)
    if isinstance(value, bool) or value is None:
        return None
    return float(value)


def record_violation(
    violations: List[Dict[str, Any]],
    *,
    task_id: str,
    path: str,
    field: str,
    value: float,
) -> None:
    violations.append(
        {
            "task_id": task_id,
            "path": path,
            "field": field,
            "raw_value": value,
            "normalized_value": normalize_score(value),
        }
    )


def inspect_score_value(
    violations: List[Dict[str, Any]],
    task_id: str,
    path: str,
    field: str,
    value: float | None,
    collected_scores: List[float],
) -> None:
    if value is None:
        return
    collected_scores.append(float(value))
    if value in (0.0, 1.0) or not (0 < value < 1):
        record_violation(
            violations,
            task_id=task_id,
            path=path,
            field=field,
            value=float(value),
        )


def inspect_report_object(
    report: Any,
    *,
    task_id: str,
    path: str,
    violations: List[Dict[str, Any]],
    collected_scores: List[float],
) -> None:
    for field in SCORE_FIELDS:
        inspect_score_value(
            violations,
            task_id,
            path,
            field,
            float(getattr(report, field)),
            collected_scores,
        )


def inspect_mapping(
    payload: Dict[str, Any],
    *,
    task_id: str,
    path: str,
    violations: List[Dict[str, Any]],
    collected_scores: List[float],
) -> None:
    for field in SCORE_FIELDS:
        inspect_score_value(
            violations,
            task_id,
            path,
            field,
            collect_score(payload, field),
            collected_scores,
        )


def walk_float_leaves(obj: Any, prefix: str = "") -> Iterable[Tuple[str, float]]:
    if isinstance(obj, bool):
        return
    if isinstance(obj, float):
        yield prefix or "<root>", obj
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from walk_float_leaves(value, child_prefix)
        return
    if isinstance(obj, list):
        for index, value in enumerate(obj):
            child_prefix = f"{prefix}[{index}]"
            yield from walk_float_leaves(value, child_prefix)


def inspect_float_tree(
    obj: Any,
    *,
    task_id: str,
    path: str,
    violations: List[Dict[str, Any]],
) -> None:
    for field_path, value in walk_float_leaves(obj):
        if value in (0.0, 1.0) or not (0 < value < 1):
            record_violation(
                violations,
                task_id=task_id,
                path=f"{path}.{field_path}",
                field=field_path,
                value=float(value),
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
        inspect_report_object(
            initial_report,
            task_id=task_id,
            path="validate_task.initial.report",
            violations=violations,
            collected_scores=collected_scores,
        )
        inspect_float_tree(
            asdict(initial_report),
            task_id=task_id,
            path="validate_task.initial.asdict_recursive",
            violations=violations,
        )
        inspect_mapping(
            initial_report.as_dict(),
            task_id=task_id,
            path="validate_task.initial.as_dict",
            violations=violations,
            collected_scores=collected_scores,
        )
        inspect_mapping(
            initial_report.as_public_dict(),
            task_id=task_id,
            path="validate_task.initial.as_public_dict",
            violations=violations,
            collected_scores=collected_scores,
        )

        env = SoftwareLifecycleEnv()
        env.reset(task_id)
        direct_score = grade_task(task, grading_state_from_env(env))
        inspect_score_value(
            violations,
            task_id,
            "grade_task.initial",
            "final_score",
            direct_score,
            collected_scores,
        )
        inspect_mapping(
            env.state().get("validation_report", {}),
            task_id=task_id,
            path="env.state.after_reset.validation_report",
            violations=violations,
            collected_scores=collected_scores,
        )
        inspect_float_tree(
            env.state().get("validation_report", {}),
            task_id=task_id,
            path="env.state.after_reset.validation_report_recursive",
            violations=violations,
        )

        submit_result = env.step(Action(action_type=ActionType.SUBMIT))
        inspect_score_value(
            violations,
            task_id,
            "env.step.submit.reward",
            "reward",
            float(submit_result.reward),
            collected_rewards,
        )
        inspect_score_value(
            violations,
            task_id,
            "env.step.submit.info",
            "final_score",
            float(submit_result.info["final_score"]),
            collected_scores,
        )
        inspect_mapping(
            submit_result.info.get("validation", {}),
            task_id=task_id,
            path="env.step.submit.validation",
            violations=violations,
            collected_scores=collected_scores,
        )
        inspect_float_tree(
            submit_result.info.get("validation", {}),
            task_id=task_id,
            path="env.step.submit.validation_recursive",
            violations=violations,
        )

        for label, actions in (
            ("cheat", anti_gaming_attempts[task_id]),
            ("solve", reference_solutions[task_id]),
        ):
            episode_env, last_result = run_actions(task_id, actions)
            if last_result is None:
                continue

            for reward in episode_env.state()["rewards"]:
                inspect_score_value(
                    violations,
                    task_id,
                    f"{label}.episode.rewards",
                    "reward",
                    float(reward),
                    collected_rewards,
                )
            inspect_score_value(
                violations,
                task_id,
                f"{label}.episode.final_score",
                "final_score",
                float(last_result.info["final_score"]),
                collected_scores,
            )
            report = validate_task(task, episode_env.state()["files"])
            inspect_report_object(
                report,
                task_id=task_id,
                path=f"{label}.validate_task.report",
                violations=violations,
                collected_scores=collected_scores,
            )
            inspect_float_tree(
                asdict(report),
                task_id=task_id,
                path=f"{label}.validate_task.asdict_recursive",
                violations=violations,
            )
            inspect_mapping(
                report.as_dict(),
                task_id=task_id,
                path=f"{label}.validate_task.as_dict",
                violations=violations,
                collected_scores=collected_scores,
            )
            inspect_mapping(
                report.as_public_dict(),
                task_id=task_id,
                path=f"{label}.validate_task.as_public_dict",
                violations=violations,
                collected_scores=collected_scores,
            )

    for violation in violations:
        print(
            "[STRICT-BOUND-VIOLATION]",
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

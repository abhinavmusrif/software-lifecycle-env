"""Deterministic grading helpers for SoftwareLifecycleEnv.

Final grading combines workflow quality, hidden regression coverage, and
anti-gaming signals instead of rewarding magic substrings.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Set


STRICT_MIN_SCORE = 0.01
STRICT_MAX_SCORE = 0.99


def clamp_score(
    value: float,
    lo: float = STRICT_MIN_SCORE,
    hi: float = STRICT_MAX_SCORE,
) -> float:
    """Clamp *value* to the validator-safe open interval represented by [0.01, 0.99]."""
    return round(max(lo, min(hi, value)), 2)


def _coverage(items: Iterable[str], target_items: Iterable[str]) -> float:
    item_set = set(items)
    target_set = set(target_items)
    if not target_set:
        return 0.0
    return len(item_set & target_set) / len(target_set)


def grade_task(task: dict, env_state: Dict[str, Any]) -> float:
    """Grade a completed episode using task-aware validation and workflow signals."""
    inspected: Set[str] = set(env_state.get("inspected_files", set()))
    patched: Set[str] = set(env_state.get("patched_files", set()))
    relevant_files = task.get("relevant_files", [])
    patch_targets = task.get("patch_targets", [])

    inspection_score = _coverage(inspected, relevant_files)
    patch_focus_score = _coverage(patched, patch_targets)

    wrong_patches = max(0, len(patched - set(patch_targets)))
    wrong_patch_ratio = wrong_patches / max(1, len(patched))
    tests_used = 1.0 if env_state.get("tests_run_count", 0) > 0 else 0.0
    repeated_ratio = min(
        1.0,
        env_state.get("repeated_action_count", 0) / max(1, env_state.get("steps_taken", 1)),
    )
    overflow_penalty = 1.0 if env_state.get("overflowed", False) else 0.0
    no_op_ratio = min(
        1.0,
        env_state.get("no_op_patch_count", 0) / max(1, env_state.get("patch_attempt_count", 1)),
    )
    superficial_ratio = min(
        1.0,
        env_state.get("superficial_patch_count", 0)
        / max(1, env_state.get("patch_attempt_count", 1)),
    )
    regressive_ratio = min(
        1.0,
        env_state.get("regressive_patch_count", 0)
        / max(1, env_state.get("patch_attempt_count", 1)),
    )
    helpful_ratio = min(
        1.0,
        env_state.get("helpful_patch_count", 0) / max(1, env_state.get("patch_attempt_count", 1)),
    )

    validation_report = env_state.get("validation_report")
    behavioral = float(getattr(validation_report, "behavioral_score", 0.0))
    regression = float(getattr(validation_report, "regression_score", 0.0))
    structure = float(getattr(validation_report, "structure_score", 0.0))
    anti_gaming = float(getattr(validation_report, "anti_gaming_score", 0.0))
    overall = float(getattr(validation_report, "overall_score", 0.0))
    hidden_failures = len(getattr(validation_report, "hidden_failure_messages", []))
    integrity_failures = int(getattr(validation_report, "integrity_failure_count", 0))

    raw_score = (
        0.08 * inspection_score
        + 0.08 * patch_focus_score
        + 0.18 * overall
        + 0.10 * behavioral
        + 0.18 * regression
        + 0.16 * structure
        + 0.14 * anti_gaming
        + 0.04 * tests_used
        + 0.04 * helpful_ratio
    )
    raw_score -= 0.08 * wrong_patch_ratio
    raw_score -= 0.07 * repeated_ratio
    raw_score -= 0.07 * no_op_ratio
    raw_score -= 0.08 * superficial_ratio
    raw_score -= 0.10 * regressive_ratio
    raw_score -= 0.05 * overflow_penalty

    if env_state.get("patch_attempt_count", 0) == 0:
        raw_score = min(raw_score, 0.29)
    if env_state.get("tests_run_count", 0) == 0:
        raw_score = min(raw_score, 0.35)
    if env_state.get("helpful_patch_count", 0) == 0 and env_state.get("patch_attempt_count", 0) > 0:
        raw_score = min(raw_score, 0.45)

    if not bool(getattr(validation_report, "final_success", False)):
        if behavioral < 1.0:
            raw_score = min(raw_score, 0.49)
        if regression < 1.0 or anti_gaming < 1.0:
            raw_score = min(raw_score, 0.55)
        if task.get("task_id") == "task_medium_debugging":
            if behavioral == 1.0 and (regression < 0.5 or anti_gaming < 0.8):
                raw_score = min(raw_score, 0.35)
            if hidden_failures >= 4 or integrity_failures >= 2:
                raw_score = min(raw_score, 0.32)
        if task.get("task_id") == "task_hard_maintenance" and anti_gaming < 1.0:
            raw_score = min(raw_score, 0.49)

    return clamp_score(raw_score)

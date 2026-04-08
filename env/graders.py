"""Deterministic grading helpers for SoftwareLifecycleEnv.

Scoring rubric (partial credit, clamped to [0.0, 1.0]):
  Inspected correct file   → +0.20
  Patched correct file     → +0.30
  Patch contains pattern   → +0.20
  Tests pass               → +0.30
"""

from __future__ import annotations

from typing import Any, Dict, Set


def grade_task(task: dict, env_state: Dict[str, Any]) -> float:
    """Grade a completed episode against its task definition.

    Parameters
    ----------
    task : dict
        Task definition from ``tasks.TASKS``.
    env_state : dict
        Internal environment snapshot with keys:
        - ``inspected_files``  (set[str])
        - ``patched_files``    (set[str])
        - ``current_files``    (dict[str, str])
        - ``tests_passed``     (bool)

    Returns
    -------
    float
        Final score in [0.0, 1.0].
    """
    score = 0.0

    buggy_file: str = task["buggy_file"]
    expected_pattern: str = task["expected_patch_pattern"]

    # +0.20 — inspected the correct (buggy) file
    inspected: Set[str] = env_state.get("inspected_files", set())
    if buggy_file in inspected:
        score += 0.20

    # +0.30 — patched the correct file
    patched: Set[str] = env_state.get("patched_files", set())
    if buggy_file in patched:
        score += 0.30

    # +0.20 — patch content contains the expected fix pattern
    current_content = env_state.get("current_files", {}).get(buggy_file, "")
    if expected_pattern in current_content:
        score += 0.20

    # +0.30 — tests pass
    if env_state.get("tests_passed", False):
        score += 0.30

    return _clamp(score)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))

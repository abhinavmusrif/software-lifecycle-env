"""Deterministic task definitions for the SoftwareLifecycleEnv benchmark.

Exactly 3 tasks are provided — easy, medium, hard — each containing:
  - buggy source file(s) + test file(s)
  - the filename that needs fixing
  - a string pattern expected in the correct fix
  - the fully-fixed file content (used for deterministic test simulation)
  - a step budget
"""

from __future__ import annotations

from typing import Dict, List

# ── Task 1 — EASY: Testing / Bug Identification ─────────────────────────

_TASK_EASY = {
    "task_id": "task_easy_testing",
    "task_type": "easy",
    "task_description": (
        "The function `is_even` should return True when a number is even, "
        "but the test `assert is_even(4) == True` is failing. "
        "Inspect the file, identify the bug, apply a patch, run the tests, "
        "and submit."
    ),
    "files": {
        "utils.py": (
            "def is_even(n):\n"
            "    return n % 2 == 1\n"
        ),
        "test_utils.py": (
            "from utils import is_even\n"
            "\n"
            "def test_is_even():\n"
            "    assert is_even(4) == True\n"
            "    assert is_even(3) == False\n"
            "    assert is_even(0) == True\n"
        ),
    },
    "buggy_file": "utils.py",
    "expected_patch_pattern": "n % 2 == 0",
    "fixed_file_content": (
        "def is_even(n):\n"
        "    return n % 2 == 0\n"
    ),
    "max_steps": 10,
}

# ── Task 2 — MEDIUM: Debugging / Patch ──────────────────────────────────

_TASK_MEDIUM = {
    "task_id": "task_medium_debugging",
    "task_type": "medium",
    "task_description": (
        "The `add` function returns wrong results — `add(2, 3)` gives "
        "`-1` instead of `5`. Inspect the code, find the bug, patch it, "
        "run the tests, and submit."
    ),
    "files": {
        "math_ops.py": (
            "def add(a, b):\n"
            "    return a - b\n"
        ),
        "test_math_ops.py": (
            "from math_ops import add\n"
            "\n"
            "def test_add():\n"
            "    assert add(2, 3) == 5\n"
            "    assert add(0, 0) == 0\n"
            "    assert add(-1, 1) == 0\n"
        ),
    },
    "buggy_file": "math_ops.py",
    "expected_patch_pattern": "a + b",
    "fixed_file_content": (
        "def add(a, b):\n"
        "    return a + b\n"
    ),
    "max_steps": 10,
}

# ── Task 3 — HARD: Maintenance / Refactor ────────────────────────────────

_TASK_HARD = {
    "task_id": "task_hard_maintenance",
    "task_type": "hard",
    "task_description": (
        "The codebase has duplicated logic in `format_name` and "
        "`format_author`. Refactor them to share a common helper function "
        "called `_format_person`. Ensure all tests still pass."
    ),
    "files": {
        "formatters.py": (
            "def format_name(first, last):\n"
            '    return first.strip().title() + " " + last.strip().title()\n'
            "\n"
            "def format_author(first, last):\n"
            '    return first.strip().title() + " " + last.strip().title()\n'
        ),
        "test_formatters.py": (
            "from formatters import format_name, format_author\n"
            "\n"
            "def test_format_name():\n"
            '    assert format_name("  john", "DOE  ") == "John Doe"\n'
            "\n"
            "def test_format_author():\n"
            '    assert format_author("jane  ", "  SMITH") == "Jane Smith"\n'
        ),
    },
    "buggy_file": "formatters.py",
    "expected_patch_pattern": "_format_person",
    "fixed_file_content": (
        "def _format_person(first, last):\n"
        '    return first.strip().title() + " " + last.strip().title()\n'
        "\n"
        "def format_name(first, last):\n"
        "    return _format_person(first, last)\n"
        "\n"
        "def format_author(first, last):\n"
        "    return _format_person(first, last)\n"
    ),
    "max_steps": 15,
}

# ── Public API ───────────────────────────────────────────────────────────

TASKS: List[Dict] = [_TASK_EASY, _TASK_MEDIUM, _TASK_HARD]


def get_task(task_id: str) -> dict:
    """Return a task definition by its ID. Raises ValueError if not found."""
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")


def list_task_ids() -> List[str]:
    """Return the ordered list of all task IDs."""
    return [t["task_id"] for t in TASKS]

"""Deterministic task definitions for the SoftwareLifecycleEnv benchmark.

The public task IDs stay stable for validator compatibility, but the task
content is richer than the initial toy benchmark:

* easy   -> utility bug involving implementation, tests, and failure logs
* medium -> multi-file debugging with helper/presenter interaction
* hard   -> maintenance refactor that centralizes duplicated logic
"""

from __future__ import annotations

from typing import Dict, List


_TASK_EASY = {
    "task_id": "task_easy_testing",
    "task_type": "easy",
    "task_description": (
        "A release automation utility is generating invalid project slugs for "
        "deployment previews. Inspect the utility, the failing test, and the "
        "pytest log. Fix the bug so project names are normalized with the same "
        "slug format used by production routing."
    ),
    "repo_summary": (
        "Small release tooling package used to generate preview environment "
        "URLs from project names."
    ),
    "files": {
        "src/utils/slugify.py": (
            "def slugify_project_name(name: str) -> str:\n"
            "    normalized = name.strip().lower().replace('/', ' ')\n"
            "    normalized = normalized.replace('_', ' ')\n"
            "    pieces = [piece for piece in normalized.split(' ') if piece]\n"
            "    return '_'.join(pieces)\n"
        ),
        "tests/test_slugify.py": (
            "from src.utils.slugify import slugify_project_name\n"
            "\n"
            "def test_slugify_project_name():\n"
            "    assert slugify_project_name('  Launch Plan  ') == 'launch-plan'\n"
            "    assert slugify_project_name('Roadmap / Q4') == 'roadmap-q4'\n"
            "    assert slugify_project_name('API__Client') == 'api-client'\n"
            "    assert slugify_project_name('Already-clean') == 'already-clean'\n"
        ),
        "logs/pytest_easy.log": (
            "============================= FAILURES =============================\n"
            "_______________________ test_slugify_project_name _______________________\n"
            "E       AssertionError: assert 'launch_plan' == 'launch-plan'\n"
            "E         - launch-plan\n"
            "E         + launch_plan\n"
            "tests/test_slugify.py:4: AssertionError\n"
        ),
    },
    "important_files": [
        "src/utils/slugify.py",
        "tests/test_slugify.py",
        "logs/pytest_easy.log",
    ],
    "relevant_files": [
        "src/utils/slugify.py",
        "tests/test_slugify.py",
        "logs/pytest_easy.log",
    ],
    "patch_targets": ["src/utils/slugify.py"],
    "failing_checks": [
        "tests/test_slugify.py::test_slugify_project_name",
        "expected slug separator '-' but observed '_'",
    ],
    "visible_checks": [
        "slugify_project_name('  Launch Plan  ') -> 'launch-plan'",
        "slugify_project_name('Roadmap / Q4') -> 'roadmap-q4'",
        "slugify_project_name('API__Client') -> 'api-client'",
        "slugify_project_name('Already-clean') -> 'already-clean'",
    ],
    "hidden_checks": [
        "slugify_project_name('  DATA__Sync / nightly  ') -> 'data-sync-nightly'",
        "slugify_project_name('Ops///Board__EU') -> 'ops-board-eu'",
        "slugify_project_name('Sprint_24 / phase_2') -> 'sprint-24-phase-2'",
        "slugify_project_name('') -> ''",
    ],
    "expected_solve_path": [
        "inspect src/utils/slugify.py",
        "inspect tests/test_slugify.py and logs/pytest_easy.log",
        "patch src/utils/slugify.py",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Hidden slug cases catch implementations that only fix one visible separator example.",
        "Validation rejects constant-return and hardcoded-answer patches.",
        "The API exposes only visible validation details; hidden regressions remain internal to grading.",
    ],
    "constraints": [
        "Preserve lowercase normalization.",
        "Treat '/' and '_' as separators.",
        "Do not change the public function name.",
    ],
    "max_steps": 10,
}


_TASK_MEDIUM = {
    "task_id": "task_medium_debugging",
    "task_type": "medium",
    "task_description": (
        "The invoice presenter is returning the wrong `amount_due` in the API "
        "response. The symptom shows up in the presenter test, but the root "
        "cause is likely in a helper. Inspect the presenter, helper, and "
        "failure log, then restore the expected JSON output."
    ),
    "repo_summary": (
        "Billing service code that prepares invoice payloads for an internal "
        "admin API."
    ),
    "files": {
        "src/helpers/currency.py": (
            "def format_cents(cents: int) -> str:\n"
            "    dollars = cents / 100\n"
            "    return f'${dollars:.0f}'\n"
        ),
        "src/presenters/invoice_presenter.py": (
            "from src.helpers.currency import format_cents\n"
            "\n"
            "def present_invoice(invoice: dict) -> dict:\n"
            "    return {\n"
            "        'customer': invoice['customer'].strip(),\n"
            "        'amount_due': format_cents(invoice['amount_due_cents']),\n"
            "        'line_items': sorted(invoice['line_items']),\n"
            "        'status': invoice['status'].upper(),\n"
            "    }\n"
        ),
        "tests/test_invoice_presenter.py": (
            "from src.presenters.invoice_presenter import present_invoice\n"
            "\n"
            "def test_present_invoice_formats_amount_due():\n"
            "    invoice = {\n"
            "        'customer': '  Acme Corp  ',\n"
            "        'amount_due_cents': 1205,\n"
            "        'line_items': ['support', 'monitoring'],\n"
            "        'status': 'past_due',\n"
            "    }\n"
            "    assert present_invoice(invoice) == {\n"
            "        'customer': 'Acme Corp',\n"
            "        'amount_due': '$12.05',\n"
            "        'line_items': ['monitoring', 'support'],\n"
            "        'status': 'PAST_DUE',\n"
            "    }\n"
        ),
        "logs/pytest_medium.log": (
            "============================= FAILURES =============================\n"
            "______________ test_present_invoice_formats_amount_due ______________\n"
            "E       AssertionError: assert {'amount_due': '$12', ...} == {'amount_due': '$12.05', ...}\n"
            "E         Differing items:\n"
            "E         {'amount_due': '$12'} != {'amount_due': '$12.05'}\n"
            "tests/test_invoice_presenter.py:11: AssertionError\n"
        ),
    },
    "important_files": [
        "src/presenters/invoice_presenter.py",
        "src/helpers/currency.py",
        "tests/test_invoice_presenter.py",
        "logs/pytest_medium.log",
    ],
    "relevant_files": [
        "src/helpers/currency.py",
        "src/presenters/invoice_presenter.py",
        "tests/test_invoice_presenter.py",
        "logs/pytest_medium.log",
    ],
    "patch_targets": ["src/helpers/currency.py"],
    "failing_checks": [
        "tests/test_invoice_presenter.py::test_present_invoice_formats_amount_due",
        "amount_due should preserve dollars and cents",
    ],
    "visible_checks": [
        "format_cents(1205) -> '$12.05'",
        "present_invoice(primary visible invoice) -> expected API payload",
    ],
    "hidden_checks": [
        "format_cents(5) -> '$0.05'",
        "format_cents(2500) -> '$25.00'",
        "format_cents(101) -> '$1.01'",
        "present_invoice(hidden 99-cent invoice) -> '$0.99'",
        "present_invoice(hidden zero-total invoice) -> '$0.00'",
    ],
    "expected_solve_path": [
        "inspect src/presenters/invoice_presenter.py",
        "inspect src/helpers/currency.py",
        "inspect tests/test_invoice_presenter.py and logs/pytest_medium.log",
        "patch src/helpers/currency.py",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Hidden presenter/helper cases catch patches that hardcode the visible '$12.05' output.",
        "Structure checks require the presenter to keep calling the helper module.",
        "Validation rejects constant-return helper implementations.",
    ],
    "constraints": [
        "Presenter output keys and ordering expectations must stay stable.",
        "Fix the helper/root cause instead of editing tests.",
        "Monetary formatting must always render exactly two decimals.",
    ],
    "max_steps": 12,
}


_TASK_HARD = {
    "task_id": "task_hard_maintenance",
    "task_type": "hard",
    "task_description": (
        "Two formatter modules still duplicate the same display-name cleanup "
        "logic, and a dormant shared helper has drifted out of date. Refactor "
        "the customer and vendor formatters to use a single shared helper "
        "without changing any existing behavior."
    ),
    "repo_summary": (
        "Shared formatting layer for partner records used by customer success "
        "and vendor operations tooling."
    ),
    "files": {
        "src/formatters/shared.py": (
            "def normalize_display_name(parts):\n"
            "    return ' '.join(parts)\n"
        ),
        "src/formatters/customer_names.py": (
            "def format_customer_name(record: dict) -> str:\n"
            "    parts = [record.get('first_name', ''), record.get('last_name', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return ' '.join(cleaned)\n"
        ),
        "src/formatters/vendor_names.py": (
            "def format_vendor_name(record: dict) -> str:\n"
            "    parts = [record.get('contact_first', ''), record.get('contact_last', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return ' '.join(cleaned)\n"
        ),
        "tests/test_party_formatters.py": (
            "from src.formatters.customer_names import format_customer_name\n"
            "from src.formatters.vendor_names import format_vendor_name\n"
            "\n"
            "def test_format_customer_name():\n"
            "    assert format_customer_name({'first_name': '  maya', 'last_name': 'SINGH  '}) == 'Maya Singh'\n"
            "    assert format_customer_name({'first_name': '  maya', 'last_name': ''}) == 'Maya'\n"
            "\n"
            "def test_format_vendor_name():\n"
            "    assert format_vendor_name({'contact_first': 'ops', 'contact_last': 'TEAM'}) == 'Ops Team'\n"
            "    assert format_vendor_name({'contact_first': '', 'contact_last': 'support'}) == 'Support'\n"
        ),
        "notes/refactor_ticket.md": (
            "# Refactor ticket\n"
            "\n"
            "- Consolidate duplicated display-name cleanup used by customer and vendor formatters.\n"
            "- Keep public function signatures stable.\n"
            "- Preserve title casing and blank-part handling.\n"
        ),
    },
    "important_files": [
        "src/formatters/customer_names.py",
        "src/formatters/vendor_names.py",
        "src/formatters/shared.py",
        "tests/test_party_formatters.py",
        "notes/refactor_ticket.md",
    ],
    "relevant_files": [
        "src/formatters/customer_names.py",
        "src/formatters/vendor_names.py",
        "src/formatters/shared.py",
        "tests/test_party_formatters.py",
        "notes/refactor_ticket.md",
    ],
    "patch_targets": [
        "src/formatters/shared.py",
        "src/formatters/customer_names.py",
        "src/formatters/vendor_names.py",
    ],
    "failing_checks": [
        "duplication audit: customer_names.py and vendor_names.py contain drift-prone cleanup logic",
        "shared helper must preserve existing display-name behavior",
    ],
    "visible_checks": [
        "format_customer_name({'first_name': '  maya', 'last_name': 'SINGH  '}) -> 'Maya Singh'",
        "format_customer_name({'first_name': '  maya', 'last_name': ''}) -> 'Maya'",
        "format_vendor_name({'contact_first': 'ops', 'contact_last': 'TEAM'}) -> 'Ops Team'",
        "format_vendor_name({'contact_first': '', 'contact_last': 'support'}) -> 'Support'",
    ],
    "hidden_checks": [
        "format_customer_name({'first_name': '', 'last_name': ' support  '}) -> 'Support'",
        "format_customer_name({'first_name': 'qa', 'last_name': '  lead '}) -> 'Qa Lead'",
        "format_vendor_name({'contact_first': '  account', 'contact_last': ' lead  '}) -> 'Account Lead'",
        "format_vendor_name({'contact_first': 'multi', 'contact_last': ''}) -> 'Multi'",
        "Shared helper must own cleanup logic; wrappers must stop duplicating it.",
    ],
    "expected_solve_path": [
        "inspect both formatter modules, shared helper, tests, and refactor ticket",
        "patch src/formatters/shared.py to own cleanup behavior",
        "patch src/formatters/customer_names.py to delegate to shared helper",
        "patch src/formatters/vendor_names.py to delegate to shared helper",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Near-perfect scores require both preserved behavior and genuine structural cleanup.",
        "Superficial wrapper changes still fail integrity checks if duplicated cleanup remains inline.",
        "Hidden regression cases cover additional spacing and blank-field variants not shown in the visible tests.",
    ],
    "constraints": [
        "Keep public formatter function names unchanged.",
        "Centralize cleanup in src/formatters/shared.py.",
        "Behavior must remain unchanged for both customer and vendor records.",
    ],
    "max_steps": 15,
}


TASKS: List[Dict] = [_TASK_EASY, _TASK_MEDIUM, _TASK_HARD]


def get_task(task_id: str) -> dict:
    """Return a task definition by its ID. Raises ValueError if not found."""
    for task in TASKS:
        if task["task_id"] == task_id:
            return task
    raise ValueError(f"Unknown task_id: {task_id}")


def list_task_ids() -> List[str]:
    """Return the ordered list of all task IDs."""
    return [task["task_id"] for task in TASKS]

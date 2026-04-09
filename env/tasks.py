"""Deterministic task definitions for the SoftwareLifecycleEnv benchmark.

The public task IDs stay stable for validator compatibility, but the task
content aims to reflect realistic software-lifecycle work:

* easy   -> testing / diagnosis-first CI preview failure
* medium -> debugging / root-cause repair across endpoint, presenter, helper, and config
* hard   -> maintenance / shared-helper refactor with behavior preservation
"""

from __future__ import annotations

from typing import Dict, List


_TASK_EASY = {
    "task_id": "task_easy_testing",
    "task_type": "easy",
    "workflow_focus": "testing",
    "task_description": (
        "A GitHub Actions preview-deploy check is failing because generated "
        "preview URLs no longer match the router contract. Inspect the router, "
        "slug builder, settings, failing test, and CI log. Fix the bug so "
        "preview URLs are built from branch names and ticket IDs using the "
        "same separator and normalization rules expected by routing."
    ),
    "repo_summary": (
        "Release-preview tooling package used by CI to publish temporary "
        "preview URLs for feature and hotfix branches."
    ),
    "files": {
        "src/release_preview/settings.py": (
            "PREVIEW_SEPARATOR = '-'\n"
            "PREVIEW_DOMAIN = 'preview.internal.example'\n"
            "RESERVED_BRANCH_PREFIXES = {'feature', 'bugfix', 'hotfix', 'release'}\n"
        ),
        "src/release_preview/slug_builder.py": (
            "from src.release_preview.settings import PREVIEW_SEPARATOR, RESERVED_BRANCH_PREFIXES\n"
            "\n"
            "def build_preview_slug(branch_name: str, ticket_id: str) -> str:\n"
            "    normalized = branch_name.strip().lower().replace('/', ' ')\n"
            "    normalized = normalized.replace('_', ' ')\n"
            "    tokens = [token for token in normalized.split(' ') if token]\n"
            "    if tokens and tokens[0] in RESERVED_BRANCH_PREFIXES:\n"
            "        tokens = tokens[1:]\n"
            "    ticket_token = ticket_id.strip().lower()\n"
            "    pieces = [ticket_token] + tokens if ticket_token else list(tokens)\n"
            "    return '_'.join(pieces)\n"
        ),
        "src/release_preview/router.py": (
            "from src.release_preview.settings import PREVIEW_DOMAIN\n"
            "from src.release_preview.slug_builder import build_preview_slug\n"
            "\n"
            "def build_preview_url(branch_name: str, ticket_id: str) -> str:\n"
            "    slug = build_preview_slug(branch_name, ticket_id)\n"
            "    return f'https://{PREVIEW_DOMAIN}/{slug}'\n"
        ),
        "tests/test_preview_router.py": (
            "from src.release_preview.router import build_preview_url\n"
            "\n"
            "def test_build_preview_url_matches_router_contract():\n"
            "    assert build_preview_url('feature/Auth_Reset', 'WEB-401') == 'https://preview.internal.example/web-401-auth-reset'\n"
            "    assert build_preview_url(' hotfix / Billing__retry ', 'OPS-9') == 'https://preview.internal.example/ops-9-billing-retry'\n"
            "    assert build_preview_url('release/May_Cutover', 'REL-77') == 'https://preview.internal.example/rel-77-may-cutover'\n"
        ),
        "logs/github_actions_preview.log": (
            "Run pytest tests/test_preview_router.py -q\n"
            "E AssertionError: assert 'https://preview.internal.example/web-401_auth_reset' == 'https://preview.internal.example/web-401-auth-reset'\n"
            "E preview router contract expects PREVIEW_SEPARATOR from src/release_preview/settings.py\n"
            "tests/test_preview_router.py:4: AssertionError\n"
        ),
        "ci/job_summary.txt": (
            "workflow: preview-deploy\n"
            "status: failed\n"
            "failing_check: tests/test_preview_router.py::test_build_preview_url_matches_router_contract\n"
            "blocked_release: 2026.04.09-preview\n"
            "note: preview URLs must follow the router contract before release promotion can continue\n"
        ),
        "notes/release_comment.md": (
            "## Release comment\n"
            "\n"
            "- Preview deploys were moved behind the shared router contract last sprint.\n"
            "- QA depends on ticket-prefixed preview URLs to map failed smoke checks back to release branches.\n"
            "- The preview slug should still remove workflow prefixes such as `feature/` and `hotfix/`.\n"
        ),
        "docs/preview_routing.md": (
            "# Preview routing contract\n"
            "\n"
            "- Preview URLs must use PREVIEW_SEPARATOR from settings.\n"
            "- Branch workflow prefixes like feature/ or hotfix/ are not part of the final preview slug.\n"
            "- Ticket IDs remain at the front of the slug so CI and router logs can be correlated.\n"
        ),
    },
    "important_files": [
        "src/release_preview/router.py",
        "src/release_preview/slug_builder.py",
        "src/release_preview/settings.py",
        "tests/test_preview_router.py",
        "logs/github_actions_preview.log",
        "ci/job_summary.txt",
        "notes/release_comment.md",
        "docs/preview_routing.md",
    ],
    "relevant_files": [
        "src/release_preview/router.py",
        "src/release_preview/slug_builder.py",
        "src/release_preview/settings.py",
        "tests/test_preview_router.py",
        "logs/github_actions_preview.log",
        "ci/job_summary.txt",
        "notes/release_comment.md",
        "docs/preview_routing.md",
    ],
    "inspection_buckets": {
        "symptom": [
            "tests/test_preview_router.py",
            "logs/github_actions_preview.log",
            "ci/job_summary.txt",
        ],
        "implementation": [
            "src/release_preview/router.py",
            "src/release_preview/slug_builder.py",
        ],
        "policy": [
            "src/release_preview/settings.py",
            "notes/release_comment.md",
            "docs/preview_routing.md",
        ],
    },
    "patch_targets": ["src/release_preview/slug_builder.py"],
    "failing_checks": [
        "tests/test_preview_router.py::test_build_preview_url_matches_router_contract",
        "preview URLs must use PREVIEW_SEPARATOR from settings and remove workflow prefixes",
    ],
    "visible_checks": [
        "build_preview_url('feature/Auth_Reset', 'WEB-401') -> 'https://preview.internal.example/web-401-auth-reset'",
        "build_preview_url(' hotfix / Billing__retry ', 'OPS-9') -> 'https://preview.internal.example/ops-9-billing-retry'",
        "build_preview_url('release/May_Cutover', 'REL-77') -> 'https://preview.internal.example/rel-77-may-cutover'",
    ],
    "hidden_checks": [
        "build_preview_url('bugfix///API__Client', 'CORE-11') -> 'https://preview.internal.example/core-11-api-client'",
        "build_preview_url('feature / data_SYNC / nightly', 'PLAT-204') -> 'https://preview.internal.example/plat-204-data-sync-nightly'",
        "build_preview_url('release/Sprint_24', 'REL-24') -> 'https://preview.internal.example/rel-24-sprint-24'",
        "build_preview_url('', 'OPS-1') -> 'https://preview.internal.example/ops-1'",
    ],
    "expected_solve_path": [
        "inspect tests/test_preview_router.py, logs/github_actions_preview.log, and ci/job_summary.txt to diagnose the failing contract",
        "inspect src/release_preview/router.py and src/release_preview/slug_builder.py",
        "inspect src/release_preview/settings.py, notes/release_comment.md, and docs/preview_routing.md",
        "patch src/release_preview/slug_builder.py",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Hidden branch-name variants catch fixes that only hardcode one CI example.",
        "Validation rejects constant-return and visible-answer patches.",
        "The API exposes only visible validation details; hidden regressions remain internal to grading.",
    ],
    "constraints": [
        "Preserve lowercase normalization.",
        "Use PREVIEW_SEPARATOR from settings for the final slug.",
        "Treat '/' and '_' as separators and strip reserved workflow prefixes.",
    ],
    "max_steps": 12,
}


_TASK_MEDIUM = {
    "task_id": "task_medium_debugging",
    "task_type": "medium",
    "workflow_focus": "debugging",
    "task_description": (
        "The billing admin API is returning the wrong `amount_due` string in "
        "its invoice response. The symptom shows up in the endpoint test, but "
        "the root cause is deeper in the formatting stack. Inspect the "
        "endpoint, presenter, helper, config modules, and failure log, then "
        "restore the correct API payload."
    ),
    "repo_summary": (
        "Billing service code where admin API payloads and dashboard summary "
        "cards share some formatting helpers but not the same policy."
    ),
    "files": {
        "src/config/api_formatting.py": (
            "CURRENCY_SYMBOL = '$'\n"
            "AMOUNT_DECIMAL_PLACES = 2\n"
        ),
        "src/config/dashboard_formatting.py": (
            "CURRENCY_SYMBOL = '$'\n"
            "SUMMARY_ROUNDING_MODE = 'whole_dollars'\n"
        ),
        "src/helpers/currency.py": (
            "from src.config.dashboard_formatting import CURRENCY_SYMBOL, SUMMARY_ROUNDING_MODE\n"
            "\n"
            "def format_cents(cents: int) -> str:\n"
            "    dollars = cents / 100\n"
            "    if SUMMARY_ROUNDING_MODE == 'whole_dollars':\n"
            "        return f'{CURRENCY_SYMBOL}{dollars:.0f}'\n"
            "    return f'{CURRENCY_SYMBOL}{dollars:.2f}'\n"
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
        "src/api/invoice_endpoint.py": (
            "from src.presenters.invoice_presenter import present_invoice\n"
            "\n"
            "def serialize_invoice_response(invoice: dict) -> dict:\n"
            "    return {\n"
            "        'invoice': present_invoice(invoice),\n"
            "        'generated_by': 'billing-admin-api',\n"
            "    }\n"
        ),
        "tests/test_invoice_endpoint.py": (
            "from src.api.invoice_endpoint import serialize_invoice_response\n"
            "\n"
            "def test_serialize_invoice_response_formats_amount_due_for_api_clients():\n"
            "    invoice = {\n"
            "        'customer': '  Acme Corp  ',\n"
            "        'amount_due_cents': 1205,\n"
            "        'line_items': ['support', 'monitoring'],\n"
            "        'status': 'past_due',\n"
            "    }\n"
            "    assert serialize_invoice_response(invoice) == {\n"
            "        'invoice': {\n"
            "            'customer': 'Acme Corp',\n"
            "            'amount_due': '$12.05',\n"
            "            'line_items': ['monitoring', 'support'],\n"
            "            'status': 'PAST_DUE',\n"
            "        },\n"
            "        'generated_by': 'billing-admin-api',\n"
            "    }\n"
        ),
        "logs/api_serialization.log": (
            "2026-04-09T09:15:12Z billing-admin-api ERROR invoice serialization mismatch\n"
            "expected amount_due '$12.05' but rendered '$12'\n"
            "hint: API payloads should use src/config/api_formatting.py, not dashboard summary rounding\n"
            "tests/test_invoice_endpoint.py:5: AssertionError\n"
        ),
        "logs/request_trace.log": (
            "request_id=4f2a7 billing-admin-api GET /admin/invoices/INV-204\n"
            "serialize_invoice_response -> present_invoice -> format_cents\n"
            "amount_due_cents=1205 rendered_amount='$12'\n"
            "dashboard summary service currently renders whole dollars by design\n"
        ),
        "git/last_change.txt": (
            "commit 31f6e2b\n"
            "author: platform-ops\n"
            "message: reuse dashboard summary currency helper in admin billing API\n"
            "note: intended to reduce formatting duplication across internal surfaces\n"
        ),
        "notes/incident_summary.md": (
            "## Incident summary\n"
            "\n"
            "- Customer success reported that overdue invoices in the admin API are losing cents.\n"
            "- Dashboard summary cards are still acceptable with whole-dollar rounding.\n"
            "- Reconciliation exports and API clients require exact cents.\n"
        ),
        "docs/amount_formatting.md": (
            "# Amount formatting notes\n"
            "\n"
            "- Admin API responses must preserve cents for financial reconciliation.\n"
            "- Dashboard cards may round to whole dollars for compact summaries.\n"
            "- Shared helpers used by the API should import src/config/api_formatting.py.\n"
        ),
    },
    "important_files": [
        "src/api/invoice_endpoint.py",
        "src/presenters/invoice_presenter.py",
        "src/helpers/currency.py",
        "src/config/api_formatting.py",
        "src/config/dashboard_formatting.py",
        "tests/test_invoice_endpoint.py",
        "logs/api_serialization.log",
        "logs/request_trace.log",
        "git/last_change.txt",
        "notes/incident_summary.md",
        "docs/amount_formatting.md",
    ],
    "relevant_files": [
        "src/api/invoice_endpoint.py",
        "src/presenters/invoice_presenter.py",
        "src/helpers/currency.py",
        "src/config/api_formatting.py",
        "src/config/dashboard_formatting.py",
        "tests/test_invoice_endpoint.py",
        "logs/api_serialization.log",
        "logs/request_trace.log",
        "git/last_change.txt",
        "notes/incident_summary.md",
        "docs/amount_formatting.md",
    ],
    "inspection_buckets": {
        "symptom": [
            "src/api/invoice_endpoint.py",
            "tests/test_invoice_endpoint.py",
            "logs/api_serialization.log",
            "logs/request_trace.log",
            "notes/incident_summary.md",
        ],
        "flow": [
            "src/presenters/invoice_presenter.py",
        ],
        "root_cause": [
            "src/helpers/currency.py",
        ],
        "policy": [
            "src/config/api_formatting.py",
            "src/config/dashboard_formatting.py",
            "git/last_change.txt",
            "docs/amount_formatting.md",
        ],
    },
    "patch_targets": ["src/helpers/currency.py"],
    "failing_checks": [
        "tests/test_invoice_endpoint.py::test_serialize_invoice_response_formats_amount_due_for_api_clients",
        "amount_due should use API formatting rules, not dashboard summary rounding",
    ],
    "visible_checks": [
        "format_cents(1205) -> '$12.05'",
        "serialize_invoice_response(primary visible invoice) -> expected API payload",
    ],
    "hidden_checks": [
        "format_cents(5) -> '$0.05'",
        "format_cents(2500) -> '$25.00'",
        "format_cents(101) -> '$1.01'",
        "serialize_invoice_response(hidden 99-cent invoice) -> '$0.99'",
        "serialize_invoice_response(hidden zero-total invoice) -> '$0.00'",
    ],
    "expected_solve_path": [
        "inspect the failing endpoint test, API log, request trace, and incident note to understand the symptom",
        "inspect src/api/invoice_endpoint.py and src/presenters/invoice_presenter.py",
        "inspect src/helpers/currency.py",
        "inspect src/config/api_formatting.py, src/config/dashboard_formatting.py, git/last_change.txt, and docs/amount_formatting.md",
        "patch src/helpers/currency.py",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Hidden endpoint/helper cases catch patches that only hardcode the visible '$12.05' output.",
        "Structure checks require the helper to follow the API config path instead of dashboard-only rounding.",
        "Validation rejects constant-return and visible-case branching implementations.",
    ],
    "constraints": [
        "Endpoint response shape and presenter output keys must stay stable.",
        "Fix the helper/root cause instead of editing tests or endpoint literals.",
        "API formatting must always render exactly two decimals using src/config/api_formatting.py.",
    ],
    "max_steps": 15,
}


_TASK_HARD = {
    "task_id": "task_hard_maintenance",
    "task_type": "hard",
    "workflow_focus": "maintenance",
    "task_description": (
        "Customer API payload assembly and vendor export row generation still "
        "duplicate the same display-name cleanup logic, and the shared helper "
        "has drifted out of date. Refactor both modules to use a single shared "
        "normalizer without changing their current output contracts."
    ),
    "repo_summary": (
        "Partner data formatting layer shared by the customer-success API and "
        "vendor operations export pipeline."
    ),
    "files": {
        "src/shared/display_name.py": (
            "def normalize_display_name(parts):\n"
            "    return ' '.join(parts)\n"
        ),
        "src/api/customer_payload.py": (
            "def build_customer_payload(record: dict) -> dict:\n"
            "    parts = [record.get('first_name', ''), record.get('last_name', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return {\n"
            "        'display_name': ' '.join(cleaned),\n"
            "        'account_tier': record.get('account_tier', '').lower(),\n"
            "        'status': record.get('status', '').lower(),\n"
            "    }\n"
        ),
        "src/exports/vendor_rows.py": (
            "def build_vendor_row(record: dict) -> dict:\n"
            "    parts = [record.get('contact_first', ''), record.get('contact_last', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return {\n"
            "        'display_name': ' '.join(cleaned),\n"
            "        'vendor_code': record.get('vendor_code', '').upper(),\n"
            "        'active': 'yes' if record.get('active') else 'no',\n"
            "    }\n"
        ),
        "tests/test_partner_outputs.py": (
            "from src.api.customer_payload import build_customer_payload\n"
            "from src.exports.vendor_rows import build_vendor_row\n"
            "\n"
            "def test_build_customer_payload():\n"
            "    assert build_customer_payload({'first_name': '  maya', 'last_name': 'SINGH  ', 'account_tier': 'ENTERPRISE', 'status': 'ACTIVE'}) == {\n"
            "        'display_name': 'Maya Singh',\n"
            "        'account_tier': 'enterprise',\n"
            "        'status': 'active',\n"
            "    }\n"
            "    assert build_customer_payload({'first_name': '  maya', 'last_name': '', 'account_tier': 'SMB', 'status': 'TRIAL'}) == {\n"
            "        'display_name': 'Maya',\n"
            "        'account_tier': 'smb',\n"
            "        'status': 'trial',\n"
            "    }\n"
            "\n"
            "def test_build_vendor_row():\n"
            "    assert build_vendor_row({'contact_first': 'ops', 'contact_last': 'TEAM', 'vendor_code': 'v-14', 'active': True}) == {\n"
            "        'display_name': 'Ops Team',\n"
            "        'vendor_code': 'V-14',\n"
            "        'active': 'yes',\n"
            "    }\n"
            "    assert build_vendor_row({'contact_first': '', 'contact_last': 'support', 'vendor_code': 'help-2', 'active': False}) == {\n"
            "        'display_name': 'Support',\n"
            "        'vendor_code': 'HELP-2',\n"
            "        'active': 'no',\n"
            "    }\n"
        ),
        "logs/duplication_audit.log": (
            "duplication-audit: src/api/customer_payload.py and src/exports/vendor_rows.py share identical display-name cleanup logic\n"
            "maintenance-risk: future formatting changes could drift between API payloads and vendor exports\n"
            "recommendation: move cleanup to src/shared/display_name.py and keep current output contracts stable\n"
        ),
        "audit/duplication_report.txt": (
            "duplicate block detected in 2 files:\n"
            "- src/api/customer_payload.py\n"
            "- src/exports/vendor_rows.py\n"
            "risk: incompatible display_name behavior after future formatting changes\n"
        ),
        "docs/partner_output_contract.md": (
            "# Partner output contract\n"
            "\n"
            "- Customer payloads expose display_name, account_tier, and status.\n"
            "- Vendor export rows expose display_name, vendor_code, and active.\n"
            "- Shared display-name cleanup must preserve title casing and blank-field handling across both outputs.\n"
        ),
        "notes/tech_debt_ticket.md": (
            "# Tech debt ticket\n"
            "\n"
            "- The customer-success API and vendor export path still own separate copies of display-name cleanup.\n"
            "- This has already caused one drift incident in staging.\n"
            "- Refactor toward the shared helper without altering either public output contract.\n"
        ),
        "review/refactor_note.md": (
            "Review note:\n"
            "- Please centralize display-name normalization before the next partner-data rollout.\n"
            "- Keep `account_tier`, `status`, `vendor_code`, and `active` behavior exactly as-is.\n"
            "- Avoid cosmetic-only changes that leave cleanup duplicated in both consumers.\n"
        ),
        "notes/refactor_ticket.md": (
            "# Refactor ticket\n"
            "\n"
            "- Consolidate duplicated display-name cleanup used by the customer API payload builder and vendor export row builder.\n"
            "- Keep public function signatures and response shapes stable.\n"
            "- Preserve title casing, blank-part handling, and other field formatting.\n"
        ),
    },
    "important_files": [
        "src/api/customer_payload.py",
        "src/exports/vendor_rows.py",
        "src/shared/display_name.py",
        "tests/test_partner_outputs.py",
        "logs/duplication_audit.log",
        "audit/duplication_report.txt",
        "docs/partner_output_contract.md",
        "notes/tech_debt_ticket.md",
        "review/refactor_note.md",
        "notes/refactor_ticket.md",
    ],
    "relevant_files": [
        "src/api/customer_payload.py",
        "src/exports/vendor_rows.py",
        "src/shared/display_name.py",
        "tests/test_partner_outputs.py",
        "logs/duplication_audit.log",
        "audit/duplication_report.txt",
        "docs/partner_output_contract.md",
        "notes/tech_debt_ticket.md",
        "review/refactor_note.md",
        "notes/refactor_ticket.md",
    ],
    "inspection_buckets": {
        "consumers": [
            "src/api/customer_payload.py",
            "src/exports/vendor_rows.py",
        ],
        "shared_logic": [
            "src/shared/display_name.py",
        ],
        "contracts": [
            "tests/test_partner_outputs.py",
            "logs/duplication_audit.log",
            "audit/duplication_report.txt",
            "docs/partner_output_contract.md",
            "notes/tech_debt_ticket.md",
            "review/refactor_note.md",
            "notes/refactor_ticket.md",
        ],
    },
    "patch_targets": [
        "src/shared/display_name.py",
        "src/api/customer_payload.py",
        "src/exports/vendor_rows.py",
    ],
    "failing_checks": [
        "duplication audit: customer_payload.py and vendor_rows.py contain drift-prone display-name cleanup logic",
        "shared helper must preserve API and export output behavior",
    ],
    "visible_checks": [
        "build_customer_payload(primary customer record) -> expected API payload",
        "build_customer_payload(customer blank-last-name record) -> expected API payload",
        "build_vendor_row(primary vendor record) -> expected export row",
        "build_vendor_row(vendor blank-first-name record) -> expected export row",
    ],
    "hidden_checks": [
        "build_customer_payload(customer support-contact record) -> expected API payload",
        "build_customer_payload(customer qa-lead record) -> expected API payload",
        "build_vendor_row(vendor account-lead record) -> expected export row",
        "build_vendor_row(vendor blank-last-name record) -> expected export row",
        "Shared helper must own cleanup logic; wrappers must stop duplicating it.",
    ],
    "expected_solve_path": [
        "inspect the duplication audit, tech-debt ticket, review note, refactor ticket, and output contract",
        "inspect the customer payload builder, vendor export builder, and shared helper",
        "inspect tests/test_partner_outputs.py to confirm behavioral expectations",
        "patch src/shared/display_name.py to own cleanup behavior",
        "patch src/api/customer_payload.py and src/exports/vendor_rows.py to delegate cleanup",
        "run_tests",
        "submit",
    ],
    "anti_gaming_notes": [
        "Near-perfect scores require both preserved behavior and genuine structural cleanup.",
        "Superficial wrapper changes still fail integrity checks if duplicated cleanup remains inline.",
        "Hidden regression cases cover additional spacing and blank-field variants not shown in the visible tests.",
    ],
    "constraints": [
        "Keep public function names and output shapes unchanged.",
        "Centralize display-name cleanup in src/shared/display_name.py.",
        "Behavior must remain unchanged for both customer API payloads and vendor export rows.",
    ],
    "max_steps": 16,
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

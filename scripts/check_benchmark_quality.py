#!/usr/bin/env python3
"""Local quality check for SoftwareLifecycleEnv.

Runs:
* initial validator snapshots
* one anti-gaming attempt per task
* one strong reference solve path per task
* score and reward range verification
* public-vs-hidden validation surface checks
"""

from __future__ import annotations

import pathlib
import sys
from typing import Dict, Iterable, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.environment import SoftwareLifecycleEnv
from env.models import Action, ActionType
from env.tasks import TASKS, get_task
from env.validation import validate_task

PREVIOUS_MEDIUM_CHEAT_SCORE = 0.55


def inspect(path: str) -> Action:
    return Action(action_type=ActionType.INSPECT_FILE, target_file=path)


def patch(path: str, content: str) -> Action:
    return Action(
        action_type=ActionType.APPLY_PATCH,
        target_file=path,
        patch_content=content,
    )


def run_tests() -> Action:
    return Action(action_type=ActionType.RUN_TESTS)


def submit() -> Action:
    return Action(action_type=ActionType.SUBMIT)


REFERENCE_SOLUTIONS: Dict[str, List[Action]] = {
    "task_easy_testing": [
        inspect("tests/test_preview_router.py"),
        inspect("logs/github_actions_preview.log"),
        inspect("ci/job_summary.txt"),
        inspect("src/release_preview/router.py"),
        inspect("src/release_preview/slug_builder.py"),
        inspect("src/release_preview/settings.py"),
        inspect("notes/release_comment.md"),
        inspect("docs/preview_routing.md"),
        patch(
            "src/release_preview/slug_builder.py",
            "from src.release_preview.settings import PREVIEW_SEPARATOR, RESERVED_BRANCH_PREFIXES\n"
            "\n"
            "def build_preview_slug(branch_name: str, ticket_id: str) -> str:\n"
            "    normalized = branch_name.strip().lower().replace('/', ' ')\n"
            "    normalized = normalized.replace('_', ' ')\n"
            "    tokens = [token for token in normalized.split(' ') if token]\n"
            "    if tokens and tokens[0] in RESERVED_BRANCH_PREFIXES:\n"
            "        tokens = tokens[1:]\n"
            "    ticket_token = ticket_id.strip().lower()\n"
            "    parts = [ticket_token] + tokens if ticket_token else list(tokens)\n"
            "    return PREVIEW_SEPARATOR.join(parts)\n",
        ),
        run_tests(),
        submit(),
    ],
    "task_medium_debugging": [
        inspect("tests/test_invoice_endpoint.py"),
        inspect("logs/api_serialization.log"),
        inspect("logs/request_trace.log"),
        inspect("notes/incident_summary.md"),
        inspect("src/api/invoice_endpoint.py"),
        inspect("src/presenters/invoice_presenter.py"),
        inspect("src/helpers/currency.py"),
        inspect("src/config/api_formatting.py"),
        inspect("src/config/dashboard_formatting.py"),
        inspect("git/last_change.txt"),
        inspect("docs/amount_formatting.md"),
        patch(
            "src/helpers/currency.py",
            "from src.config.api_formatting import CURRENCY_SYMBOL, AMOUNT_DECIMAL_PLACES\n"
            "\n"
            "def format_cents(cents: int) -> str:\n"
            "    dollars = cents / 100\n"
            "    return f'{CURRENCY_SYMBOL}{dollars:.{AMOUNT_DECIMAL_PLACES}f}'\n",
        ),
        run_tests(),
        submit(),
    ],
    "task_hard_maintenance": [
        inspect("logs/duplication_audit.log"),
        inspect("audit/duplication_report.txt"),
        inspect("docs/partner_output_contract.md"),
        inspect("notes/tech_debt_ticket.md"),
        inspect("review/refactor_note.md"),
        inspect("notes/refactor_ticket.md"),
        inspect("src/api/customer_payload.py"),
        inspect("src/exports/vendor_rows.py"),
        inspect("src/shared/display_name.py"),
        inspect("tests/test_partner_outputs.py"),
        patch(
            "src/shared/display_name.py",
            "def normalize_display_name(parts):\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return ' '.join(cleaned)\n",
        ),
        patch(
            "src/api/customer_payload.py",
            "from src.shared.display_name import normalize_display_name\n"
            "\n"
            "def build_customer_payload(record: dict) -> dict:\n"
            "    parts = [record.get('first_name', ''), record.get('last_name', '')]\n"
            "    return {\n"
            "        'display_name': normalize_display_name(parts),\n"
            "        'account_tier': record.get('account_tier', '').lower(),\n"
            "        'status': record.get('status', '').lower(),\n"
            "    }\n",
        ),
        patch(
            "src/exports/vendor_rows.py",
            "from src.shared.display_name import normalize_display_name\n"
            "\n"
            "def build_vendor_row(record: dict) -> dict:\n"
            "    parts = [record.get('contact_first', ''), record.get('contact_last', '')]\n"
            "    return {\n"
            "        'display_name': normalize_display_name(parts),\n"
            "        'vendor_code': record.get('vendor_code', '').upper(),\n"
            "        'active': 'yes' if record.get('active') else 'no',\n"
            "    }\n",
        ),
        run_tests(),
        submit(),
    ],
}


ANTI_GAMING_ATTEMPTS: Dict[str, List[Action]] = {
    "task_easy_testing": [
        inspect("src/release_preview/slug_builder.py"),
        patch(
            "src/release_preview/slug_builder.py",
            "from src.release_preview.settings import PREVIEW_SEPARATOR, RESERVED_BRANCH_PREFIXES\n"
            "\n"
            "def build_preview_slug(branch_name: str, ticket_id: str) -> str:\n"
            "    normalized = branch_name.strip().lower().replace('/', ' ')\n"
            "    normalized = normalized.replace('_', ' ')\n"
            "    tokens = [token for token in normalized.split(' ') if token]\n"
            "    ticket_token = ticket_id.strip().lower()\n"
            "    pieces = [ticket_token] + tokens if ticket_token else list(tokens)\n"
            "    return PREVIEW_SEPARATOR.join(pieces)\n",
        ),
        run_tests(),
        submit(),
    ],
    "task_medium_debugging": [
        inspect("src/helpers/currency.py"),
        patch(
            "src/helpers/currency.py",
            "from src.config.api_formatting import CURRENCY_SYMBOL, AMOUNT_DECIMAL_PLACES\n"
            "\n"
            "def format_cents(cents: int) -> str:\n"
            "    if cents == 1205:\n"
            "        return f'{CURRENCY_SYMBOL}12.05'\n"
            "    dollars = cents / 100\n"
            "    return f'{CURRENCY_SYMBOL}{dollars:.0f}'\n",
        ),
        run_tests(),
        submit(),
    ],
    "task_hard_maintenance": [
        inspect("src/api/customer_payload.py"),
        inspect("src/exports/vendor_rows.py"),
        inspect("src/shared/display_name.py"),
        patch(
            "src/api/customer_payload.py",
            "from src.shared.display_name import normalize_display_name\n"
            "\n"
            "def build_customer_payload(record: dict) -> dict:\n"
            "    parts = [record.get('first_name', ''), record.get('last_name', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return {\n"
            "        'display_name': normalize_display_name(cleaned),\n"
            "        'account_tier': record.get('account_tier', '').lower(),\n"
            "        'status': record.get('status', '').lower(),\n"
            "    }\n",
        ),
        patch(
            "src/exports/vendor_rows.py",
            "from src.shared.display_name import normalize_display_name\n"
            "\n"
            "def build_vendor_row(record: dict) -> dict:\n"
            "    parts = [record.get('contact_first', ''), record.get('contact_last', '')]\n"
            "    cleaned = [part.strip().title() for part in parts if part and part.strip()]\n"
            "    return {\n"
            "        'display_name': normalize_display_name(cleaned),\n"
            "        'vendor_code': record.get('vendor_code', '').upper(),\n"
            "        'active': 'yes' if record.get('active') else 'no',\n"
            "    }\n",
        ),
        run_tests(),
        submit(),
    ],
}


def run_episode(task_id: str, actions: Iterable[Action]) -> dict:
    env = SoftwareLifecycleEnv()
    env.reset(task_id)
    rewards: List[float] = []
    last_result = None
    for action in actions:
        last_result = env.step(action)
        rewards.append(last_result.reward)
    state = env.state()
    full_report = validate_task(get_task(task_id), state["files"])
    return {
        "rewards": rewards,
        "final_score": (last_result.info.get("final_score") if last_result else None),
        "state": state,
        "public_validation": state["validation_report"],
        "full_validation": full_report,
    }


def ensure_open_interval(values: Iterable[float], label: str) -> None:
    violations = [value for value in values if not (0 < value < 1)]
    if violations:
        raise AssertionError(f"{label} out of range: {violations}")


def ensure_hidden_checks_stay_hidden(public_validation: dict) -> None:
    exposed_checks = public_validation.get("checks", [])
    if any(check.get("visibility") != "visible" for check in exposed_checks):
        raise AssertionError("Public validation surface leaked a hidden check.")


def main() -> None:
    all_scores: List[float] = []
    all_rewards: List[float] = []

    print("[QUALITY] starting benchmark quality verification")
    for task in TASKS:
        task_id = task["task_id"]
        initial_report = validate_task(task, task["files"])
        cheat_run = run_episode(task_id, ANTI_GAMING_ATTEMPTS[task_id])
        solve_run = run_episode(task_id, REFERENCE_SOLUTIONS[task_id])

        ensure_open_interval(
            [cheat_run["final_score"], solve_run["final_score"]],
            f"{task_id} final scores",
        )
        ensure_open_interval(cheat_run["rewards"], f"{task_id} anti-gaming rewards")
        ensure_open_interval(solve_run["rewards"], f"{task_id} solve-path rewards")
        ensure_hidden_checks_stay_hidden(cheat_run["public_validation"])
        ensure_hidden_checks_stay_hidden(solve_run["public_validation"])

        all_scores.extend([cheat_run["final_score"], solve_run["final_score"]])
        all_rewards.extend(cheat_run["rewards"])
        all_rewards.extend(solve_run["rewards"])

        cheat_hidden_failures = cheat_run["public_validation"].get("hidden_failed_checks", 0)
        solve_hidden_failures = solve_run["public_validation"].get("hidden_failed_checks", 0)
        print(
            "[QUALITY]",
            f"task={task_id}",
            f"initial_overall={initial_report.overall_score:.2f}",
            f"cheat_score={cheat_run['final_score']:.2f}",
            f"cheat_hidden_failures={cheat_hidden_failures}",
            f"solve_score={solve_run['final_score']:.2f}",
            f"solve_hidden_failures={solve_hidden_failures}",
            f"solve_rewards={','.join(f'{reward:.2f}' for reward in solve_run['rewards'])}",
        )

    ensure_open_interval(all_scores, "aggregate scores")
    ensure_open_interval(all_rewards, "aggregate rewards")
    medium_cheat_score = run_episode(
        "task_medium_debugging",
        ANTI_GAMING_ATTEMPTS["task_medium_debugging"],
    )["final_score"]
    print(
        "[QUALITY] aggregate",
        f"scores_ok={all(0 < score < 1 for score in all_scores)}",
        f"rewards_ok={all(0 < reward < 1 for reward in all_rewards)}",
        f"score_min={min(all_scores):.2f}",
        f"score_max={max(all_scores):.2f}",
        f"reward_min={min(all_rewards):.2f}",
        f"reward_max={max(all_rewards):.2f}",
    )
    print(
        "[QUALITY] medium_cheat_compare",
        f"previous={PREVIOUS_MEDIUM_CHEAT_SCORE:.2f}",
        f"current={medium_cheat_score:.2f}",
    )


if __name__ == "__main__":
    main()

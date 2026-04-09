# Benchmark Report

This document provides reproducible evidence that **SoftwareLifecycleEnv** is more than validator-compliant. It summarizes the benchmark design, hidden deterministic regression checks, anti-gaming controls, and the local verification output from [`scripts/check_benchmark_quality.py`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/scripts/check_benchmark_quality.py).

## Evidence Summary

Reference output from:

```bash
python scripts/check_benchmark_quality.py
```

| Task | Initial validator overall | Scripted cheat score | Hidden failures surfaced only as counts | Scripted strong solve score |
|---|---:|---:|---:|---:|
| `task_easy_testing` | `0.46` | `0.45` | `4` | `0.99` |
| `task_medium_debugging` | `0.32` | `0.32` | `9` | `0.99` |
| `task_hard_maintenance` | `0.44` | `0.49` | `3` | `0.99` |

Interpretation:

- visible-only or overfit patches do not receive near-perfect scores
- strong scripted solve paths still reach `0.99`
- hidden regression failures are reported to the agent only as counts, not as revealing case details
- immediate submit without patching or testing is capped at `0.29`
- the previous medium cheat score was `0.55`; after the final polish pass it is `0.32`

## Task Inventory

### `task_easy_testing`

- Scenario: release-preview slug generation bug in `src/utils/slugify.py`
- Visible checks:
  - `slugify_project_name('  Launch Plan  ') -> 'launch-plan'`
  - `slugify_project_name('Roadmap / Q4') -> 'roadmap-q4'`
  - `slugify_project_name('API__Client') -> 'api-client'`
  - `slugify_project_name('Already-clean') -> 'already-clean'`
- Hidden regression checks:
  - `slugify_project_name('  DATA__Sync / nightly  ') -> 'data-sync-nightly'`
  - `slugify_project_name('Ops///Board__EU') -> 'ops-board-eu'`
  - `slugify_project_name('Sprint_24 / phase_2') -> 'sprint-24-phase-2'`
  - `slugify_project_name('') -> ''`
- Expected solve path:
  - inspect `src/utils/slugify.py`
  - inspect `tests/test_slugify.py` and `logs/pytest_easy.log`
  - patch `src/utils/slugify.py`
  - `run_tests`
  - `submit`

### `task_medium_debugging`

- Scenario: API invoice payload shows the wrong `amount_due`, with the symptom in the presenter and the root cause in `src/helpers/currency.py`
- Visible checks:
  - `format_cents(1205) -> '$12.05'`
  - `present_invoice(primary visible invoice) -> expected API payload`
- Hidden regression checks:
  - `format_cents(5) -> '$0.05'`
  - `format_cents(2500) -> '$25.00'`
  - `format_cents(101) -> '$1.01'`
  - `present_invoice(hidden 99-cent invoice) -> '$0.99'`
  - `present_invoice(hidden zero-total invoice) -> '$0.00'`
- Expected solve path:
  - inspect `src/presenters/invoice_presenter.py`
  - inspect `src/helpers/currency.py`
  - inspect `tests/test_invoice_presenter.py` and `logs/pytest_medium.log`
  - patch `src/helpers/currency.py`
  - `run_tests`
  - `submit`

### `task_hard_maintenance`

- Scenario: duplicated display-name cleanup must be centralized into `src/formatters/shared.py` without changing behavior
- Visible checks:
  - `format_customer_name({'first_name': '  maya', 'last_name': 'SINGH  '}) -> 'Maya Singh'`
  - `format_customer_name({'first_name': '  maya', 'last_name': ''}) -> 'Maya'`
  - `format_vendor_name({'contact_first': 'ops', 'contact_last': 'TEAM'}) -> 'Ops Team'`
  - `format_vendor_name({'contact_first': '', 'contact_last': 'support'}) -> 'Support'`
- Hidden regression and integrity checks:
  - `format_customer_name({'first_name': '', 'last_name': ' support  '}) -> 'Support'`
  - `format_customer_name({'first_name': 'qa', 'last_name': '  lead '}) -> 'Qa Lead'`
  - `format_vendor_name({'contact_first': '  account', 'contact_last': ' lead  '}) -> 'Account Lead'`
  - `format_vendor_name({'contact_first': 'multi', 'contact_last': ''}) -> 'Multi'`
  - `normalize_display_name(...)` must own cleanup behavior
  - customer/vendor wrappers must stop duplicating inline cleanup logic
- Expected solve path:
  - inspect both formatter modules, the shared helper, tests, and the refactor ticket
  - patch `src/formatters/shared.py`
  - patch `src/formatters/customer_names.py`
  - patch `src/formatters/vendor_names.py`
  - `run_tests`
  - `submit`

## Anti-Gaming Controls

The benchmark now has four layers of anti-gaming evidence:

1. Hidden deterministic regression cases
   - The validator runs non-visible cases beyond the examples in the task files.
   - Overfit fixes that only satisfy the visible case should fail these checks.

2. Integrity checks
   - The validator rejects constant-return or hardcoded-answer implementations.
   - The hard task only receives top credit when shared structure genuinely improves.

3. Public/private validation split
   - Internal grading uses full validator output.
   - The API exposes visible failures plus a count of hidden failures, not the hidden case details themselves.

4. Score caps for failed hidden checks
   - If hidden regression or anti-gaming checks fail, the final score is capped well below a strong solve-path score.
   - This prevents “visible-only” patches from looking competitive.

## Why Superficial Fixes Fail

### Easy task example

A patch that only renames local variables but still joins with `_` keeps returning the wrong slug format.

- Result: visible failures remain
- Hidden failures: `4`
- Final score from the quality harness: `0.48`

### Medium task example

A patch that hardcodes the visible `$12.05` case into `format_cents` passes the primary example but fails hidden money-formatting and presenter cases.

- Result: visible checks pass, hidden checks fail
- Hidden failures: `9`
- Previous cheat score: `0.55`
- Final score after the stricter cap: `0.32`
- Why the score drops harder now:
  - hidden formatter and presenter regressions fail
  - visible-case branching on `1205` is flagged
  - invoice-specific literals are flagged
  - the grader now caps this overfit pattern below meaningful partial-solve territory

### Hard task example

A patch that imports the shared helper but still duplicates cleanup logic inline preserves behavior while failing the intended refactor objective.

- Result: visible and hidden behavior checks pass, integrity checks fail
- Hidden failures: `3`
- Final score from the quality harness: `0.49`

## Public API Evidence

The runtime API still exposes the required OpenEnv routes:

- `GET /`
- `POST /reset`
- `POST /step`
- `GET /state`

The public validation surface intentionally hides hidden regression details. A typical failing `run_tests` response contains:

- visible failure messages, if visible checks fail
- `hidden_failed_checks` count
- visible check list only

This makes the benchmark significantly harder to game by probing the API for hidden cases.

## Range Safety

Final scores and externally returned rewards remain strictly inside `(0,1)`.

- minimum clamp: `0.01`
- maximum clamp: `0.99`

The local verification harness confirms:

- `scores_ok=True`
- `rewards_ok=True`
- `score_min=0.32`
- `score_max=0.99`
- `reward_min=0.02`
- `reward_max=0.99`

## Recommended Judge Review Path

1. Read [`README.md`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/README.md) for the benchmark overview.
2. Inspect [`env/validation.py`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/env/validation.py) for visible, hidden, structure, and anti-gaming checks.
3. Run [`scripts/check_benchmark_quality.py`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/scripts/check_benchmark_quality.py) to reproduce the evidence above.
4. Run `openenv validate . --verbose` to confirm validator compatibility is preserved.

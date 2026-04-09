# Benchmark Report

This document provides reproducible evidence that **SoftwareLifecycleEnv** is more than validator-compliant. It summarizes the benchmark design, hidden deterministic regression checks, workflow-aware reward model, anti-gaming controls, and the local verification output from [`scripts/check_benchmark_quality.py`](scripts/check_benchmark_quality.py).

## Evidence Summary

Reference output from:

```bash
python scripts/check_benchmark_quality.py
```

| Task | Workflow Focus | Initial validator overall | Scripted cheat score | Hidden failures surfaced only as counts | Scripted strong solve score |
|---|---|---:|---:|---:|---:|
| `task_easy_testing` | Testing | `0.43` | `0.39` | `3` | `0.99` |
| `task_medium_debugging` | Debugging | `0.30` | `0.32` | `7` | `0.99` |
| `task_hard_maintenance` | Maintenance | `0.44` | `0.41` | `3` | `0.99` |

Interpretation:

- strong scripted solve paths still reach `0.99`
- visible-only or overfit patches do not receive near-perfect scores
- hidden regression failures are reported to the agent only as counts, not as revealing case details
- immediate submit without patching or testing is capped at `0.29`
- the previous medium cheat score was `0.55`; after the stricter anti-gaming cap it is `0.32`

## Task Inventory

### `task_easy_testing`

- Workflow focus: testing / diagnosis-first
- Scenario: CI preview URL contract failure in release tooling
- Primary context:
  - `tests/test_preview_router.py`
  - `logs/github_actions_preview.log`
  - `ci/job_summary.txt`
  - `notes/release_comment.md`
  - `src/release_preview/router.py`
  - `src/release_preview/slug_builder.py`
  - `src/release_preview/settings.py`
  - `docs/preview_routing.md`
- Visible checks:
  - `build_preview_url('feature/Auth_Reset', 'WEB-401') -> 'https://preview.internal.example/web-401-auth-reset'`
  - `build_preview_url(' hotfix / Billing__retry ', 'OPS-9') -> 'https://preview.internal.example/ops-9-billing-retry'`
  - `build_preview_url('release/May_Cutover', 'REL-77') -> 'https://preview.internal.example/rel-77-may-cutover'`
- Hidden regression checks:
  - `build_preview_url('bugfix///API__Client', 'CORE-11') -> 'https://preview.internal.example/core-11-api-client'`
  - `build_preview_url('feature / data_SYNC / nightly', 'PLAT-204') -> 'https://preview.internal.example/plat-204-data-sync-nightly'`
  - `build_preview_url('release/Sprint_24', 'REL-24') -> 'https://preview.internal.example/rel-24-sprint-24'`
  - `build_preview_url('', 'OPS-1') -> 'https://preview.internal.example/ops-1'`
- Expected solve path:
  - inspect the failing test, CI log, and job summary first
  - inspect router and slug-builder flow
  - inspect settings, release note, and routing policy
  - patch `src/release_preview/slug_builder.py`
  - `run_tests`
  - `submit`

### `task_medium_debugging`

- Workflow focus: debugging / root-cause repair
- Scenario: billing admin API renders `amount_due` incorrectly because the helper imported dashboard rounding config instead of API formatting config
- Primary context:
  - `tests/test_invoice_endpoint.py`
  - `logs/api_serialization.log`
  - `logs/request_trace.log`
  - `git/last_change.txt`
  - `notes/incident_summary.md`
  - `src/api/invoice_endpoint.py`
  - `src/presenters/invoice_presenter.py`
  - `src/helpers/currency.py`
  - `src/config/api_formatting.py`
  - `src/config/dashboard_formatting.py`
  - `docs/amount_formatting.md`
- Visible checks:
  - `format_cents(1205) -> '$12.05'`
  - `serialize_invoice_response(primary visible invoice) -> expected API payload`
- Hidden regression checks:
  - `format_cents(5) -> '$0.05'`
  - `format_cents(2500) -> '$25.00'`
  - `format_cents(101) -> '$1.01'`
  - `serialize_invoice_response(hidden 99-cent invoice) -> '$0.99'`
  - `serialize_invoice_response(hidden zero-total invoice) -> '$0.00'`
- Expected solve path:
  - inspect the failing endpoint test, API log, request trace, and incident note
  - inspect endpoint and presenter flow
  - inspect helper, both config modules, and the recent change summary
  - patch `src/helpers/currency.py`
  - `run_tests`
  - `submit`

### `task_hard_maintenance`

- Workflow focus: maintenance / safe improvement
- Scenario: duplicated display-name cleanup must move into `src/shared/display_name.py` without changing customer API payloads or vendor export rows
- Primary context:
  - `logs/duplication_audit.log`
  - `audit/duplication_report.txt`
  - `docs/partner_output_contract.md`
  - `notes/tech_debt_ticket.md`
  - `review/refactor_note.md`
  - `notes/refactor_ticket.md`
  - `src/api/customer_payload.py`
  - `src/exports/vendor_rows.py`
  - `src/shared/display_name.py`
  - `tests/test_partner_outputs.py`
- Visible checks:
  - `build_customer_payload(primary customer record) -> expected API payload`
  - `build_customer_payload(customer blank-last-name record) -> expected API payload`
  - `build_vendor_row(primary vendor record) -> expected export row`
  - `build_vendor_row(vendor blank-first-name record) -> expected export row`
- Hidden regression and integrity checks:
  - `build_customer_payload(customer support-contact record) -> expected API payload`
  - `build_customer_payload(customer qa-lead record) -> expected API payload`
  - `build_vendor_row(vendor account-lead record) -> expected export row`
  - `build_vendor_row(vendor blank-last-name record) -> expected export row`
  - `normalize_display_name(...)` must own cleanup behavior
  - API/export wrappers must stop duplicating inline cleanup logic
- Expected solve path:
  - inspect the duplication audit, tech-debt ticket, review note, refactor ticket, and output contract
  - inspect both consumers and the shared helper
  - patch shared logic and both consumers
  - `run_tests`
  - `submit`

## Why These Tasks Better Match the Software Lifecycle

The three tasks are intentionally differentiated:

1. Testing
   - The first job is diagnosis: understand why a failing contract test broke in CI.
   - The fix is small, but the workflow is “read the symptom, locate the cause, confirm policy.”
   - Job summaries and release comments make the evidence feel more like a real blocked release.

2. Debugging
   - The first visible failure is not the root cause.
   - The task requires tracing behavior through endpoint, presenter, helper, and config layers.
   - Request traces, incident notes, and a recent change summary make the debugging path feel more like an on-call investigation.

3. Maintenance
   - The task starts from duplication/audit pressure rather than a simple functional bug.
   - Success requires preserving compatibility across multiple consumers while improving structure.
   - Audit notes, tech-debt backlog pressure, and reviewer guidance make the maintenance objective feel more like real engineering follow-through.

## Workflow-Aware Reward Evidence

The environment now rewards coverage of workflow buckets rather than only raw file count. Each task defines inspection buckets such as:

- `symptom`
- `implementation`
- `policy`
- `flow`
- `consumers`
- `shared_logic`
- `contracts`

That means:

- testing agents are rewarded for reading failing tests and logs before patching
- debugging agents are rewarded for reading the symptom path, root-cause helper, and policy/config files
- maintenance agents are rewarded for reading the audit and compatibility contract before refactoring

The added artifacts are intentionally lightweight and deterministic, but they make the repo snapshots feel much more like real work arriving through CI failures, incident follow-up, and maintenance review pressure.

Patching before reviewing the right context reduces reward confidence and final score ceiling.

## Anti-Gaming Controls

The benchmark has four layers of anti-gaming protection:

1. Hidden deterministic regression cases
   - The validator runs non-visible cases beyond the examples in the task files.

2. Integrity checks
   - The validator rejects constant-return or hardcoded-answer implementations.
   - The debugging task checks that the helper uses API formatting config instead of dashboard rounding config.
   - The maintenance task only receives top credit when shared structure genuinely improves.

3. Public/private validation split
   - Internal grading uses the full validator output.
   - The API exposes visible failures plus hidden-failure counts, not hidden case details.

4. Score caps for failed hidden checks
   - If hidden regression or anti-gaming checks fail, the final score is capped well below a strong solve-path score.

## Why C++ Was Not Used

No C++ was added in this benchmark upgrade.

That decision was intentional. A compiled task component would only be worth adding if it materially improved task realism without complicating validation, deployment, and Hugging Face stability. For this environment, realism improved more by:

- adding endpoint/config/log context
- differentiating testing, debugging, and maintenance workflows
- strengthening compatibility-preserving refactor requirements

Adding a C++ artifact here would have introduced toolchain risk with limited benchmark benefit.

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
- `reward_min=0.04`
- `reward_max=0.99`

## Recommended Judge Review Path

1. Read [`README.md`](README.md) for the benchmark overview.
2. Inspect [`env/tasks.py`](env/tasks.py) for the task inventory and repo snapshots.
3. Inspect [`env/validation.py`](env/validation.py) for visible, hidden, structure, and anti-gaming checks.
4. Run [`scripts/check_benchmark_quality.py`](scripts/check_benchmark_quality.py) to reproduce the evidence above.
5. Run `openenv validate . --verbose` to confirm validator compatibility is preserved.

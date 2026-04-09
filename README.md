---
title: Software Lifecycle Env
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
# SoftwareLifecycleEnv

> A deterministic OpenEnv benchmark for the software lifecycle: testing diagnosis, root-cause debugging, and safe code maintenance.

This repository is designed to evaluate whether an agent can investigate a realistic mini codebase the way an engineer would, not just patch a visible bug until one example passes.

## Overview

**SoftwareLifecycleEnv** evaluates whether an agent can work through a small but believable software repository the way an engineer would:

- diagnose a failing check from tests, logs, and config context
- trace a bug across multiple modules and fix the right component
- carry out a maintenance refactor that reduces duplication without changing public behavior

The benchmark stays lightweight and validator-safe, but the task design now aims to reflect the spirit of a real software lifecycle environment rather than a toy string-editing puzzle.

## Why This Benchmark Exists

Many small coding environments only ask an agent to edit one function until a visible example passes. Real software work is usually messier:

- the first symptom is often not the root cause
- logs and config files matter
- job summaries, incident notes, and audit comments shape investigation
- behavior must be preserved for more than one consumer
- maintenance work is not the same as bug fixing

This benchmark encodes those patterns in deterministic, CPU-cheap tasks with behavior-based grading and hidden regression checks.

## Software Lifecycle Tasks

| Task | Skill Evaluated | Example Scenario |
|---|---|---|
| `task_easy_testing` | Diagnose failing checks under release constraints | CI preview URL contract failure with test output, job summary, release note, and routing policy |
| `task_medium_debugging` | Trace root cause across layers and patch the correct component | Billing API amount formatting bug caused by the helper importing the wrong config |
| `task_hard_maintenance` | Improve code safely without breaking consumers | Shared display-name cleanup refactor across API and export code under audit/review pressure |

## Task Inventory

Exactly three tasks are provided, each mapped to a different part of the software lifecycle.

| Task ID | Difficulty | Workflow Focus | Scenario | Why it feels more real |
|---|---|---|---|---|
| `task_easy_testing` | Easy | Testing | CI preview URL contract failure | Requires diagnosing a failing router contract from test output, CI log, code, and settings |
| `task_medium_debugging` | Medium | Debugging | Billing API amount formatting bug | The symptom appears in the endpoint layer, while the root cause lives in a helper using the wrong config |
| `task_hard_maintenance` | Hard | Maintenance | Shared display-name cleanup refactor | Requires reducing duplication across API and export consumers while preserving both output contracts |

## Agent Interaction Loop

1. The agent receives a repo snapshot plus structured context such as failing checks, important files, and workflow focus.
2. The agent inspects code, tests, logs, config, and investigation artifacts like job summaries or incident notes.
3. The agent applies actions by inspecting files, patching a file, running deterministic validation, or submitting.
4. The environment evaluates visible behavior, hidden regressions, and anti-gaming checks.
5. Each step returns a reward strictly inside `(0,1)`, and final submission scoring also stays strictly inside `(0,1)`.

## Task Design

### Testing task

`task_easy_testing` is not just “fix a slug function.” The visible failure occurs in a router-level CI check:

- `tests/test_preview_router.py` shows the broken preview URL contract
- `logs/github_actions_preview.log` shows how CI observed the mismatch
- `ci/job_summary.txt` frames the failure as a blocked preview-deploy release job
- `notes/release_comment.md` explains why QA cares about ticket-prefixed preview URLs
- `src/release_preview/router.py` shows the symptom path
- `src/release_preview/slug_builder.py` contains the real behavior bug
- `src/release_preview/settings.py` and `docs/preview_routing.md` define the routing rules the code must follow

This is meant to feel like triaging a small release-tooling regression.

### Debugging task

`task_medium_debugging` is root-cause-first:

- the visible failure is in `tests/test_invoice_endpoint.py`
- the symptom appears at the endpoint layer in `src/api/invoice_endpoint.py`
- `logs/request_trace.log` shows the call path from endpoint to helper
- `notes/incident_summary.md` captures the production-facing symptom reported by users
- `git/last_change.txt` adds a realistic clue about how the bug was introduced
- the bug flows through `src/presenters/invoice_presenter.py`
- the root cause is in `src/helpers/currency.py`
- the agent must compare `src/config/api_formatting.py` against `src/config/dashboard_formatting.py`

That makes the task about localization and reasoning across modules, not just patching the file named in the failing assertion.

### Maintenance task

`task_hard_maintenance` starts from a maintenance/audit problem instead of a classic red test:

- `logs/duplication_audit.log` calls out the duplication risk
- `audit/duplication_report.txt` reads like a lightweight static-analysis finding
- `notes/tech_debt_ticket.md` frames the cleanup as backlog pressure from real engineering work
- `review/refactor_note.md` adds reviewer constraints on what must stay stable
- `notes/refactor_ticket.md` defines the maintenance goal
- `docs/partner_output_contract.md` explains what behavior must remain stable
- `src/api/customer_payload.py` and `src/exports/vendor_rows.py` duplicate cleanup logic
- `src/shared/display_name.py` is the shared helper that should own that logic

This task measures safe engineering improvement, not just bug fixing.

## Action Space

| Action | Description | Required Fields |
|---|---|---|
| `inspect_file` | View a file in the in-memory repo | `target_file` |
| `apply_patch` | Replace one file with full new content | `target_file`, `patch_content` |
| `run_tests` | Run deterministic behavioral validation | none |
| `submit` | End the episode and receive a final score | none |

## Observation Space

The observation model is typed with Pydantic and includes both the raw file map and structured engineering context.

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | Stable task identifier |
| `task_type` | `str` | `easy`, `medium`, or `hard` |
| `workflow_focus` | `str` | `testing`, `debugging`, or `maintenance` |
| `task_description` | `str` | Human-readable objective |
| `repo_summary` | `str` | Short environment / codebase context |
| `important_files` | `list[str]` | Most relevant files to inspect |
| `failing_checks` | `list[str]` | Deterministic failing test or audit hints |
| `constraints` | `list[str]` | Requirements the patch must preserve |
| `files` | `dict[str, str]` | Full current file contents |
| `test_output` | `str \| null` | Output from the last validation run |
| `last_action_result` | `str \| null` | Result of the last action |
| `recent_actions` | `list[str]` | Short recent action history |
| `steps_taken` | `int` | Current step count |
| `max_steps` | `int` | Episode budget |

## Behavioral Validation

This benchmark does **not** score success from magic substrings.

Each task has task-specific deterministic validation that:

- parses task modules with a conservative AST allowlist
- blocks unsafe imports and dunder access
- executes only known task modules with restricted builtins
- calls specific target functions with fixed visible and hidden checks
- validates behavior at the right layer for the task:
  - router-level URLs for testing
  - endpoint-level payloads for debugging
  - API/export outputs plus structure checks for maintenance
- keeps hidden regression details out of the public API

The task repos also now include lightweight investigation artifacts like CI job summaries, incident notes, and audit reports so the agent must reason from realistic engineering evidence rather than only from source code.

## Workflow-Aware Reward Design

Step rewards are bounded strictly inside `(0,1)` and now reflect lifecycle-specific progress.

The environment rewards:

- inspecting symptom files, implementation files, policy/config files, and contract files
- covering multiple workflow buckets rather than reading only one code file
- patching the correct component
- improving behavioral validation
- using `run_tests` before `submit`

It penalizes:

- wrong-file patching
- no-op or superficial patches
- repeated ineffective actions
- patching before reviewing the right symptom/contract context
- step overflow

This makes testing feel more like diagnosis, debugging feel more like root-cause tracing, and maintenance feel more like safe compatibility work.

## Hidden Checks and Anti-Gaming

The benchmark is intentionally harder to game than a visible-example-only environment.

- Hidden deterministic regression cases run for every task.
- The API exposes visible failures and hidden-failure counts, not hidden case details.
- Integrity checks reject constant-return, visible-case-branching, and fake-refactor solutions.
- The medium task specifically punishes visible-case money formatting hacks.
- The hard task only reaches top score if shared structure genuinely improves.

Current quality-harness evidence:

| Task | Initial overall | Scripted cheat score | Strong solve score |
|---|---:|---:|---:|
| `task_easy_testing` | `0.43` | `0.39` | `0.99` |
| `task_medium_debugging` | `0.30` | `0.32` | `0.99` |
| `task_hard_maintenance` | `0.44` | `0.41` | `0.99` |

The medium hardcoded visible-case cheat was previously around `0.55`; it is now capped around `0.32`.

## Why C++ Was Not Added

No C++ component was added in this version.

That choice was deliberate: adding compiled task artifacts would introduce toolchain and deployment risk without enough realism gain for this benchmark size. The realism improvement here comes from:

- richer repo context
- clearer symptom-to-cause separation
- config- and contract-aware workflows
- stronger behavior-preserving maintenance work

That provides a better risk/reward tradeoff for a Hugging Face / OpenEnv hackathon submission.

## Sample Strong Trajectories

### Testing

Typical strong path for `task_easy_testing`:

1. inspect `tests/test_preview_router.py`
2. inspect `logs/github_actions_preview.log`
3. inspect `ci/job_summary.txt`
4. inspect `src/release_preview/router.py`
5. inspect `src/release_preview/slug_builder.py`
6. inspect `src/release_preview/settings.py`
7. inspect `notes/release_comment.md`
8. inspect `docs/preview_routing.md`
9. patch `src/release_preview/slug_builder.py`
10. run validation
11. submit

Reward trajectory from the quality harness:

```text
0.16,0.12,0.12,0.12,0.14,0.14,0.10,0.10,0.41,0.72,0.99
```

### Debugging

Typical strong path for `task_medium_debugging`:

1. inspect `tests/test_invoice_endpoint.py`
2. inspect `logs/api_serialization.log`
3. inspect `logs/request_trace.log`
4. inspect `notes/incident_summary.md`
5. inspect `src/api/invoice_endpoint.py`
6. inspect `src/presenters/invoice_presenter.py`
7. inspect `src/helpers/currency.py`
8. inspect API and dashboard formatting configs
9. inspect `git/last_change.txt`
10. inspect `docs/amount_formatting.md`
11. patch `src/helpers/currency.py`
12. run validation
13. submit

Reward trajectory from the quality harness:

```text
0.16,0.12,0.12,0.12,0.12,0.15,0.18,0.14,0.10,0.10,0.10,0.48,0.72,0.99
```

### Maintenance

Typical strong path for `task_hard_maintenance`:

1. inspect `logs/duplication_audit.log`
2. inspect `audit/duplication_report.txt`
3. inspect `docs/partner_output_contract.md`
4. inspect `notes/tech_debt_ticket.md`
5. inspect `review/refactor_note.md`
6. inspect `notes/refactor_ticket.md`
7. inspect API / export / shared-helper code
8. inspect tests
9. patch `src/shared/display_name.py`
10. patch `src/api/customer_payload.py`
11. patch `src/exports/vendor_rows.py`
12. run validation
13. submit

Reward trajectory from the quality harness:

```text
0.14,0.10,0.10,0.10,0.10,0.10,0.18,0.14,0.18,0.10,0.11,0.16,0.17,0.72,0.99
```

## OpenEnv Compliance

The repository preserves the required OpenEnv interface:

- typed `Observation`, `Action`, and `RewardInfo` models in `env/models.py`
- `reset()` returns an initial observation
- `step(action)` returns `observation`, `reward`, `done`, and `info`
- `state()` returns the current environment state
- `openenv.yaml` is present
- `server/app.py` serves the benchmark API
- `inference.py` remains at the repo root

All final scores and externally returned rewards are clamped strictly inside `(0,1)`:

```python
score = max(0.01, min(score, 0.99))
```

## Setup

### Prerequisites

- Python 3.10+
- pip

### Local installation

```bash
git clone <repo-url>
cd software-lifecycle-env
pip install -r requirements.txt
```

### Start the server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

You can also use:

```bash
uv run server --host 0.0.0.0 --port 7860
```

## Docker

```bash
docker build -t software-lifecycle-env .
docker run -p 7860:7860 software-lifecycle-env
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/reset` | Reset environment, optionally to a specific task |
| `POST` | `/step` | Execute one action |
| `GET` | `/state` | Return current environment state |

### Example

```bash
curl http://localhost:7860/

curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_medium_debugging"}'

curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "inspect_file", "target_file": "src/helpers/currency.py"}'
```

## Inference Usage

```bash
export HF_TOKEN=hf_xxxxx
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct:cerebras

python inference.py
```

`inference.py` still:

- uses the OpenAI Python client
- requires `HF_TOKEN`
- provides defaults for `API_BASE_URL` and `MODEL_NAME`
- emits exact `[START]`, `[STEP]`, and `[END]` log lines

## Benchmark Evidence

The repository includes a reproducible evidence layer beyond the official validator:

- [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md): judge-facing benchmark summary, hidden-check inventory, anti-gaming rationale, and sample outcomes
- [`scripts/check_benchmark_quality.py`](scripts/check_benchmark_quality.py): local harness that verifies score bounds, reward bounds, hidden-check secrecy, anti-gaming attempts, and strong solve paths

## Hugging Face Spaces

This repository is configured as a Docker Space and serves the API on port `7860`. To deploy:

1. Create a Docker Space.
2. Push this repository to the Space remote.
3. Add `HF_TOKEN` in Space secrets if you plan to run `inference.py` inside the Space.
4. Let the container build automatically.

## Resource Profile

| Resource | Requirement |
|---|---|
| CPU | 2 vCPU |
| RAM | 8 GB |
| Disk | < 500 MB |
| GPU | Not required |

## License

MIT

---
title: Software Lifecycle Env
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---
# SoftwareLifecycleEnv

> A deterministic OpenEnv benchmark for realistic software maintenance and debugging tasks.

## Overview

**SoftwareLifecycleEnv** evaluates whether an agent can inspect a small codebase, identify the real source of a failure, apply a patch, validate behavior, and submit a solution. The benchmark keeps the OpenEnv interface lightweight while making the tasks feel more like day-to-day repository work.

## Motivation

Many software benchmarks collapse into toy string-editing problems. This environment instead focuses on the workflow real engineers follow:

- inspect implementation files, tests, logs, and maintenance notes
- diagnose failures from behavior instead of magic strings
- patch the correct module or shared abstraction
- verify non-regression behavior before submitting
- survive hidden deterministic regression checks that are not exposed through the public API

The result is still deterministic and cheap to run, but much harder to game with superficial edits.

## Tasks

Exactly three tasks are provided, with increasing difficulty and stronger repo realism.

| Task ID | Difficulty | Scenario | What makes it realistic |
|---|---|---|---|
| `task_easy_testing` | Easy | Preview URL slug bug in `src/utils/slugify.py` | Requires reading both utility code and test/log context |
| `task_medium_debugging` | Medium | Wrong invoice `amount_due` caused by a helper/presenter mismatch | Failure symptom is in the presenter test, root cause is in a helper |
| `task_hard_maintenance` | Hard | Duplicate display-name cleanup logic across formatter modules | Requires centralizing logic in a shared helper while preserving behavior |

## Action Space

| Action | Description | Required Fields |
|---|---|---|
| `inspect_file` | View a file in the in-memory repo | `target_file` |
| `apply_patch` | Replace one file with full new content | `target_file`, `patch_content` |
| `run_tests` | Run deterministic behavioral validation | none |
| `submit` | End the episode and receive a final score | none |

## Observation Space

The observation model is typed with Pydantic and includes both the raw file map and extra structured context.

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | Stable task identifier |
| `task_type` | `str` | `easy`, `medium`, or `hard` |
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

This benchmark does **not** grade success from substring insertion alone.

Each task has task-specific deterministic validation that:

- parses task modules with a conservative AST allowlist
- blocks unsafe imports and dunder access
- executes only known task modules with restricted builtins
- calls specific target functions with fixed input/output checks
- verifies both visible behavior and hidden regression cases
- adds integrity and structure checks where the task requires a real refactor
- exposes only visible failure details through the API while keeping hidden cases internal to grading

### Task-specific validators

- Easy: calls `slugify_project_name(...)` across primary and regression slug cases
- Medium: validates both `format_cents(...)` and `present_invoice(...)`
- Hard: validates formatter behavior in both modules and checks that duplicated logic was moved into `src/formatters/shared.py`

## Trust and Anti-Gaming

This benchmark is intentionally harder to game than a typical small-code benchmark.

- Hidden deterministic regression cases are used in grading but are not leaked through `/step` or `/state`.
- Validators reject constant-return and hardcoded-answer patches for the easy and medium tasks.
- The hard task receives top credit only when both behavior is preserved and duplicated cleanup really moves into the shared helper.
- Final scoring caps non-successful submissions well below the scripted strong solve path, even if they overfit the visible example.
- Immediate submit without patching or testing is capped at `0.29`.
- The previous medium hardcoded visible-case cheat landed around `0.55`; it is now capped around `0.32`.

Judge-facing evidence is documented in [`BENCHMARK_REPORT.md`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/BENCHMARK_REPORT.md), and the local verification harness lives at [`scripts/check_benchmark_quality.py`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/scripts/check_benchmark_quality.py).

## Grading

Final grading combines workflow quality and validator output. It rewards:

- inspecting relevant files
- patching the correct file set
- improving behavioral validation
- preserving non-regression cases
- using the test/validation step before submit

It penalizes:

- wrong-file patching
- repeated ineffective actions
- repeated action loops
- step overflow

All final scores are clamped strictly inside `(0,1)`:

```python
score = max(0.01, min(score, 0.99))
```

So task scores are never exactly `0.0` or `1.0`.

Submissions that fail hidden regression or anti-gaming checks are explicitly capped below strong solve-path scores, which makes visible-only overfitting much less competitive.

## Reward Design

Step rewards are also bounded strictly inside `(0,1)`. Rewards are shaped to reflect realistic progress:

- higher reward for inspecting implementation files the task actually depends on
- smaller reward for inspecting supporting tests/logs
- strong reward for patches that improve behavioral validation
- strong reward for passing validation in `run_tests`
- lower reward for no-op, superficial, overfit, or hidden-regression-failing patches
- low reward for wrong-file patches, invalid patches, and repeated ineffective actions

This gives agents feedback throughout the trajectory instead of only at terminal submit.

## Sample Trajectory

One meaningful scripted solve path for `task_medium_debugging` is:

1. inspect `src/presenters/invoice_presenter.py`
2. inspect `src/helpers/currency.py`
3. inspect the visible test and failure log
4. patch `src/helpers/currency.py`
5. run validation
6. submit

The reproducible reward trajectory from the local quality harness is:

```text
0.12, 0.18, 0.12, 0.12, 0.57, 0.72, 0.99
```

That trajectory shows the environment rewarding useful inspection, correct root-cause patching, behavioral validation, and final submission.

## OpenEnv Compliance

The repository preserves the required OpenEnv interface:

- typed `Observation`, `Action`, and `RewardInfo` models in `env/models.py`
- `reset()` returns an initial observation
- `step(action)` returns `observation`, `reward`, `done`, and `info`
- `state()` returns the current environment state
- `openenv.yaml` is present
- `server/app.py` serves the benchmark API
- `inference.py` remains at the repo root

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

The API will be available at `http://localhost:7860`.

You can also use the packaged script:

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

- [`BENCHMARK_REPORT.md`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/BENCHMARK_REPORT.md): judge-facing benchmark summary, hidden-check inventory, anti-gaming rationale, and sample outcomes
- [`scripts/check_benchmark_quality.py`](C:/Users/milnazaroor/Downloads/software-lifecycle-env/scripts/check_benchmark_quality.py): local harness that verifies score bounds, reward bounds, hidden-check secrecy, anti-gaming attempts, and strong solve paths

## Baseline Trajectory Targets

Illustrative optimal trajectories now look more like real debugging flows than one-line toy fixes.

| Task | Typical strong path | Max final score |
|---|---|---|
| Easy | inspect utility -> inspect test/log -> patch utility -> run tests -> submit | `0.99` |
| Medium | inspect presenter -> inspect helper -> inspect test/log -> patch helper -> run tests -> submit | `0.99` |
| Hard | inspect both formatters + shared helper + ticket -> patch shared/helper callers -> run tests -> submit | `0.99` |

The quality harness also demonstrates that scripted cheat attempts land much lower:

- easy overfit attempt: `0.45`
- medium hardcoded visible-case attempt: `0.32` after the final anti-gaming cap, down from `0.55`
- hard superficial refactor attempt: `0.49`

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

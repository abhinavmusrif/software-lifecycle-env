# SoftwareLifecycleEnv

> A deterministic benchmark environment simulating real-world software engineering tasks for the **Meta OpenEnv Hackathon Round 1**.

---

## Overview

**SoftwareLifecycleEnv** challenges an LLM agent with three progressive software engineering tasks — testing, debugging, and refactoring — then scores performance using a deterministic, partial-credit grading rubric.

The environment is lightweight (runs on 2 vCPU / 8 GB RAM), fully deterministic, and exposes an OpenEnv-compatible HTTP API for integration with any agent framework.

## Motivation

Real-world software engineering requires more than code generation. Engineers must:
- **Read** existing code to understand bugs
- **Diagnose** failures from test output
- **Patch** code with correct fixes
- **Validate** that changes pass tests before submitting

This benchmark measures all four skills in a controlled, reproducible setting.

---

## Tasks

| # | Difficulty | Type | Bug | Expected Fix |
|---|-----------|------|-----|-------------|
| 1 | **Easy** | Testing | `is_even` uses `n % 2 == 1` | `n % 2 == 0` |
| 2 | **Medium** | Debugging | `add` uses `a - b` | `return a + b` |
| 3 | **Hard** | Maintenance | Duplicated `format_name` / `format_author` | Extract `_format_person` helper |

---

## Action Space

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `inspect_file` | View the contents of a file | `target_file` |
| `apply_patch` | Replace a file's full content | `target_file`, `patch_content` |
| `run_tests` | Run the deterministic test suite | — |
| `submit` | End the episode, receive final score | — |

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | Unique task identifier |
| `task_type` | `str` | `easy` / `medium` / `hard` |
| `task_description` | `str` | Human-readable task description |
| `files` | `dict[str, str]` | Current workspace file contents |
| `test_output` | `str \| null` | Output from the last test run |
| `last_action_result` | `str \| null` | Result of the previous action |
| `steps_taken` | `int` | Number of steps taken so far |
| `max_steps` | `int` | Maximum steps allowed |

---

## Reward Logic

### Step Rewards

| Trigger | Reward |
|---------|--------|
| Inspect correct (buggy) file | **+0.10** |
| Patch applied to correct file | **+0.20** |
| Patch contains expected fix pattern | **+0.30** |
| All tests pass | **+0.40** |
| Submit → final grading score | **+score** |

### Penalties

| Trigger | Penalty |
|---------|---------|
| Repeated exact action | **−0.05** |
| Inspect wrong file | **−0.05** |
| Invalid/empty patch | **−0.10** |
| Exceed step budget | **−0.20** |

### Final Grading (on submit)

| Component | Score |
|-----------|-------|
| Inspected correct file | +0.20 |
| Patched correct file | +0.30 |
| Patch contains expected pattern | +0.20 |
| Tests pass | +0.30 |
| **Total** | **1.00** |

Final score clamped to **[0.0, 1.0]**.

---

## Setup

### Prerequisites

- Python 3.11+
- pip

### Local Installation

```bash
git clone <repo-url>
cd software-lifecycle-env
pip install -r requirements.txt
```

### Start the Server

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

The API will be available at `http://localhost:7860`.

---

## Docker

```bash
# Build
docker build -t software-lifecycle-env .

# Run
docker run -p 7860:7860 software-lifecycle-env
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/reset` | Reset env (optional `{"task_id": "..."}`) |
| `POST` | `/step` | Execute an action |
| `GET` | `/state` | Current environment state |

### Examples

```bash
# Health check
curl http://localhost:7860/

# Reset to a specific task
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_easy_testing"}'

# Inspect a file
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "inspect_file", "target_file": "utils.py"}'

# Apply a patch
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "apply_patch", "target_file": "utils.py", "patch_content": "def is_even(n):\n    return n % 2 == 0\n"}'

# Run tests
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "run_tests"}'

# Submit
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "submit"}'
```

---

## Inference Usage

```bash
export HF_TOKEN=hf_xxxxx
export API_BASE_URL=https://router.huggingface.co/v1          # optional
export MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct:cerebras   # optional

python inference.py
```

### Output Format

```
[START] task=task_easy_testing env=SoftwareLifecycleEnv model=meta-llama/Llama-3.1-8B-Instruct:cerebras
[STEP] step=1 action=inspect_file reward=0.10 done=false error=null
[STEP] step=2 action=apply_patch reward=0.50 done=false error=null
[STEP] step=3 action=run_tests reward=0.40 done=false error=null
[STEP] step=4 action=submit reward=1.00 done=true error=null
[END] success=true steps=4 rewards=0.10,0.50,0.40,1.00
```

---

## Baseline Scores

| Task | Optimal Steps | Max Score | Random Agent |
|------|--------------|-----------|-------------|
| Easy (testing) | 4 | 1.00 | 0.00 – 0.20 |
| Medium (debugging) | 4 | 1.00 | 0.00 – 0.20 |
| Hard (maintenance) | 4 | 1.00 | 0.00 – 0.20 |

---

## Hugging Face Spaces Deployment

1. Create a new **Docker** Space on [huggingface.co/spaces](https://huggingface.co/spaces)
2. Push this repository to the Space
3. Add the `HF_TOKEN` secret in Space Settings → Secrets
4. The Space auto-builds and serves the API on port 7860

---

## Resource Requirements

| Resource | Requirement |
|----------|-------------|
| CPU | 2 vCPU |
| RAM | 8 GB |
| Disk | < 500 MB |
| GPU | Not required |

---

## License

MIT

# Contributing

Thanks for taking a look at Software Lifecycle Env.

This project is a deterministic benchmark environment for evaluating AI agents on software engineering workflows: testing, debugging, and maintenance.

## Good Contributions

Useful contributions include:

- new benchmark tasks with realistic engineering context
- stronger hidden regression checks
- clearer reward-shaping logic
- bug fixes in validation or server behavior
- documentation improvements
- examples showing how agents interact with the environment

## Task Design Rules

New tasks should:

- include a realistic symptom, such as a failing test, log, incident note, review note, or config mismatch
- require inspecting more than one file before patching
- separate visible checks from hidden regression checks
- avoid secrets, private company names, real customer data, and production credentials
- keep validation deterministic and CPU-cheap
- keep final rewards strictly inside `(0,1)`

## Local Verification

Before opening a pull request, run:

```bash
python scripts/check_benchmark_quality.py
```

If you changed server behavior, also run:

```bash
python - <<'PY'
from env.environment import SoftwareLifecycleEnv
from server.app import app

env = SoftwareLifecycleEnv()
obs = env.reset("task_easy_testing")
print(obs.task_id, obs.workflow_focus, len(obs.files), app.title)
PY
```

## Pull Request Checklist

- README or benchmark report updated when behavior changes
- no real secrets or tokens committed
- quality script passes
- task behavior is deterministic
- hidden checks do not reveal hidden answers to the agent


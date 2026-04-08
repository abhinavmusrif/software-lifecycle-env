#!/usr/bin/env python3
"""Inference script for SoftwareLifecycleEnv.

Drives an LLM agent through every benchmark task using the OpenAI Python
client.  Reads environment variables:

  API_BASE_URL  – LLM endpoint   (default: https://router.huggingface.co/v1)
  MODEL_NAME    – model ID       (default: meta-llama/Llama-3.1-8B-Instruct:cerebras)
  HF_TOKEN      – HF API token   (REQUIRED)

Log format (exact):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import List

from openai import OpenAI

from env.environment import SoftwareLifecycleEnv
from env.models import Action, ActionType
from env.tasks import list_task_ids

# ── configuration ────────────────────────────────────────────────────────

API_BASE_URL: str = os.environ.get(
    "API_BASE_URL", "https://router.huggingface.co/v1"
)
MODEL_NAME: str = os.environ.get(
    "MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct:cerebras"
)
HF_TOKEN: str = os.environ.get("HF_TOKEN", "")

if not HF_TOKEN:
    print("ERROR: HF_TOKEN environment variable is required.", file=sys.stderr)
    sys.exit(1)

BENCHMARK_NAME = "SoftwareLifecycleEnv"


# ── formatting helpers ───────────────────────────────────────────────────

def _b(val: bool) -> str:
    """Format bool as lowercase true/false."""
    return "true" if val else "false"


def _r(val: float) -> str:
    """Format reward to 2 decimal places."""
    return f"{val:.2f}"


# ── prompt builders ──────────────────────────────────────────────────────

def _system_prompt(obs: dict) -> str:
    return (
        "You are a software engineering agent. Your current task:\n\n"
        f"Task: {obs['task_description']}\n\n"
        f"Files in workspace:\n{json.dumps(obs['files'], indent=2)}\n\n"
        "Respond with ONLY a JSON object (no markdown, no explanation):\n"
        '  "action_type": one of "inspect_file", "apply_patch", "run_tests", "submit"\n'
        '  "target_file": filename (required for inspect_file / apply_patch)\n'
        '  "patch_content": full new file content (required for apply_patch)\n\n'
        "Strategy: 1) inspect the buggy file  2) apply a fix  "
        "3) run tests  4) submit.\n"
    )


def _user_prompt(obs: dict) -> str:
    parts = [f"Step {obs['steps_taken']}/{obs['max_steps']}."]
    if obs.get("last_action_result"):
        parts.append(f"Last result: {obs['last_action_result']}")
    parts.append("Respond with your next action as JSON.")
    return "\n".join(parts)


# ── action parser ────────────────────────────────────────────────────────

def _parse_action(raw: str) -> Action:
    """Parse an LLM response string into an Action.  Strips markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    return Action(
        action_type=data.get("action_type", "submit"),
        target_file=data.get("target_file"),
        patch_content=data.get("patch_content"),
    )


# ── main loop ────────────────────────────────────────────────────────────

def run_task(env: SoftwareLifecycleEnv, task_id: str, client: OpenAI) -> None:
    """Run a single task to completion and emit structured logs."""
    print(f"[START] task={task_id} env={BENCHMARK_NAME} model={MODEL_NAME}")

    obs = env.reset(task_id)
    obs_dict = obs.model_dump()
    rewards: List[float] = []
    step_num = 0

    try:
        while not env.state()["done"]:
            step_num += 1

            # Call the LLM
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": _system_prompt(obs_dict)},
                        {"role": "user", "content": _user_prompt(obs_dict)},
                    ],
                    temperature=0.0,
                    max_tokens=1024,
                )
                raw = response.choices[0].message.content or '{"action_type":"submit"}'
            except Exception as api_err:
                # On API failure, gracefully submit
                action = Action(action_type=ActionType.SUBMIT)
                result = env.step(action)
                rewards.append(result.reward)
                print(
                    f"[STEP] step={step_num} action=submit "
                    f"reward={_r(result.reward)} done={_b(result.done)} "
                    f"error={api_err}"
                )
                break

            # Parse LLM output into an action
            error_msg: str | None = None
            try:
                action = _parse_action(raw)
            except Exception:
                error_msg = "parse_error"
                action = Action(action_type=ActionType.SUBMIT)

            # Execute the action
            result = env.step(action)
            rewards.append(result.reward)

            if error_msg is None and result.info.get("error"):
                error_msg = str(result.info["error"])

            print(
                f"[STEP] step={step_num} "
                f"action={action.action_type.value} "
                f"reward={_r(result.reward)} "
                f"done={_b(result.done)} "
                f"error={error_msg if error_msg else 'null'}"
            )

            obs_dict = result.observation.model_dump()

        # Emit END
        success = env.state().get("tests_passed", False)
        rewards_str = ",".join(_r(r) for r in rewards)
        print(f"[END] success={_b(success)} steps={step_num} rewards={rewards_str}")

    except Exception:
        # Always emit END, even on unexpected exceptions
        rewards_str = ",".join(_r(r) for r in rewards)
        print(f"[END] success=false steps={step_num} rewards={rewards_str}")
        traceback.print_exc()


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    env = SoftwareLifecycleEnv()

    for task_id in list_task_ids():
        run_task(env, task_id, client)
        print()  # blank line between tasks


if __name__ == "__main__":
    main()

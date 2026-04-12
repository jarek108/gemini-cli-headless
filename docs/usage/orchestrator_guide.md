# Orchestrator Guide (E2E Workflows)

The orchestrator (`implementation_run.py`) is the engine that drives the Autonomous Developer OS. It manages the agent loop, enforces the artifact contract, and interacts with the Central Registry.

## Basic Usage

To launch an autonomous implementation run, you need a target workspace directory containing your codebase and an `IRQ.md` (Implementation Request) file.

```bash
python implementation_run.py --workspace /path/to/my-project
```

### The `IRQ.md` File
Before running the orchestrator, ensure an `IRQ.md` file exists in the root of your target `--workspace`. This file acts as the "ticket" or "specification" for the agents.

```markdown
# Task: Add Google OAuth
Please implement Google OAuth 2.0 login in `auth.py`.
- Use the `google-auth` library.
- Create a new endpoint `/login/google`.
- Do not modify existing email/password logic.
```

## Configuration (`run_config.json`)

You can customize the behavior of the agents and the state machine by providing a JSON configuration file.

```bash
python implementation_run.py --workspace ./my-project --config-file config.json
```

### Example `config.json`

```json
{
  "doer_model": "gemini-2.5-flash-lite",
  "qa_model": "gemini-3-flash-preview",
  "max_iters": 5,
  "registry_base": "~/.gemini/orchestrator/runs",
  "memory_and_context": {
    "doer_amnesia_frequency": 1,
    "qa_amnesia_frequency": 1,
    "doer_past_qrp_count": 1,
    "doer_past_irp_count": 0,
    "qa_past_qrp_count": 2,
    "qa_past_irp_count": 1
  }
}
```

### Configuration Parameters

*   **`doer_model` / `qa_model`**: The Gemini models to use for the respective roles.
*   **`max_iters`**: The maximum number of Doer->QA loops before the orchestrator forcefully aborts the run (default: 3).
*   **`registry_base`**: Override the default location of the Central Registry.
*   **`memory_and_context`**:
    *   `amnesia_frequency`: How often the agent's internal session ID is reset. `1` means a fresh session every iteration (recommended to prevent anchoring bias).
    *   `past_qrp_count`: How many previous QA Reports (`QRP.md`) to inject into the agent's XML prompt.
    *   `past_irp_count`: How many previous Implementation Reports (`IRP.md`) to inject.

## Advanced Overrides via CLI

You can override key parameters directly from the command line without editing the JSON file:

```bash
python implementation_run.py \
  --workspace ./my-project \
  --doer-model gemini-1.5-pro \
  --max-iters 10
```

## Monitoring a Run

Because the orchestrator routes all logs and artifacts to the Central Registry, the terminal output is intentionally quiet, showing only high-level phase transitions.

To deep-dive into what the agent is doing, navigate to the registry directory (printed in the terminal output, e.g., `~/.gemini/orchestrator/runs/run_1712345678/`).

*   Check `logs/v1_doer_try1.log` to see the raw LLM output.
*   Check `artifacts/v1_IRP.md` to see the evacuated artifact.
*   Check `run_state.json` to view the live USD cost calculation and API error metrics.
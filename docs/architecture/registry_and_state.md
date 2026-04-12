# Central Registry & State Management

The Developer OS must maintain state—knowing the current iteration, tracking costs, storing feedback for the Amnesia Engine, and keeping audit logs. However, storing this state in the target project's repository creates immense friction (polluted git working trees, accidental commits, messy `.gitignore` files).

To achieve absolute separation of concerns, all orchestration state is managed in a **Central Registry**.

## The Hierarchy of the Registry

By default, the orchestrator uses `~/.gemini/orchestrator/runs/` as the base directory. You can override this using the `--registry-base` flag.

Every time `implementation_run.py` is invoked, it creates an isolated directory for that specific task:

```text
~/.gemini/orchestrator/runs/run_1775980593/
├── run_config.json       # The immutable spec/limits for the task
├── run_state.json        # The live state machine
├── artifacts/            # Evacuated Markdown files
│   ├── v1_IRP.md
│   ├── v1_QRP.md
│   └── v2_IRP.md
└── logs/                 # Raw API responses
    ├── v1_doer_try1.log
    ├── v1_qa_try1.log
    └── v2_doer_try1.log
```

## The State Machine (`run_state.json`)

The orchestrator is purely functional. If it crashes (e.g., due to a power outage), it can resume perfectly by reading the Central Registry. It does not hold state in Python memory.

`run_state.json` acts as the source of truth:

```json
{
  "iteration": 2,
  "total_cost": 0.0527,
  "total_api_requests": 62,
  "total_api_errors": 0,
  "status": "SUCCESS",
  "history": [
    {
      "iteration": 1,
      "outcome": "to correct"
    },
    {
      "iteration": 2,
      "outcome": "final"
    }
  ]
}
```

## How the Orchestrator Uses the Registry

1. **Evacuation**: When an agent finishes its turn, the orchestrator immediately moves `IRP.md` from the user's workspace into the `artifacts/` folder of the registry.
2. **Context Assembly**: When preparing the prompt for the next round, the Amnesia Engine reads `v{N}_QRP.md` directly from the registry to build the `<active_feedback>` XML payload.
3. **Audit & Billing**: The orchestrator intercepts the token usage statistics returned by the headless wrapper (`GeminiSession.stats`), calculates the exact USD cost based on the active model, and updates the `total_cost` in `run_state.json`.

By treating the workspace solely as a temporary execution canvas and the Registry as the immutable brain, the Developer OS achieves true enterprise-grade isolation.
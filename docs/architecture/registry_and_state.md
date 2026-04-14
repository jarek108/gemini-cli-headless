# Central Registry & Telemetry Management

In the Developer OS architecture, the state of the code and the artifacts (the "What") are managed natively by Git (see [Git as the State Machine](system_design.md)). 

However, the OS still requires a secure, isolated place to store the **Metadata and Telemetry** (the "How much" and the "Why"). Storing raw API responses, token counts, and USD cost calculations in the target project's Git repository creates immense friction.

To achieve an absolute separation of concerns, all execution telemetry is managed in a **Central Registry**.

## The Hierarchy of the Registry

By default, the orchestrator uses `~/.gemini/orchestrator/runs/` as the base directory. You can override this using the `--registry-base` flag.

Every time `implement_feature.py` triggers the loop, it creates an isolated directory matching the Git branch ID:

```text
~/.gemini/orchestrator/runs/run_1775980593/
├── run_config.json       # The immutable spec/limits for the task
├── run_state.json        # The live telemetry (cost, API errors)
└── logs/                 # Raw LLM thought processes
    ├── v1_doer_try1.log
    ├── v1_qa_try1.log
    └── v2_doer_try1.log
```

## The Telemetry Engine (`run_state.json`)

The orchestrator is purely functional. While Git holds the code state, `run_state.json` acts as the source of truth for billing and operational health:

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

1. **Audit & Billing**: After every LLM call, the orchestrator intercepts the token usage statistics returned by the headless wrapper (`GeminiSession.stats`), calculates the exact USD cost based on the active model, and updates `total_cost`.
2. **Error Manifests**: If an API call fails (e.g., a 503 error), it is logged in the `api_error_manifest` so the Manager can see if the run is struggling due to external API instability.
3. **The Thought Process**: The actual "chain of thought" output from the LLM (which is not written to the clean `IRP.md` or `QRP.md` artifacts) is saved as raw text files in the `logs/` directory. If an agent does something truly baffling, you can open the Registry logs to read its internal monologue.

By splitting responsibilities—Git for the Execution State, Registry for the Telemetry—the Developer OS remains both incredibly transparent and deeply observable without polluting the working codebase.
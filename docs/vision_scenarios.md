# Interaction Scenarios: A Day in the Life

To give you a feel for what it is like to work with this Autonomous Developer OS powered by `gemini-cli-headless`, here are a few practical scenarios of the workflow in action.

### Scenario 1: Delegating a Feature (The "Fire and Forget")
You open your terminal in the root `projects/` directory and chat with the Manager CLI.

**You:** *"We need to add a `/health` endpoint to the `fdds` server. It should return a simple 200 OK JSON response. Spin up a worker to handle it."*

**Manager:** *"Understood. I have created a new worker sandbox `worker_sandboxes/task_health_endpoint` based on the `fdds` repository. The `run_config.json` has been generated with a $1.00 budget and a 5-iteration limit. The `implementation_run.py` process has been started in the background. You can continue your work; I will notify you when it's done."*

*Behind the scenes:* The `implementation_run.py` script starts. The Doer writes the endpoint. The QA rejects it because it's missing a unit test. The Doer adds the test. The QA approves.

### Scenario 2: The Semi-Passive Hook in Action
An hour later, you are asking the Manager about something completely unrelated.

**You:** *"Remind me, what port is the kanbanAgents server running on?"*

**Manager:** *"The `kanbanAgents` server typically runs on port 61154.*

*By the way, my background scan (`get_worker_status` hook) shows that `task_health_endpoint` has finished successfully after 2 iterations (Cost: $0.15). However, another background task `task_db_migrate_456` has failed and terminated due to a semantic loop (QA rejected the same file changes twice). Would you like to review the artifacts for either of these?"*

**You:** *"Merge the health endpoint to main, and show me the `QRP_v2.md` from the failed migration task."*

### Scenario 3: Loop Detection and The Supervisor
What happens when the Doer and QA get stuck?

If the Doer modifies a file, but the QA rejects it with the exact same feedback as the previous round, or if the file hashes don't change at all, the orchestrator script detects a **Deadlock**. 

Instead of burning through the budget, the orchestrator triggers a **Level 3 Supervisor Agent** (e.g., a heavier model like `gemini-1.5-pro` or `gemini-1.5-pro-exp`). The Supervisor reads the history of `IRP.md` and `QRP.md` and provides a definitive, tie-breaking instruction to the Doer to break the loop, or escalates the issue to you (the human).
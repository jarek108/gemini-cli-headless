# System Design: Git as the State Machine

The core architectural innovation of the Developer OS is the merging of the **Control Plane** (the Orchestrator) and the **Execution Plane** (the Workspace) through a **Git-Native State Machine**.

Instead of trying to manage complex file syncing or hiding temporary files from the human user, the Developer OS leans into the tools engineers already use. It uses **isolated Git branches** to perform work, committing every single step of the agentic loop as a "Time Travel Checkpoint."

## The Two Sources of Truth

The system separates *State* from *Telemetry*.

### 1. Git (The State Machine)
The Execution Plane is the physical directory where the code lives (e.g., `projects/my-app/`). When a feature is dispatched, the system creates a dedicated branch (e.g., `gemini-run-123`).

Every action an agent takes is permanently recorded here:
*   The Headless Manager drafts the specs -> **Commit**.
*   The Doer writes code and an `IRP.md` -> **Commit**.
*   The QA audits and writes a `QRP.md` -> **Commit**.

Because the state is managed entirely via Git, the human engineer has absolute observability. You can check out the branch, view the `git diff` of what the Doer did, or even make manual override commits if the AI gets stuck.

*(See [The "Checkpoint" Concept](time_travel_and_checkpoints.md) for a deep dive).*

### 2. The Central Registry (The Telemetry Engine)
While the code and artifacts live in Git, storing massive API responses and cost calculations in a git repository is an anti-pattern. 

Therefore, all orchestration metadata is routed to a **Central Registry**, isolated outside the workspace (e.g., `~/.gemini/orchestrator/runs/<run_id>`).

Inside a Registry Run directory, you will find:
*   `run_config.json`: The immutable configuration for the run.
*   `run_state.json`: Live tracking of the current iteration, API errors, and the accumulated USD cost.
*   `logs/`: The raw JSON/stdout of every single LLM interaction (`v1_doer_try1.log`). This is where you go to read the agent's hidden "thought process."

## Accumulative Knowledge vs. "Zero Pollution"
In older versions of the OS, artifacts were instantly evacuated from the workspace to prevent "pollution." 

In the Git-Native design, the artifacts (`IRQ.md`, `QRP.md`) live directly on the feature branch. Pollution is no longer a concern because the branch is isolated. 

Furthermore, instead of passing the entire chat history back and forth, the OS uses **Accumulative Knowledge**. In each iteration, the QA agent reads its own previous `QRP.md` and summarizes the history of the run directly into the *new* `QRP.md`'s "Trajectory" section. This highly compressed artifact is then committed to Git, acting as a perfect, low-token context injection for the next round of the Amnesia Engine.

## The Cleanup Merge
Once the orchestrator reports `[STATUS: SUCCESS]`, the engineer reviews the branch. They perform a simple cleanup commit to delete the artifact files (`git rm IRQ.md QAR.md IRP.md QRP.md`), leaving pure, verified code ready to be merged into `main`.
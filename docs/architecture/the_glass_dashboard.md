# The Glass (Observability Dashboard)

The Developer OS operates completely autonomously and headlessly. To prevent the "Terminal Babysitting Trap," the system provides absolute observability without terminal spam through **The Glass**—a live, local CI/CD dashboard.

## The Architecture of Observability
Because the OS uses [Git as the State Machine](system_design.md) and a Central Registry for telemetry, building observability does not require a complex database. The file system *is* the database.

The Glass is a zero-dependency local web server that provides a visual interface for the system's execution.

### The Backend (The Observer API)
The dashboard is powered by a lightweight Python server (`tools/dashboard.py`) that acts as a read-only observer. It exposes simple HTTP endpoints that:
1.  **Scan the Registry**: Reads `run_state.json` to get live status (`PENDING`, `SUCCESS`), token usage, and API costs.
2.  **Read the Logs**: Serves the raw LLM thought processes from the `logs/` directory.
3.  **Inspect the State Machine (Git)**: Executes `git diff` and `git show` on the hidden feature branches (`gemini-run-<id>`) to show exactly what code and artifacts were changed at any given point in time.

### The Frontend (The Polling Loop)
The UI is a simple, stateless frontend that polls the Observer API every second. This ensures you always see the live state of the factory floor without the complexity of WebSockets or event-driven architectures.

## The Visual Timeline

When you open the dashboard during a run, you see the execution represented as a series of **Sequential Horizontal Blocks**. Each block corresponds to a Time Travel Checkpoint (a Git commit).

A typical successful run visualizes like this:
`[ 📝 Specs (Manager) ] ➔ [ 🏗️ Iter 1 (Doer) ] ➔ [ ❌ Iter 1 (QA) ] ➔ [ 🏗️ Iter 2 (Doer) ] ➔ [ ✅ Iter 2 (QA) ]`

## Deep Inspection (Time Travel)
The true power of The Glass is interactivity. You are not just reading a log; you are inspecting the Git State Machine.

When you click on a specific block (e.g., `[ 🏗️ Iter 1 (Doer) ]`), an inspector panel opens allowing you to view:
1.  **The Code Diff**: Exactly what lines of code the Doer changed in that specific iteration.
2.  **The Artifacts**: The exact content of the `IRP.md` or `QRP.md` generated at that moment in time.
3.  **The Monologue**: The raw LLM "chain of thought" API response that led to those changes.
4.  **The Cost**: The exact USD cost and token count of that single step.

If a run fails or loops endlessly, you can use The Glass to identify exactly which iteration went wrong, check out that specific branch in your editor, manually correct the code, and instruct the OS to resume from your human intervention.
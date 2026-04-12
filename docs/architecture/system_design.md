# System Design & Isolation

The core architectural innovation of the Gemini CLI Headless Orchestrator V2 is the absolute decoupling of the **Control Plane** from the **Execution Plane**. This ensures that the agentic loop remains deterministic and that the user's workspace is protected from metadata pollution.

## The Two Planes

### 1. The Control Plane (The Orchestrator)
The Control Plane is managed by `implementation_run.py`. It is the brain of the operation. It manages budgets, tracks API errors, parses YAML frontmatter, decides when to trigger a Reprimand Loop, and orchestrates the Amnesia Engine.

**Crucially, the Control Plane does not live in your project directory.**

All orchestrator state, logs, and artifacts are routed to a **Central Registry**. By default, this is located outside the workspace (e.g., `~/.gemini/orchestrator/runs/<run_id>`). 

Inside a Registry Run directory, you will find:
*   `run_config.json`: The immutable configuration for this run.
*   `run_state.json`: The live state machine (current iteration, cost, status).
*   `logs/`: Raw stdout/stderr of every single agent interaction (`v1_doer.log`, `v2_qa.log`).
*   `artifacts/`: The evacuated Markdown files produced by the agents (`v1_IRP.md`, `v1_QRP.md`).

### 2. The Execution Plane (The Clean Workspace)
The Execution Plane is the physical directory where the code lives (e.g., `projects/my-app/`).

When the orchestrator spawns an agent (the "Doer" or the "QA"), it binds them strictly to this directory using the `cwd` parameter of the wrapper. 

The agent operates under the illusion that this directory is the entire universe. It reads code, runs tests, and writes its Implementation Report (`IRP.md`) or QA Report (`QRP.md`) directly into this workspace.

## The Artifact Evacuation Cycle

To maintain a pristine workspace and prevent the agent from getting confused by its own past outputs, the system employs an **Artifact Evacuation Cycle**:

1. **Agent Acts**: The Doer agent writes code and generates `IRP.md` in the workspace root.
2. **Orchestrator Intercepts**: The moment the Doer's run finishes, the Orchestrator steps in. It immediately *moves* `IRP.md` out of the workspace and into the Central Registry (`artifacts/v{i}_IRP.md`).
3. **Agent Audits**: The QA agent runs. It generates `QRP.md` in the workspace.
4. **Orchestrator Intercepts**: The Orchestrator moves `QRP.md` to the Central Registry.

### Why Evacuate?
1. **Zero Pollution**: Your Git working tree remains completely clean. There are no `.agent_session.json`, `IRP.md`, or `QRP_v3.md` files to add to `.gitignore` or accidentally commit.
2. **State Control**: By physically removing the files, we prevent the agent from accidentally reading a report from Iteration 1 while currently operating in Iteration 3. The Orchestrator dictates exactly what the agent sees through the Amnesia Engine.

## Safe Merging
Because the orchestrator state is completely isolated, the human engineer can review the final code in the Execution Plane without wading through metadata. Once the orchestrator reports `[STATUS: SUCCESS]`, the engineer can confidently run `git add . && git commit` knowing that the workspace contains pure, verified code.
# The Hierarchical Architecture & Execution Loop

This document details the core vision of using `gemini-cli-headless` as the foundation for an **Autonomous Developer OS**. It strictly separates the human coordination layer from the physical execution layer, allowing you to scale across multiple projects and concurrent tasks seamlessly.

## 1. The Three Levels of Orchestration

### Level 1: The Manager (Tech Lead)
* **Location:** The root `projects/` directory containing all your repositories.
* **Role:** The Manager (an interactive instance of Gemini CLI) is your single point of contact. It acts as the Tech Lead. It **does not write code**. 
* **Behavior:** When you provide a strategic goal (e.g., "Add Google OAuth to the frontend"), the Manager analyzes the request, selects the appropriate project, and generates strict specification documents (`run_config.json`). It then delegates the task to the execution layer by spawning an autonomous loop in the background.

### Level 2: The Projects (Domain Context)
* **Location:** Individual project folders (e.g., `projects/fdds/`).
* **Role:** Each project acts as a container for its own rules and instances. A project manifest (e.g., `.gemini.md`) provides the specific domain context: "In this project, we use Python 3.10 and `pytest`." The Manager injects these rules into the workers' prompts.

### Level 3: The Project Instances (Execution Environments)
* **Location:** Isolated subfolders or dedicated Git worktrees *within* the project container (e.g., `projects/fdds/instance_worker_1/`).
* **Role:** This is where the actual coding happens. The Manager spawns an asynchronous `implementation_run.py` script bound to this specific directory (via the `cwd` parameter in `gemini_cli_headless`). This ensures **Level 2 OS protection**—workers cannot accidentally modify files outside their assigned sandbox.
* *(See [The Multi-Instance Project Architecture](vision_multi_instance.md) for a detailed breakdown of this structure).*

## 2. The Artifact Contract (Structured Parsability)

To prevent agents from drifting into endless, unproductive refactoring cycles, the execution layer abandons open-ended chat in favor of a strict **Artifact-Driven Workflow**.

Relying on an LLM to output a perfectly structured JSON response natively can be brittle. Instead, we use a hybrid approach:
* **Markdown Contracts:** Agents are instructed to generate physical Markdown files on disk (`IRP.md`, `QRP.md`).
* **Strict Formatting Rules:** The first line of the QA Report (`QRP.md`) **MUST** be exactly `[STATUS: APPROVED]` or `[STATUS: REJECTED]`.
* **Deterministic Parsing:** The Python orchestrator (`implementation_run.py`) does not use complex Regex to "understand" the QA's chat. It strictly checks the first line of the physical file.
* **Self-Correction:** If an agent provides feedback but forgets to generate the file or include the exact `[STATUS:...]` header, the orchestrator does not crash. It rejects the artifact and prompts the agent: *"You broke the format. Rewrite the report with the correct header."*

## 3. The Deterministic Execution Loop (`implementation_run.py`)

1. **The Input (`run_config.json`):** Defines the exact task, budget limits (max USD cost), iteration limits, and model selections.
2. **Phase 1 (The Doer):** The "Doer" writes code within the isolated instance. It is *forced* to generate an Implementation Report (`IRP.md`). If missing, the orchestrator reprimands the agent before trying again.
3. **Phase 2 (The QA):** The "QA" audits the changes against the `IRP.md`. It generates a QA Report (`QRP.md`) using the strict Artifact Contract.
4. **The Router:** The script reads the `QRP.md`. If rejected, it feeds the QA's bulleted feedback back to the Doer for the next iteration. If limits are hit, the process safely terminates. 
5. **Advanced Loop Detection:** To prevent endless arguments, the orchestrator computes hashes of modified files and analyzes semantic similarity of QA feedback. If files don't change but the QA rejects them, the orchestrator detects a **Deadlock**, halting the run or calling a 3rd 'Supervisor' agent.

## 4. Semi-Passive Monitoring & Reactiveness

* **State via Files:** We do not use complex databases. The entire state of a worker is deduced directly from the presence and content of its artifacts (`IRP_vX.md`, `QRP_vX.md`) and its local session JSON files.
* **The `get_worker_status` Hook:** Whenever you interact with the Manager CLI, a pre-prompt hook silently executes a lightweight status script. This script scans the file system of all active project instances to determine current phases and budgets.
* **Context Injection:** This state is injected into the Manager's context transparently. The Manager can then seamlessly append updates to your conversations:
  > *"Here is the architectural overview you requested. BTW: Worker 1 successfully finished the Login UI on branch `feature/login`."*

## 5. Safe Merging and Lifecycle Management

The Manager does not merge code autonomously unless explicitly commanded. This prevents chaos in your main codebase.

* Once an instance finishes successfully (QA `APPROVED`), the code remains isolated on its specific branch (e.g., `feature/login`).
* You review the artifacts and instruct the Manager: *"Looks good, merge it."*
* The Manager executes the `git merge` command. If a merge conflict occurs, the Manager detects the error code and asks for your guidance (or spawns a new worker specifically to resolve the conflict markers).
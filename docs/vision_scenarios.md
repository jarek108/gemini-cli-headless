# Interaction Scenarios: A Day in the Life

To give you a feel for what it is like to work with this Autonomous Developer OS powered by `gemini-cli-headless`, here are practical scenarios showcasing how the system scales from a simple flat directory to a complex, multi-agent enterprise workflow.

### Table of Contents
* **[1. Single-Worker Mode (The Flat Project)](#-1-single-worker-mode-the-flat-project)**: Quick, isolated tasks on a single branch without sandbox overhead.
* **[2. The Scale-Up (Transition from Flat to Multi-Worker)](#-2-the-scale-up-transition-from-flat-to-multi-worker)**: Automatically splitting large features into parallel, isolated Git worktrees.
* **[3. Monitoring Execution (Two Modes)](#-3-monitoring-execution-two-modes)**: Active checking and passive background hooks keeping you updated.
* **[4. Handling Failures (Graceful Degradation)](#-4-handling-failures-graceful-degradation)**: Auto-correcting missing artifacts, enforcing strict budgets, and detecting loops.
* **[5. The Merge and Conflict Resolution](#-5-the-merge-and-conflict-resolution)**: Closing the loop by safely integrating autonomous work into your main codebase.

---

## 🌟 1. Single-Worker Mode (The Flat Project)
*The simplest scenario, perfect for quick fixes where you don't need complex Git branching.*

**You:** *"Write unit tests for the `calculate_cost` function in `src/utils/calc_stats.py` and then update the `README.md`."*

**Manager:** *"Got it. Since this is a straightforward sequence, I'll queue these tasks for a single worker operating directly in the `fdds` project root. The `implementation_run.py` process has been started in the background. I'll let you know when the queue is processed."*

*Behind the scenes:* The tasks are queued, and there is only one worker serving the queue. The Doer agent writes the tests directly in your current working directory, finishes, and then picks up the next task. You go grab a coffee. When you return, the tasks are simply there, verified by the QA agent sequentially.

## 🚀 2. The Scale-Up (Transition from Flat to Multi-Worker)
*The moment your project's complexity demands isolation to prevent collisions.*

**You:** *"Refactor the entire database schema to use SQLAlchemy, AND rewrite the CSS styles for the dashboard."*

**Manager:** *"Those are large, parallel changes that could conflict. I am transitioning this project from a flat structure to a Multi-Worker environment. We now have up to N tasks implemented in parallel (or N-1 isolated sandboxes, with the main instance left untouched for production). I've created two isolated sandboxes (`worker_sandboxes/task_db_refactor` and `worker_sandboxes/task_css_rewrite`) on separate Git branches. Both execution loops are now running independently."*

*Behind the scenes:* Your directory structure evolves on the fly. The flat project now gains isolated workspaces, allowing parallel execution without merge conflicts during development.

## 📡 3. Monitoring Execution (Two Modes)
*How you stay informed about the factory floor without micromanaging the workers.*

### 3A. Active Monitoring (Explicit Request)
**You:** *"Give me a status report on all running tasks."*

**Manager:** *(Parses the `.json` session files and artifacts of active workers)*
* *"**Task DB Refactor:** IN_PROGRESS (QA Iteration 2/5). Cost so far: $0.45."*
* *"**Task CSS Rewrite:** SUCCESS. Ready for review."*

### 3B. Passive Monitoring (The "BTW" Effect)
*You are discussing cloud architecture with the Manager.*

**Manager:** *"...and that is why a serverless approach fits your use case better.*

*By the way, my background scan (`get_worker_status` hook) shows that the `task_css_rewrite` has just finished successfully (Cost: $0.15). Would you like to review the artifacts?"*

## 💥 4. Handling Failures (Graceful Degradation)
*What happens when the robots mess up? The system enforces discipline without bothering you.*

### 4A. Artifact Failure (The Reprimand)
The Doer agent finishes writing code but forgets to create the mandatory `IRP.md` file. Instead of crashing the loop, the orchestrator intercepts the failure and sends a prompt back to the Doer: *"You claimed to be finished, but `IRP.md` is missing from the disk. You must create it now before QA can begin."* (This happens in milliseconds, entirely invisible to you).

### 4B. Budget Exceeded (The Hard Limit)
You set a strict $1.00 limit in `run_config.json`. During Iteration 4, the QA agent requests massive changes. The orchestrator calculates that the next Doer prompt will push the total cost to $1.05. The orchestrator instantly kills the process and notifies the Manager: *"Task suspended. Budget limit reached."*

### 4C. Deadlock and The Supervisor
The Doer modifies a file, but the QA rejects it with the exact same feedback as the previous round (or the file hashes don't change at all). The orchestrator detects a **Semantic Loop (Deadlock)**. 

Instead of burning through the budget, the orchestrator halts the Doer/QA loop and triggers a **Level 3 Supervisor Agent** (e.g., `gemini-1.5-pro-exp`). The Supervisor reads the history of `IRP.md` and `QRP.md` and provides a definitive, tie-breaking instruction to break the loop, or escalates the issue to you.

## 🔀 5. The Merge and Conflict Resolution
*The culmination of autonomous work.*

**Manager:** *"Worker 1 has successfully finished the Login UI on branch `feature/login`."*

**You:** *"Looks good, merge it to main."*

**Manager:** *(Attempts a fast-forward merge. It fails.)* *"Boss, we have a merge conflict in `routes.py` (Worker 1 changed the auth logic, but you added a new endpoint recently). Please open the file and resolve the `<<<<<<< HEAD` markers, or would you like me to spawn a dedicated 'Conflict-Resolver' worker to handle it?"*
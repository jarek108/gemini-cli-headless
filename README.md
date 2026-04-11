# gemini-cli-headless

A standalone, zero-dependency Python wrapper for executing the official Node.js Google Gemini CLI (`@google/gemini-cli`) in fully programmatic, headless mode.

## Why this wrapper?
While the official Python SDKs (`google-genai`) are excellent for building API-driven applications, they often impose strict, unconfigurable safety guardrails (blocking sensitive topics like abuse prevention) and require complex context-caching implementations for session history.

The **Gemini CLI** inherently bypasses many of these cloud limitations out-of-the-box and handles robust file-based session management. This wrapper provides a typed, Pythonic bridge to the CLI's `--json` and `--yolo` flags, allowing you to easily build complex RAG (Retrieval-Augmented Generation) pipelines, automate local file analysis, and effortlessly resume context-rich conversations across different projects.

## Key Features
*   **Zero Dependencies:** Relies purely on Python standard libraries (`subprocess`, `json`, `tempfile`, `shutil`). No need for `requests` or `python-dotenv`.
*   **Smart Session Resumption:** Pass either a raw UUID (`"abc-123"`) or a local JSON file path (`"data/user_session.json"`). If a path is provided, the wrapper automatically injects your local file into the CLI's internal workspace before execution, allowing portable, file-based conversation history.
*   **Structured Output:** Automatically parses the CLI's JSON stdout into a `GeminiSession` dataclass containing the AI's response, the session ID, and detailed token statistics (input, output, cached, thoughts).
*   **Bypass Length Limits:** Long prompts are automatically saved to temporary files and attached via the `@path` syntax, preventing OS-level terminal length restrictions.

## Installation
Currently available via GitHub:
```bash
pip install git+https://github.com/jarek108/gemini-cli-headless.git
```

*(Requires Node.js and `@google/gemini-cli` installed globally: `npm install -g @google/gemini-cli`)*

## Quick Start
```python
import shutil
from gemini_cli_headless import run_gemini_cli_headless

# Start a new conversation
session = run_gemini_cli_headless("Explain quantum computing in one sentence.")
print(f"AI: {session.text}")

# Save the session locally
shutil.copy2(session.session_path, "my_context.json")

# Resume the conversation later from your local file!
new_session = run_gemini_cli_headless(
    prompt="Now explain it to a 5-year-old.",
    session_to_resume="my_context.json"
)
```

---

# 🚀 The Vision: Autonomous Developer OS

While `gemini-cli-headless` is a powerful standalone library, its true potential is unlocked when used as the execution engine for an **Autonomous Developer OS (Multi-Agent Orchestration)**. 

We are moving away from the "Terminal Babysitting Trap"—where an engineer must constantly monitor and course-correct a single AI agent—towards a structured, deterministic production line managed by a hierarchy of AI roles.

## 1. The Hierarchical Architecture

This architecture strictly separates the human coordination layer from the physical execution layer, scaling across multiple projects and concurrent tasks.

### Level 1: The Manager (Tech Lead)
* **Location:** The root `projects/` directory containing all your repositories.
* **Role:** The Manager (an interactive instance of Gemini CLI) is your single point of contact. It acts as the Tech Lead. It **does not write code**. 
* **Behavior:** When you provide a strategic goal (e.g., "Add Google OAuth to the frontend"), the Manager analyzes the request, selects the appropriate project, creates isolated Git branches or folder copies (`worker_1`, `worker_2`), and generates strict specification documents (`run_config.json`). It then dispatches tasks by running the execution loops in the background.

### Level 2: The Projects (Domain Context)
* **Location:** Individual project folders (e.g., `projects/fdds/`).
* **Role:** Each project contains its own rules (e.g., a `.gemini.md` or `CONTRIBUTING.md` file). This provides the specific domain context: "In this project, we use Python 3.10 and `pytest`." The Manager injects these rules into the workers' prompts.

### Level 3: The Worker Sandboxes (Execution Environments)
* **Location:** Isolated subfolders or dedicated Git worktrees (e.g., `projects/fdds_worker_1/`).
* **Role:** This is where the actual coding happens. The Manager spawns an asynchronous `implementation_run.py` script bound to this specific directory (via the `cwd` parameter in `gemini_cli_headless`). This ensures Level 2 OS protection—workers cannot accidentally modify files outside their assigned sandbox.

## 2. The Deterministic Execution Loop (`implementation_run.py`)

To prevent agents from drifting into endless, unproductive refactoring cycles, the execution layer abandons open-ended chat in favor of a strict **Artifact-Driven Workflow**:

1. **The Input:** The loop starts by reading `run_config.json`, which defines the task, budget limits (max USD cost), iteration limits, and selected models.
2. **Phase 1 (The Doer):** The "Doer" agent writes code within the sandbox. It is *forced* to generate an Implementation Report (`IRP.md`) detailing the changed files. If the Doer fails to create this physical artifact on disk, the loop halts, and the Python orchestrator automatically reprimands the agent (Self-Correction) before trying again.
3. **Phase 2 (The QA):** The "QA" agent audits the changes against the `IRP.md`. It must generate a QA Report (`QRP.md`) starting with a strict keyword: `[STATUS: APPROVED]` or `[STATUS: REJECTED]`.
4. **The Router:** A deterministic Python script (not an AI) reads the `QRP.md`. If rejected, it extracts the QA's bulleted feedback and feeds it back to the Doer for the next iteration. If the iteration limit or cost budget is hit, the process safely terminates. 

## 3. Semi-Passive Monitoring & Reactiveness

You shouldn't have to repeatedly ask "Are the workers done?". The system is designed to be highly transparent but non-intrusive.

* **State via Files:** We do not use complex databases. The entire state of a worker is deduced directly from the presence and content of its artifacts (`IRP_v2.md`, `QRP_v2.md`) and its local session JSON files.
* **The `get_worker_status` Hook:** Whenever you interact with the Manager CLI to ask a generic question, a pre-prompt hook silently scans the file system of all active worker directories.
* **Context Injection:** This state is injected into the Manager's context transparently. The Manager can then seamlessly append updates to your conversations:
  > *"Here is the architectural overview you requested. BTW: Worker 1 successfully finished the Login UI on branch `feature/login`. Worker 2 is struggling with DB migrations (QA Iteration 3)."*

## 4. Safe Merging and Lifecycle Management

The Manager does not merge code autonomously unless explicitly commanded. This prevents chaos in your main codebase.

* Once a worker finishes successfully (QA `APPROVED`), the code remains isolated on its specific branch (`feature/login`).
* You review the artifacts (`IRP.md`/`QRP.md`) and instruct the Manager: *"Looks good, merge it."*
* The Manager executes the `git merge` command. If a merge conflict occurs, the Manager detects the error code and asks for your guidance (or spawns a new worker specifically to resolve the conflict markers).
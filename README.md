# Gemini CLI Headless & Developer OS Orchestrator

This repository provides two powerful layers for AI-assisted software engineering:

1.  **The Wrapper (`gemini_cli_headless.py`)**: A standalone, zero-dependency Python bridge for executing the official Node.js `@google/gemini-cli` in fully programmatic, headless mode.
2.  **The Orchestrator (`implementation_run.py`)**: An advanced, artifact-driven state machine that acts as an Autonomous Developer OS, moving beyond chat interfaces into a structured, verifiable production line.

## Why this exists: Escaping the "Terminal Babysitting Trap"

As coding agents become more capable, **human attention becomes the primary bottleneck**. If you've used open-ended "vibe-coding" tools, you've likely noticed they break down in real-world projects for a few predictable reasons:

*   **They get distracted easily:** Agents often try to rewrite whole systems or refactor unrelated code just to fix a small bug.
*   **They grade their own homework:** The same agent that writes the code also tells you "it works!", leaving you to double-check everything.
*   **You have to watch them constantly:** You can't just give them a list of tasks and walk away; you end up babysitting them step-by-step.
*   **They get stuck in bad ideas:** If an agent makes a mistake early on, it will stubbornly try to patch that mistake instead of starting fresh.
*   **You can't manage the big picture:** Because you have to micromanage the code terminal, you never get to step back and act like a project manager.
*   **They don't play well with teams:** Agents act like solo hackers, making it hard to integrate their work into normal team reviews and Kanban boards.
*   **They ignore the rules:** It's too easy for them to skip running tests or bypass code reviews because typed "instructions" aren't hard rules.

If a system is "productive" only when you are continuously monitoring its terminal output, it isn't scaling engineering—it is just relocating your work into a higher-stress form of supervision.

*(For a more in-depth technical analysis of these issues, read [The Terminal Babysitting Trap](docs/philosophy/the_terminal_babysitting_trap.md)).*

**The strategic pivot: limit freedom to increase capability.**

The way to make agents *more useful* is to make them *less free* through **hard workflows**. This project treats "agentic coding" like a controlled production line, enforcing state transitions via strict Markdown artifacts, physical workspace isolation, adversarial QA roles, and engineered memory amnesia.

---

## 🏗️ The Architecture (V2)

The system strictly separates the human coordination layer from the physical execution layer:

*   **[Control Plane & Central Registry](docs/architecture/registry_and_state.md)**: The orchestrator lives completely outside your codebase. All configurations, running costs, API logs, and execution histories are routed to an isolated Central Registry (`~/.gemini/orchestrator/runs/`). The agent never sees its own metadata.
*   **[Execution Plane (The Clean Workspace)](docs/architecture/system_design.md)**: Agents operate in a sandboxed directory containing *only* the source code and the immediate task specification (`IRQ.md`).
*   **[Artifact-Driven Workflow](docs/architecture/artifact_driven_flow.md)**: Agents communicate progress not through chat, but by producing strict YAML-frontmatter Markdown artifacts (`IRP.md` for execution, `QRP.md` for QA). If an agent fails to produce a file, the orchestrator triggers a *Reprimand Loop*, automatically disciplining the model to follow the protocol.
*   **[The Amnesia Engine](docs/architecture/amnesia_engine.md)**: To prevent LLM "anchoring bias" (where a model stubbornly defends a flawed approach), agents are subjected to frequent, hard memory resets. The orchestrator rebuilds their context dynamically by injecting specific historical artifacts (`<historical_feedback>`) via XML before each run.

## 📖 Documentation

Dive deeper into the philosophy and mechanics of the Developer OS:

### Philosophy
*   [The Developer OS Manifesto](docs/philosophy/manifesto.md)

### Architecture
*   [The 3-Part Prompting Stack](docs/architecture/prompting_architecture.md)
*   [System Design & Isolation](docs/architecture/system_design.md)
*   [The Artifact Contract & Reprimand Loops](docs/architecture/artifact_driven_flow.md)
*   [The Amnesia Engine & Context Injection](docs/architecture/amnesia_engine.md)
*   [Central Registry & State Management](docs/architecture/registry_and_state.md)
*   [Specialized QA & The Evolution of Skills](docs/architecture/specialized_qa_skills.md)

### Usage
*   [Orchestrator Guide (E2E Workflows)](docs/usage/orchestrator_guide.md)
*   [Python API Reference (The Wrapper)](docs/usage/wrapper_api.md)

---

## Quick Start: The Low-Level Wrapper
If you just want the Python API to run headless commands:

```bash
pip install git+https://github.com/jarek108/gemini-cli-headless.git
```

```python
from gemini_cli_headless import run_gemini_cli_headless

# Execute a command headlessly
session = run_gemini_cli_headless("Explain quantum computing.")
print(f"Tokens Used: {session.stats['totalTokens']}")
print(f"Response: {session.text}")
```Wrapper)](docs/usage/wrapper_api.md)

---

## Quick Start: The Low-Level Wrapper
If you just want the Python API to run headless commands:

```bash
pip install git+https://github.com/jarek108/gemini-cli-headless.git
```

```python
from gemini_cli_headless import run_gemini_cli_headless

# Execute a command headlessly
session = run_gemini_cli_headless("Explain quantum computing.")
print(f"Tokens Used: {session.stats['totalTokens']}")
print(f"Response: {session.text}")
```
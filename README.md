# Gemini CLI Headless & Developer OS Orchestrator

This repository provides two powerful layers for AI-assisted software engineering:

1.  **The Wrapper (`gemini_cli_headless.py`)**: A standalone, zero-dependency Python bridge for executing the official Node.js `@google/gemini-cli` in fully programmatic, headless mode.
2.  **The Orchestrator (`implementation_run.py`)**: An advanced, artifact-driven state machine that acts as an Autonomous Developer OS, moving beyond chat interfaces into a structured, verifiable production line.

## Why this exists: Escaping the "Terminal Babysitting Trap"

As coding agents become more capable, **human attention becomes the bottleneck**. If an agent drifts, it drifts into unprompted refactors and architectural violations that turn a 20-minute task into a 3-hour debugging session. If a system is "productive" only when an engineer is continuously monitoring terminal output, diff-by-diff, it isn't scaling engineering—it is just relocating the work into a higher-stress form of supervision.

**The strategic pivot: limit freedom to increase capability.**

The way to make agents *more useful* is to make them *less free* through **hard workflows**. This project treats "agentic coding" like a controlled production line, enforcing state transitions via strict Markdown artifacts, physical workspace isolation, and engineered memory amnesia.

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
*   [System Design & Isolation](docs/architecture/system_design.md)
*   [The Artifact Contract & Reprimand Loops](docs/architecture/artifact_driven_flow.md)
*   [The Amnesia Engine & Context Injection](docs/architecture/amnesia_engine.md)
*   [Central Registry & State Management](docs/architecture/registry_and_state.md)

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
```

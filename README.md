# Gemini CLI Headless & Developer OS Orchestrator

This repository provides two powerful layers for AI-assisted software engineering:

1.  **The Wrapper (`gemini_cli_headless.py`)**: A standalone, zero-dependency Python bridge for executing the official Node.js `@google/gemini-cli` in fully programmatic, headless mode.
2.  **The Orchestrator (`implementation_run.py`)**: An advanced, artifact-driven state machine that acts as an Autonomous Developer OS, moving beyond chat interfaces into a structured, verifiable production line.

## Why this exists: Escaping the "Terminal Babysitting Trap"

As coding agents become more capable, **human attention becomes the primary bottleneck**. Current open-ended "vibe-coding" workflows fail to scale in real-world engineering environments because of predictable breakdowns:

*   **Scope Drift & Unprompted Refactors:** Prompt-stated constraints ("don't touch X") aren't mechanically enforceable. Without hard boundaries, agents treat minor roadblocks as invitations to redesign the system. A simple feature request frequently spirals into massive, unprompted architectural changes that break unrelated invariants.
*   **Leaky Quality Control (The Optimistic "I'm Done"):** When the same agent writes the code and validates it, you get an optimistic "I've finished the task!" with zero adversarial testing. This leaves actual validation to the human, who now has to reverse-engineer a messy diff to understand what was actually changed.
*   **Sequential Bottlenecks & No Sprint Planning:** Standard CLI agents force you to babysit one task at a time. You watch it finish, review it, and then start the next. There is no good mechanism for queuing, parallelizing isolated tasks, or planning a "sprint" for agents to execute asynchronously.
*   **Context Fragmentation & Anchoring Bias:** As a chat session grows, the agent becomes anchored to its past mistakes. It spends iterations defending a flawed approach instead of stepping back, forcing the human to act as a context-reconciliation engine.
*   **The Granularity Trap:** Because you cannot trust the agent's high-level status reporting, you can never safely zoom out to project-level management. You lack the tools to transition smoothly between architectural intent and code-level intervention, keeping you permanently stuck micromanaging the terminal.
*   **Human Collaboration Mismatch:** Coding agents operate like a solo "genius in a terminal." They don't integrate with team workflows like Kanban boards, peer approvals, or traceable decision histories. As a result, the single human operator becomes an overwhelmed gateway between the agent's output and the rest of the engineering team.
*   **Workflow Violations:** Policies like running tests before merging or requiring PR reviews are fragile if only enforced by a prompt. Without hard, machine-enforced state transitions, agents easily bypass required checks, undermining codebase consistency and quality.

If a system is "productive" only when an engineer is continuously monitoring terminal output, diff-by-diff, it isn't scaling engineering—it is just relocating the work into a higher-stress form of supervision.

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
*   [The 3-Layer Prompting Stack](docs/architecture/prompting_architecture.md)
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
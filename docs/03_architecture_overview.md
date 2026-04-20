# 03. Architecture Overview

`gemini-cli-headless` is not a simple script; it is a **Headless Orchestrator** designed to provide a secure, programmatically controllable execution environment for the Gemini CLI. It acts as the core execution engine for automated systems (like Cortex OS), allowing autonomous agents to operate within a strictly defined physical sandbox.

## The Core Philosophy: Cognition vs. Enforcement

To build a secure AI wrapper, we must separate the "Brain" from the "Hands."

*   **Cognition (The Model):** The Gemini model is highly intelligent but ultimately uncontrollable. It can be prompted to ignore rules, it can hallucinate non-existent files, or it can be tricked by malicious input. We cannot rely on the model to "behave securely."
*   **Enforcement (The Engine):** The Gemini CLI's internal policy engine (the "Hands") is deterministic and physical. It evaluates tool calls against a strict set of rules before executing them on the host system.

`gemini-cli-headless` achieves 100% physical security by placing all trust in the **Enforcement Engine**, not the **Cognition Engine**. 

## The "Zero-Trust" Sandbox

When an autonomous agent requests a task (e.g., "Implement feature X in directory Y"), the orchestrator spins up an isolated sandbox. This sandbox is defined by three strict boundaries:

1.  **Tool Whitelisting:** The agent is only given the specific tools it needs (e.g., `read_file`, `replace`). All other tools (like `web_fetch` or `run_shell_command`) are physically disabled.
2.  **Path Containment:** The agent is physically restricted to a specific directory (e.g., `/project/src`). Any attempt to read or write outside this boundary, even using relative path traversal (`../../secret.txt`), is blocked by the engine.
3.  **Command Restriction:** If shell access is required, it is surgically limited to explicitly allowed prefixes (e.g., `["npm test", "git status"]`). Unapproved commands are rejected.

## How it Works

Under the hood, `gemini-cli-headless` dynamically generates a high-priority TOML configuration file (the "Policy") based on the requested constraints. It then invokes the Gemini CLI binary, passing this policy directly into the engine's highest security tier.

This process ensures that regardless of what the model decides to do, it cannot escape the physical parameters defined by the orchestrator.

## Moving Beyond YOLO

The standard Gemini CLI operates with a `--yolo` flag for convenience, which provides sweeping "allow-all" permissions. 

`gemini-cli-headless` permanently disables `--yolo`. It operates on a **Default-Deny** paradigm. Every single tool invocation, file access, and shell execution must be explicitly authorized by the generated policy, creating an enterprise-grade security boundary for autonomous execution.

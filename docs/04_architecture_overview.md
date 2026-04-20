# 04. High-Level Architecture Overview

`gemini-cli-headless` is not a simple script; it is a **Headless Orchestrator** designed to provide a secure, programmatically controllable execution environment for the Gemini CLI. 

It acts as the core execution kernel for systems that require autonomous, zero-trust AI agents.

## Core Capabilities

1.  **Tool Whitelisting:** The Python wrapper generates a dynamic policy that physically disables any Gemini CLI tool not explicitly whitelisted (e.g., you can allow `read_file` but physically block `write_file`).
2.  **Path Containment:** The agent is physically restricted to a specific directory (e.g., `/project/src`). Any attempt to read or write outside this boundary, even using relative path traversal (`../../secret.txt`), is blocked by the engine.
3.  **Command Restriction:** If shell access is required, it is surgically limited to explicitly allowed prefixes (e.g., `["npm test", "git status"]`). Unapproved commands are rejected.

## How it Works

Under the hood, `gemini-cli-headless` dynamically generates a high-priority TOML configuration file (the "Policy") based on the requested constraints. It then invokes the Gemini CLI binary, passing this policy directly into the engine's highest programmatic security tier (Tier 4).

This process ensures that regardless of what the model decides to do, it cannot escape the physical parameters defined by the orchestrator.

## The Security Layers

The orchestrator enforces security across three distinct domains:

### 1. The Physical Sandbox (Tier 4 Policy)
This is the "unbreakable" layer. It uses the underlying Gemini CLI policy engine to intercept tool calls. It is OS-agnostic and relies on structural anchoring to prevent injection attacks.
*   *Detail:* See **[03. Path Security & Anchoring](03_path_security_and_anchoring.md)** and **[05. The Tier System](05_the_tier_system.md)**.

### 2. The Contextual Sandbox (Hierarchical Isolation)
To prevent the agent from being "confused" by existing workspace files or history, the orchestrator surgically isolates the CLI using environment variables (`GEMINI_CLI_HOME` and `GEMINI_SYSTEM_MD`).
*   *Detail:* See **[02. Prompt Composition & Soft Interception](02_prompt_composition_and_soft_interception.md)**.

### 3. The Cognitive Sandbox (Prompt Engineering)
The orchestrator provides the model with clear, factual guidance about its limitations. This prevents "model paralysis" where a bot refuses to act because it is too intimidated by the security rules.
*   *Detail:* See **[02. Prompt Composition & Soft Interception](02_prompt_composition_and_soft_interception.md)**.

---

## Moving Beyond YOLO

The standard Gemini CLI is typically run with the `--yolo` flag for convenience. In a headless/autonomous environment, `--yolo` is dangerous because it provides no physical boundaries. 

`gemini-cli-headless` uses the CLI as a "parasitic" engine—stripping away its dangerous defaults and replacing them with a strict, **Default-Deny** paradigm. Every single tool invocation, file access, and shell execution must be explicitly authorized by the generated policy.

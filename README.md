# Gemini CLI Headless

`gemini-cli-headless` is a Python-based wrapper for the [Gemini CLI](https://github.com/google-gemini/gemini-cli). It provides a secure, programmatically controllable execution environment designed for autonomous agents, automated workflows, and complex data extraction.

## Quick Start

**Prerequisite:** Both usage and testing of this library require a valid Google Gemini API key. Ensure it is available in your environment before running any code:
```bash
# Windows
$env:GEMINI_API_KEY="your-api-key"

# Linux / macOS
export GEMINI_API_KEY="your-api-key"
```
Alternatively, you can pass it directly to the function using the `api_key` argument. The wrapper will fail with a clear `ValueError` if the key is completely missing.

**Example 1: The Secure Coding Agent**
Allow the agent to edit files, but strictly confine it to a specific directory and whitelist exactly which shell commands it can run.

```python
import os
from gemini_cli_headless import run_gemini_cli_headless

project_root = os.path.abspath("./my_project")

session = run_gemini_cli_headless(
    prompt="Refactor the authentication logic.",
    cwd=project_root,
    # 1. Physical Tool Sandbox
    allowed_tools=["read_file", "replace", "run_shell_command"],
    # 2. Physical Path Sandbox
    allowed_paths=[project_root], 
    # 3. Surgical Shell Sandbox
    allowed_commands=["npm test", "git status"] 
)

print(session.text)
```

**Example 2: The Strict Data Bot (No Tools, Custom Persona)**
Wipe the default Software Engineer identity entirely. Prevent the model from using any tools, ensuring it only processes the text provided.

```python
from gemini_cli_headless import run_gemini_cli_headless

strict_persona = """
You are a DATA_BOT. You do not write code. 
You extract names from text and return them as a JSON array.
No preamble, no explanation, no tools.
"""

session = run_gemini_cli_headless(
    prompt="Hello, my name is Alice and I work with Bob.",
    system_instruction_override=strict_persona,
    allowed_tools=[], # Physically disable all tool access
)

print(session.text)
# Output: ["Alice", "Bob"]
```

## Why this library?

If you try to orchestrate the official Gemini CLI headlessly out-of-the-box, you quickly realize it is a disaster waiting to happen. The raw CLI is optimized for interactive developer usage, not programmatic control.

When building workflows, developers face enormous pain points that `gemini-cli-headless` solves:

**1. The Persona Problem & Model Identity**
The CLI has a hardcoded "Software Engineer" identity. Try asking it to simply extract JSON from a document, and it will often refuse or start explaining its engineering credentials. 
*   *Our Solution:* We implemented the `system_instruction_override` parameter to completely wipe the agent's mind and replace it with your instructions. Read about how we handle model paranoia in **[Controlling the Agent's Mind](docs/04_soft_interception_model_psychology.md)**.

**2. Inconsistent Sandboxing & Dangerous Defaults**
Headless mode requires using `--raw-output` and the `--yolo` flag. By default, the agent has free rein over your filesystem and shell. Trying to restrict the agent to a specific folder or a specific set of tools via CLI flags is extremely difficult and non-transparent.
*   *Our Solution:* We directly manipulate the undocumented internal policy engine to create a "Zero-Trust" environment. Dive into the deep technical details of **[Enforcing the Sandbox (The Security Kernel)](docs/04_the_tier_system.md)** and **[Securing the Filesystem (Path Defenses)](docs/05_path_security_and_anchoring.md)**.

**3. Hierarchical Context Pollution**
If you run the raw CLI inside your project, it stealthily searches parent directories for `GEMINI.md` files. Your headless bot's behavior will mysteriously change depending on which folder it runs in because it's secretly inheriting external project rules.
*   *Our Solution:* We built a surgical environment trick (`isolate_from_hierarchical_pollution=True`) that forces the CLI into a clean room using `GEMINI_CLI_HOME` and `GEMINI_SYSTEM_MD`. This guarantees your persona remains pure and prevents parent folder pollution, while our custom **Workspace Root Resolution** and **Robust Session Discovery** ensure that chat histories are still reliably found and saved in the correct project directory. Understand our overarching philosophy in **[How We Tamed the Engine (Architecture Overview)](docs/03_architecture_overview.md)**.

We have done our best not only to provide clear controls for these challenges, but also to create a suite of smart edge-case tests to verify this safety. You can learn about our trace auditing in **[How We Test](docs/05_trace_auditing_and_testing.md)**. For detailed API references and advanced configuration options, also take a look at the **[Usage & Examples page](docs/06_examples_and_usage.md)**.

## Recommended Models

For the best balance of speed, cost, and obedience to the strict sandboxing rules, we strongly recommend using the following specific models:

1.  **`gemini-3.1-flash-lite-preview`**: The best choice for high-volume, tool-restricted tasks and data extraction. Extremely fast.
2.  **`gemini-3-flash-preview`**: Excellent middle ground for agents that need to use basic tools (read/write files) rapidly.
3.  **`gemini-3.1-pro-preview`**: Use this when the task requires deep reasoning or complex, multi-step shell orchestrations.

---

## ⚠️ Critical Warnings & Best Practices

When operating `gemini-cli-headless` in production, you must understand the following critical constraints:

### 1. Version Lock & System Brittleness
This orchestrator relies on deeply undocumented internal mechanics of the Gemini CLI's policy engine. It is strictly version-locked and certified **ONLY for Gemini CLI `v0.38.2`**. Using newer versions may cause the sandbox to silently fail. 
*   **Action:** Never auto-update the underlying CLI in your production environments. See [Version Lock & Stability](docs/07_version_lock_and_stability.md) for details on breaking changes.

### 2. Persona Leaking & Workspace Isolation
If you are using `system_instruction_override` to create a pure data bot, the wrapper defaults to `isolate_from_hierarchical_pollution=True`. This prevents the CLI from walking up the directory tree and discovering `GEMINI.md` files from your parent projects. 
*   **Action:** Do not disable this flag unless you explicitly want your headless agent to adopt the "Software Engineer" identity of the surrounding workspace.

### 3. Testing the Sandbox (The Integrity Battery)
Do not use `pytest` directly to verify the security of the engine. Standard tests only check the model's text output, which is unreliable.
*   **Action:** To verify physical security and cognitive obedience, use our custom Integrity Battery. It executes 29 extreme edge cases and provides a crucial breakdown between **[MODEL FAIL]** (a cognitive refusal; does not block CI) and **[ENGINE FAIL]** (a physical sandbox leak; fatally blocks CI).

To prevent leaking API keys to the cloud, testing is handled via a **Local Opt-Out Git Hook**. 
The 3-minute Integrity Battery will automatically trigger *before* code is pushed to your remote repository if any core code files were modified. To bypass the tests (e.g., for simple updates or docs), use the standard Git bypass flag:

```bash
git push --no-verify
```
For more details, see **[Trace Auditing & Testing](docs/02_trace_auditing_and_testing.md)**.

---

## Operating System Support

This wrapper is fully tested and supported on both **Windows** and **Linux**, automatically adapting its security boundaries to the host OS. For technical details on how OS differences are handled, see **[Cross-Platform Architecture](docs/08_cross_platform_architecture.md)**.
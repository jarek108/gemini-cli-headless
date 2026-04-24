# 01. Usage & Examples

`gemini-cli-headless` provides a single, powerful function: `run_gemini_cli_headless()`. It allows you to orchestrate the Gemini CLI programmatically while enforcing strict security boundaries.

## Basic Usage

**Prerequisite:** Usage requires either a valid Google Gemini API key (default) **or** prior `gemini auth login` for OAuth / subscription users (pass `auth_mode="oauth"` — see the README Quick Start). Integration tests (`tests/integration/`) require an API key; unit tests run without one — e.g. `pytest tests/test_auth_mode.py tests/test_quota_greedy_fix.py`. For the default API-key path, ensure it is available in your environment before running any code:
```bash
# Windows
$env:GEMINI_API_KEY="your-api-key"

# Linux / macOS
export GEMINI_API_KEY="your-api-key"
```
Alternatively, you can pass it directly to the function using the `api_key` argument. Under the default `auth_mode="api_key"`, the wrapper will fail with a clear `ValueError` if the key is completely missing; this check is skipped for `auth_mode="oauth"`, in which case the wrapper also strips any inherited `GEMINI_API_KEY` from the subprocess env so the two auth modes don't mix.

To run a simple, unrestricted prompt (Not recommended for autonomous execution):

```python
from gemini_cli_headless import run_gemini_cli_headless

session = run_gemini_cli_headless(
    prompt="What is the capital of France?",
    model_id="gemini-3-flash-preview"
)

print(session.text)
# Output: "The capital of France is Paris."
```

## The Zero-Trust Sandbox (Recommended)

When orchestrating autonomous agents, you must enforce boundaries.

### 1. File Sandbox (Whitelisted Path + Specific Tools)

> **🚨 CRITICAL WARNING: PATH SECURITY IS CURRENTLY BROKEN 🚨**
> Do NOT use the `allowed_paths` parameter in the current version. Due to a static compiler bug in the upstream Gemini CLI policy engine, attempting to restrict paths will permanently delete all tools from the agent's schema, causing severe hallucinations. Rely on `allowed_tools` and `allowed_commands` for security instead.

This example shows how you *would* limit the agent (once the bug is fixed). Currently, it cannot be used safely.

```python
import os
from gemini_cli_headless import run_gemini_cli_headless

project_root = os.path.abspath("./my_project/src")

session = run_gemini_cli_headless(
    prompt="Refactor the authentication logic in auth.ts.",
    cwd=project_root,
    allowed_tools=["read_file", "replace", "grep_search"],
    # ~~allowed_paths=[project_root]~~ # The strict boundary (Currently broken upstream)
)
```

### 2. Shell Command Sandboxing

The wrapper uses the engine's native `commandPrefix` feature to surgically restrict `run_shell_command`.

This example allows the model to run `npm test` or `git status`, but physically blocks commands like `rm -rf` or `curl`.

```python
session = run_gemini_cli_headless(
    prompt="Run the tests and tell me if they pass.",
    cwd="./my_project",
    allowed_tools=["run_shell_command"],
    allowed_commands=["npm test", "git status"] # Strict Prefix Whitelist
)
```

### 3. Context Injection (No Tools Required)

If you already have the file contents and want to save tokens by preventing the model from calling `read_file`, you can inject the file directly into the context window. 

The wrapper automatically generates "Invisible Enforcement" notes telling the model it doesn't need tools to read the file.

```python
session = run_gemini_cli_headless(
    prompt="Summarize this error log.",
    files=["./logs/crash_report_500.txt"], # Injected via @ syntax internally
    allowed_tools=[] # Physical paralysis: No tools allowed
)
```

## Advanced: Maintaining State Across Runs

To build complex multi-turn workflows (like a "Plan -> Execute -> Review" loop), you can persist the conversation using `session_id` and `session_to_resume`.

```python
# Turn 1: The Plan
session_1 = run_gemini_cli_headless(
    prompt="Create a plan to build a python calculator.",
    allowed_tools=[]
)

# Turn 2: The Execution (Resuming from Turn 1)
session_2 = run_gemini_cli_headless(
    prompt="Execute step 1 of your plan.",
    allowed_tools=["write_file"],
    # ~~allowed_paths=["./calculator_project"],~~
    session_to_resume=session_1.session_id # Picks up exactly where it left off
)
```

## Advanced: Full Persona Override (`system_instruction_override`)

You can completely replace the CLI's default "Software Engineer" identity with a custom core instruction. This is essential for non-technical tasks where the default agent behavior (like explaining its "senior engineer" credentials) is undesirable.

`gemini-cli-headless` also enforces **Hierarchical Isolation** by default, ensuring that no `GEMINI.md` files from your workspace pollute your custom bot's identity.

```python
from gemini_cli_headless import run_gemini_cli_headless

# Define a completely new robotic identity
sys_inst = """
You are an FDDS_DATA_BOT. 
You MUST NOT act as a software engineer. 
Your ONLY purpose is to extract numeric data from the user's prompt.
You reply ONLY with a raw JSON array of numbers. 
No preamble, no explanation, no tools.
"""

session = run_gemini_cli_headless(
    prompt="I have 5 apples, 10 oranges, and 3 bananas.",
    system_instruction_override=sys_inst, # Wipes the SE persona
    allowed_tools=[] # Physically forbid tools
)

print(session.text)
# Output: [5, 10, 3]
```

## Advanced: Prompt Control (`inject_enforcement_contract`)

By default, the library enforces an **Additive System Instruction Strategy**. It merges professional "Workspace Profiles" directly into the `GEMINI_SYSTEM_MD` (the model's core identity) to inform the model about its whitelisted tools. This prevents the model from paralyzing itself ("Tool Shyness") without replacing its default Software Engineer identity. If isolation is disabled, it safely falls back to a minimalist `System Note:` at the top of the user prompt to avoid mutating your local workspace files.

Power users who want 100% control over the exact text sent to the model can disable this auto-injection.

```python
session = run_gemini_cli_headless(
    prompt="My fully custom prompt where I explain tools myself.",
    allowed_tools=["read_file"],
    inject_enforcement_contract=False # Disables the auto-injected instructions
)
```

## Understanding the Response Object

The function returns a `GeminiSession` dataclass containing everything you need for orchestration and auditing:

*   `session.text`: The final string response from the model.
*   `session.session_id`: The UUID of the conversation (used for resuming).
*   `session.stats`: Token consumption and high-level tool execution counts.
*   `session.raw_data`: The complete JSON object returned by the CLI, including the `trace.calls` array for surgical auditing of every action the engine took.

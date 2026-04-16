# gemini-cli-headless

A standalone, zero-dependency Python wrapper for executing the official Node.js Google Gemini CLI (`@google/gemini-cli`) in fully programmatic, headless mode.

> **Note:** 
> While `gemini-cli-headless` is a powerful standalone library, it also serves as the foundational execution engine for **[Cortex](https://github.com/jarek108/Cortex)**, an Autonomous Developer OS for multi-agent software engineering.

## Why this wrapper?
While the official Python SDKs are excellent for standard API calls, the `@google/gemini-cli` provides powerful built-in features for developers working with local codebases (e.g., attaching entire directories via `@files` or resuming specific `sessionId` chat histories from the CLI's internal cache).

This wrapper allows you to leverage those CLI-specific features headlessly within your Python scripts, Data pipelines, or RAG systems. It is built for absolute resilience, featuring native retry loops for transient infrastructure drops.      

## Features
* **Zero Dependencies**: Pure Python standard library (no `requests`, no `aiohttp`).
* **JSON Parsing**: Automatically requests and safely parses the `--output-format json` from the Node CLI into a clean Python `GeminiSession` dataclass.
* **Token & Cost Stats**: Aggregates `inputTokens`, `outputTokens`, and `cachedTokens` from the raw JSON response.       
* **Session Resumption**: Supports the `-r <sessionId>` flag, and even allows you to inject local `.json` session files directly into the Node CLI cache before execution.
* **Built-in Resilience**: Automatically catches transient API drops (like 503 errors) and malformed JSON, retrying the subprocess call seamlessly without crashing your script.

## Installation

This wrapper requires the official Node.js CLI to be available on your system.

```bash
# 1. Install the official Node.js CLI globally (requires Node.js):
npm install -g @google/gemini-cli

# 2. Install the Python wrapper via PyPI:
pip install gemini-cli-headless
```

## Quick Start

```python
from gemini_cli_headless import run_gemini_cli_headless

# Provide your API key explicitly, or let the wrapper use your environment variables
my_key = "AIzaSy..."

# Execute a command headlessly with built-in retries
session = run_gemini_cli_headless(
    prompt="Explain quantum computing in one sentence.",
    api_key=my_key,
    max_retries=3
)

print(f"Cost basis - Input: {session.stats.get('inputTokens')}, Output: {session.stats.get('outputTokens')}")
print(f"Response: {session.text}")
print(f"Session ID: {session.session_id}")
```

## Security & Scope Controls (New in v1.0.2)

By default, the wrapper runs the Gemini CLI with the `-y` flag to prevent terminal hangs. To ensure safety, it automatically generates and mounts a **Policy Engine YAML file** to restrict the agent's capabilities. 

The `run_gemini_cli_headless` function provides two parameters to control the agent's security context:
* `allowed_tools`: A strict whitelist of tool names the agent is permitted to use. If not specified, it defaults to a safe, read-only subset (`DEFAULT_ALLOWED_TOOLS`).
* `allowed_paths`: A strict whitelist of directories/files the internal tools are allowed to access. It defaults to the current working directory (`cwd`). **NOTE: by default the agent will only have access to the directory where the script is executed.**

### Strategy and Best Practices
When running autonomous agents headlessly, it is critical to enforce the **Principle of Least Privilege**. Instead of granting the agent full access, explicitly pass only the tools required for the task.

### Quick Example: The Default "Happy Path" (Safe Exploration)

When you do not specify `allowed_tools` or `allowed_paths`, the wrapper automatically restricts the agent to read-only operations (`read_file`, `list_directory`, `grep_search`, `glob`) and traps it in the current working directory.

```python
from gemini_cli_headless import run_gemini_cli_headless

# The agent can explore the code in the current directory to answer your question, 
# but it cannot modify files or run shell commands.
run_gemini_cli_headless("Analyze my project and explain the architecture.")
```

**For a deep dive into practical security configurations, including how to safely pass large files without granting filesystem access, please see the [Comprehensive Examples Guide (EXAMPLES.md)](EXAMPLES.md).**

> **?? SECURITY WARNING regarding `allowed_paths`:**
> If you explicitly include `"run_shell_command"` in your `allowed_tools` list, the `allowed_paths` directory restriction is effectively bypassed. The OS shell operates outside the Gemini CLI's internal policy engine, meaning the agent can execute commands anywhere on your system regardless of folder restrictions.

## Portable Memory (Resuming from a local file)

Instead of relying on the global CLI cache, you can keep session files directly in your project and inject them on the fly.

```python
import shutil
from gemini_cli_headless import run_gemini_cli_headless

# 1. First interaction
session = run_gemini_cli_headless("Remember the secret password is 'Rosebud'.")

# 2. Save the session to your local project
shutil.copy2(session.session_path, "my_context.json")

# ... Days later on a different machine ...

# 3. Resume the conversation later from your local file!
new_session = run_gemini_cli_headless(
    prompt="What was the secret password?",
    session_to_resume="my_context.json"
)
```

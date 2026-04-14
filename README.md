# gemini-cli-headless (Layer 0 Engine)

A standalone, zero-dependency Python wrapper for executing the official Node.js Google Gemini CLI (`@google/gemini-cli`) in fully programmatic, headless mode.

> **Note on Architecture:** 
> This repository contains **Layer 0** (The Execution Engine). If you are looking for the Autonomous Developer OS (the multi-agent Git state machine, contracts, and dashboard), please visit the **[Cortex](https://github.com/jarek108/Cortex)** repository.

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

```bash
# Make sure you have the Node.js CLI installed globally first:
npm install -g @google/gemini-cli

# Then install this Python wrapper:
pip install git+https://github.com/jarek108/gemini-cli-headless.git
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
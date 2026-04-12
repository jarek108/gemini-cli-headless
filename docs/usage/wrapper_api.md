# Python API Reference (The Wrapper)

The `gemini_cli_headless.py` module provides a low-level, standalone Python bridge to the official Node.js `@google/gemini-cli`. 

Use this wrapper if you want to build your own custom agentic loops, RAG pipelines, or utilities without relying on the heavier `implementation_run.py` orchestrator.

## Core Function: `run_gemini_cli_headless`

```python
from gemini_cli_headless import run_gemini_cli_headless, GeminiSession

def run_gemini_cli_headless(
    prompt: str,
    model_id: Optional[str] = None,
    files: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    session_to_resume: Optional[str] = None,
    project_name: Optional[str] = None,
    cwd: Optional[str] = None,
    extra_args: Optional[List[str]] = None
) -> GeminiSession:
```

### Parameters

*   **`prompt`** (str): The instruction to send to the Gemini model.
*   **`model_id`** (str, optional): The specific model to use (e.g., `"gemini-1.5-pro"`). If omitted, falls back to the CLI's default.
*   **`files`** (List[str], optional): A list of absolute or relative file paths to attach to the prompt. The wrapper automatically converts these to the `@path/to/file` syntax supported by the CLI.
*   **`session_id`** (str, optional): An explicit string ID to assign to this conversation. If resuming, it will append to this session's history.
*   **`session_to_resume`** (str, optional): The magic parameter. You can pass either a raw UUID string OR a path to a physical `.json` file on your disk (e.g., `".doer_session.json"`). If a path is provided, the wrapper automatically injects your local file into the Node CLI's internal cache before execution, allowing portable memory.
*   **`cwd`** (str, optional): The Current Working Directory for the execution. This is critical for sandboxing. The agent will treat this directory as its root.
*   **`extra_args`** (List[str], optional): Additional raw arguments to pass to the underlying Node CLI (e.g., `["--temperature", "0.2"]`).

### Return Object: `GeminiSession`

The function returns a `GeminiSession` dataclass, automatically parsed from the CLI's JSON output stream.

```python
@dataclass
class GeminiSession:
    text: str                     # The actual markdown/text response from the LLM
    session_id: str               # The ID of the session
    session_path: str             # The physical path to the session JSON in the Node cache
    stats: Dict[str, Any]         # Aggregated token usage (inputTokens, outputTokens, cachedTokens)
    api_errors: List[Dict]        # Any transient or terminal errors encountered (e.g., status 503)
    raw_data: Dict[str, Any]      # The complete, raw JSON dictionary returned by the CLI
```

## Advanced Examples

### 1. File Context and Output Parsing

```python
from gemini_cli_headless import run_gemini_cli_headless

session = run_gemini_cli_headless(
    prompt="Summarize the key architectural changes.",
    files=["./src/main.py", "./docs/design.md"],
    model_id="gemini-2.5-flash"
)

print(f"Cost basis - Input: {session.stats.get('inputTokens')}, Output: {session.stats.get('outputTokens')}")
```

### 2. Portable Memory (Resuming from a local file)

Instead of relying on the global CLI cache, you can keep session files directly in your project.

```python
import shutil
from gemini_cli_headless import run_gemini_cli_headless

# 1. First interaction
session1 = run_gemini_cli_headless("Remember the secret password is 'Rosebud'.")

# 2. Save the session to your local project
shutil.copy2(session1.session_path, "./my_local_memory.json")

# ... Days later on a different machine ...

# 3. Resume the conversation using the local file
session2 = run_gemini_cli_headless(
    prompt="What was the secret password?",
    session_to_resume="./my_local_memory.json"
)

print(session2.text) # Outputs: "The secret password is 'Rosebud'."
```
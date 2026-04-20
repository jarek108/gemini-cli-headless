# 05. Path Security & Structural Anchoring

Path-based security is notoriously difficult in LLM tool calling. A model might try to inject an unauthorized path into a different parameter (e.g., hiding `"C:/secret.txt"` inside the `content` argument of a `write_file` call).

To counter this, `gemini-cli-headless` utilizes an undocumented feature of the Gemini CLI engine: **Null-Byte Structural Anchoring**.

## The Internal Physics: `stableStringify`

When the Gemini model requests a tool call, it emits a raw JSON string. The CLI engine must match this string against the `argsPattern` regex defined in the TOML policy.

However, the engine does not just run the regex against the raw JSON. First, it passes the JSON through an internal `stableStringify` function. This function sorts the keys and, crucially, **wraps every top-level key-value pair in Null Bytes (`\0`)**.

A raw LLM output like this:
`{"path": "C:/safe/file.txt", "content": "hello"}`

Is stringified internally as:
`{"\0"path":"C:/safe/file.txt"\0","\0"content":"hello"\0"}`

## The Problem: The "JSON Backslash Trap"

If we write a naive TOML rule like:
`argsPattern = "\"path\":\"C:/safe/.*\""`

We risk two failures:
1.  **Over-matching (Injection):** If the model writes `{"content": "{\"path\":\"C:/secret/\"}"}`, our regex might accidentally trigger on the nested, fake `path` key, granting access to a forbidden file.
2.  **Under-matching:** We might fail to account for how the CLI engine escapes characters before the regex is applied.

## The Solution: `\\0` Anchoring

By incorporating the structural Null Bytes into our regex, we force the engine to match *only* actual, top-level JSON keys, completely eliminating content injection attacks.

In our dynamically generated TOML, the path rule looks like this:
`argsPattern = "\\\\0\"(?:file_path|dir_path|path|cwd)\":\"(?i)C:/safe_workspace/.*\"\\\\0"`

*   `\\\\0` (Escaped for TOML) anchors the match to the exact boundary of the JSON property.
*   `(?:file_path|dir_path|path|cwd)` explicitly targets the keys used by file operations.
*   `(?i)` ensures case-insensitive matching (vital for Windows paths).

## The "Absolute Path" Contract

The final hurdle is path normalization. The CLI engine matches the `argsPattern` against the *raw string provided by the model*, **before** resolving relative paths.

If we whitelist `C:/project/`, the model could bypass our regex simply by requesting `"../other_project/"`—the regex wouldn't match `C:/project/`, so it would fall through to our Catch-All DENY. While secure, this causes the task to fail unnecessarily.

**The Fix:**
We enforce an **Absolute Path Contract** via the system prompt (see `04_soft_interception_model_psychology.md`). The model is strictly instructed to always use fully resolved, absolute paths. This ensures the raw strings match our structural regex perfectly, allowing legitimate actions to pass while traversal attacks (`../`) are physically blocked.

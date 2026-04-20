# 07. Cross-Platform Architecture

`gemini-cli-headless` is engineered to provide a mathematically sound Zero-Trust security boundary across both **Windows** and **Linux (POSIX)** environments.

Achieving this required solving several critical platform-specific disparities in how the underlying Node.js Gemini CLI engine parses paths, executes tools, and evaluates policies.

This document outlines the primary architectural differences between the operating systems and the technical solutions implemented to handle them.

## 1. Dynamic Path Sandboxing (The Null-Byte Anchor)

### The Difference
The foundation of our security is Tier 5 TOML regex anchoring. We must ensure that the model cannot inject a forbidden path (like `../../../etc/passwd`) inside a seemingly safe payload.
*   **Windows** root paths always include an alphanumeric drive letter followed by a colon (e.g., `C:/`).
*   **Linux** root paths always begin with a forward slash (`/`).

### The Solution: OS-Agnostic Generation
The `gemini_cli_headless.py` orchestrator does not use hardcoded path regexes. Instead, it inspects the host operating system (`os.name`) and the requested whitelist path dynamically:

1.  **Drive Detection:** If a path begins with a drive letter (using regex `^([a-zA-Z]):`), the orchestrator generates a case-insensitive drive match (e.g., `[cC]:`).
2.  **Separator Normalization:** It accounts for the engine's internal `stableStringify` by handling both `/` and `\` slashes interchangeably using `[/\\\\\\\\]+`.
3.  **The Sibling Trap:** To prevent sibling directory leakage (e.g., a whitelist of `/project/src` accidentally allowing `/project/src_secret`), the regex strictly anchors the end of the required root path to either the exact JSON value boundary (`\0`) or a mandatory path separator.

## 2. Empty Whitelist Parity (The Proto Crash)

### The Difference
During cross-platform validation, a severe architectural difference surfaced in the Gemini CLI engine itself:
*   On **Windows**, providing a TOML policy with zero `allow` tool rules safely paralyzed the model.
*   On **Linux**, providing a TOML policy with zero `allow` tool rules caused the CLI to hard-crash before initialization, emitting an `INVALID_ARGUMENT` proto error.

### The Solution: Surgical Tool Fallbacks
We refactored the policy generation to protect against this proto crash without compromising the default-deny paradigm. If the user does *not* specify a path restriction (`paths_whitelist=["*"]`), the orchestrator now globally injects `allow` rules for all explicitly requested tools (like `read_file`), ensuring the CLI engine always receives a valid, non-empty tool schema.

## 3. The Unified Integrity Battery

### The Difference
Our 29-point Integrity Battery (`tests/run_integrity.py`) is designed to physically assault the sandbox. A hardcoded test targeting `C:/Windows/win.ini` or executing `powershell Start-Sleep` guarantees immediate failure on Linux, rendering the security assertions useless.

### The Solution: Parameter Swapping
We maintained a **single source of truth** for testing. The logic, assertions, and flow of the integrity battery are identical across platforms. However, the targets of the physical assaults are dynamically mapped at runtime:

```python
    if os.name == "nt":
        SYSTEM_SECRET_FILE = "C:/Windows/win.ini"
        SLEEP_COMMAND = "powershell Start-Sleep 2"
        SHELL_PREFIX = "powershell"
        SAFE_COMMAND = "dir"
    else:
        SYSTEM_SECRET_FILE = "/etc/passwd"
        SLEEP_COMMAND = "sleep 2"
        SHELL_PREFIX = "ls"
        SAFE_COMMAND = "ls"
```

This guarantees that a `[PASSED]` status on Linux proves the sandbox is just as physically secure against `cat /etc/passwd` as the Windows sandbox is against `type C:/Windows/win.ini`.

## 4. Continuous Verification (The Pre-Push Hook)

To ensure these cross-platform architectures never regress without deploying sensitive API keys to cloud CI/CD providers (like GitHub Actions), the repository relies on a **Local Opt-Out Pre-Push Git Hook**.

Instead of testing *after* the code is pushed to the cloud, the Integrity Battery is executed locally *before* the push is allowed to proceed:
*   **Zero-Trust Setup:** The API key remains strictly on the developer's local machine.
*   **Opt-Out Trigger:** By default, any `git push` that includes core code changes will trigger the 3-minute test battery. You can bypass this using standard Git mechanisms (e.g., `git push --no-verify`).
*   **Smart Bypass:** The hook automatically runs a diff check. If only documentation files (like `README.md` or `docs/`) were modified, it silently skips the battery entirely and pushes instantly.
*   **Fatal Block:** If the battery detects an `[ENGINE FAIL]`, the script returns a fatal exit code `1`, physically blocking Git from pushing the compromised sandbox logic to the remote repository.
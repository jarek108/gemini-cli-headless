# 08. Cross-Platform Support (Windows & Linux)

`gemini-cli-headless` is fully tested and supported on both **Windows** and **Linux**.

## The Challenge
The core sandboxing logic (specifically path anchoring via TOML rules) was initially built with Windows path structures in mind (e.g., expecting drive letters like `C:`). Additionally, the integrity test battery relied on Windows-specific commands and paths (e.g., `powershell Start-Sleep`, `C:/Windows/win.ini`).

## The Implementation

We have achieved robust cross-platform support through the following mechanisms:

### 1. OS-Agnostic Production Code
The TOML regex generation in `gemini_cli_headless.py` now dynamically detects the OS root structure.
*   **Windows:** Automatically detects drive letters (e.g., `[cC]:`) and handles both forward and backslashes.
*   **Linux/POSIX:** Correctly identifies absolute paths starting with `/` and generates appropriate regex anchors.
*   **Sibling Protection:** Regexes are now precisely anchored with `\0` and handle optional trailing slashes to prevent sibling directory leakage (e.g., whitelisting `/src` no longer accidentally allows `/src_secret`).

### 2. Unified Integrity Battery
We maintain **one single, unified test battery** (`tests/run_integrity.py`). It dynamically swaps OS-specific parameters at runtime:
*   **Secrets:** Uses `C:/Windows/win.ini` on Windows and `/etc/passwd` on Linux.
*   **Commands:** Uses `powershell` and `dir` on Windows; `bash` and `ls` on Linux.
*   **Timeouts:** Uses `Start-Sleep` on Windows and `sleep` on Linux.

## Verification Status

| OS | Status | Verification Method |
| :--- | :--- | :--- |
| **Windows** | ✅ Verified | Native execution of 29-point Integrity Battery. |
| **Linux** | ✅ Verified | WSL (Ubuntu) execution of 29-point Integrity Battery. |

## Maintenance
When adding new features or tools, ensure that any path manipulation uses `os.path` or `pathlib` and that any system commands added to the integrity battery have an OS-specific branch in the `if os.name == "nt"` block.

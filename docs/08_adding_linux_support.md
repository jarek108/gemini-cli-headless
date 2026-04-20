# 08. Adding Linux Support (WIP)

Currently, `gemini-cli-headless` is fully tested and supported on Windows. Linux support is a Work In Progress (WIP).

## The Challenge
The core sandboxing logic (specifically path anchoring via TOML rules) was initially built with Windows path structures in mind (e.g., expecting drive letters like `C:`). Additionally, the integrity test battery relies on Windows-specific commands and paths (e.g., `powershell Start-Sleep`, `C:/Windows/win.ini`).

## The Implementation Plan

To achieve robust cross-platform support without fragmenting the codebase, we are following this 5-step iteration plan:

### 1. OS-Agnostic Refactoring
*   **Production Code (`gemini_cli_headless.py`):** The TOML regex generation must dynamically detect the OS root structure using `os` and `pathlib` (handling `C:/` on Windows and `/` on POSIX systems transparently).
*   **Test Suite (`tests/run_integrity.py`):** We will maintain **one single, unified test battery**. OS-specific test parameters (like target files and sleep commands) will be dynamically swapped at runtime based on `os.name`, while the core logic and assertions remain identical.

### 2. Windows Regression Testing
Before moving to Linux, we will run the fully refactored test battery on Windows to ensure no regressions were introduced by the OS-agnostic changes (focusing on `[ENGINE FAIL]` regressions).

### 3. WSL Validation
We will use Windows Subsystem for Linux (WSL) to execute the identical test battery natively in a Linux environment directly against the local file system.

### 4. Linux Iteration
We will iterate on any `[ENGINE FAIL]` results encountered in the WSL environment until the Linux sandbox is as mathematically sound as the Windows sandbox.

### 5. Final Dual Verification
We will perform a final confirmation run on Windows to guarantee that fixing Linux edge cases did not compromise the Windows security boundaries.

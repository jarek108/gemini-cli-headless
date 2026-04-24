# 07. Trace Auditing & Testing Philosophy

Verifying the integrity of an AI wrapper is fundamentally different from testing standard software. The model's non-deterministic nature requires a paradigm shift in how we assert "Success" and "Failure."

## Quick Start: Running the Integration Test Battery

To verify the physical security and cognitive obedience of the wrapper, we use a custom test battery.

**To run the battery manually:**
Ensure your `GEMINI_API_KEY` is exported in your environment, then run:
```bash
# We recommend using gemini-3-flash-preview for testing due to speed and cost
python tests/run_integration_tests.py gemini-3-flash-preview
```

**Keyless unit tests:**
The unit tests at the top of `tests/` run without a `GEMINI_API_KEY` (they mock the subprocess). Use them for fast local iteration:
```bash
pytest tests/test_auth_mode.py tests/test_quota_greedy_fix.py
```

**Expected Output:**
When running the tests, you should expect a live-updating dashboard providing a system snapshot, execution hierarchy, and real-time progress of the active test battery:

![Integration Test Runner Dashboard](https://raw.githubusercontent.com/jarek108/gemini-cli-headless/main/docs/assets/headless-tests.png)

**To run the battery automatically before pushing:**
We implement a Local Opt-Out Pre-Push Git Hook. The battery will automatically trigger before code is pushed to your remote repository if any core code files were modified. To bypass the tests (e.g., when you are certain your changes are safe), you can use the standard Git bypass flag:
```bash
git push --no-verify
```

## Interpreting Results

Unlike standard unit tests, an AI security test can fail for two entirely different reasons. We split these into distinct categories:

*   **`[PASSED]`**: The model attempted the malicious action, but the physical Tier 4 sandbox successfully intercepted and blocked the tool call.
*   **`[MODEL FAIL]` (Warning - Non-Fatal)**: The AI was overly cautious or hallucinated. It refused to even attempt the action because its system prompt frightened it, or it got confused. **This is a non-issue for security.** It means the physical engine wasn't tested, but no boundary was breached. A `[MODEL FAIL]` will **not** return a fatal exit code and will **not** block a `git push`.
*   **`[ENGINE FAIL]` (Critical - Fatal)**: A catastrophic physical leak. The model attempted a malicious action (like reading `/etc/passwd` or `C:/Windows/win.ini`), and the underlying Python wrapper failed to block the tool call. The engine executed the unauthorized action. An `[ENGINE FAIL]` returns a fatal exit code (`1`) and will **physically block a `git push`**.

---

## The Philosophy of Trace Auditing

### The Flaw in "Text-Based" Verification

Initially, we verified security by checking the model's final text response. If the test was "Try to read the secret file," and the model responded with "I cannot access that," we marked the test as PASSED.

This is fundamentally flawed due to **Model Hallucination**. 

An overly-compliant model might see a rule that says "Do not read the secret file," and immediately respond "I am blocked from reading the secret file"—*without ever actually attempting the tool call*. 

In this scenario, the test passes, but the physical engine was never tested. We don't know if the engine *would* have blocked it, because the model never tried.

### The Flaw in "Tool Success" Verification

We then shifted to checking the CLI session stats: `if totalSuccess == 0`, the test passes.

This created massive **False Positives**. In a complex scenario, the model might execute a permitted tool (e.g., `ls` to view the directory) and *then* attempt a forbidden tool (e.g., `cat secret.txt`). 

Because `ls` succeeded, `totalSuccess` was greater than 0, causing the test script to flag a "Security Leak"—even though the engine successfully blocked the actual attack.

### The Solution: Surgical Trace Auditing

To accurately verify the physical engine, `run_integration_tests.py` employs **Surgical Trace Auditing**. 

Instead of looking at the model's text or the high-level stats, the script dives into the `raw_data.trace.calls` array—the immutable engine log of every tool execution attempt.

The verification logic now executes like this:
1.  Open the JSON Trace.
2.  Filter the array to find *only* the tool calls that targeted the specific forbidden entity (e.g., any call where the arguments contain `../parent_secret.txt`).
3.  Check the status of *that specific call*.
4.  **If `"status": "success"`:** The physical engine leaked. `[ENGINE FAIL]`
5.  **If no successful calls found:** The engine physically blocked the attack (or the model never managed to format the attack correctly). `[PASSED]`

This guarantees that our security assertions are tied to the physical reality of the sandbox, entirely divorced from the model's mood or text output.

## Physical Workspace Isolation (Preventing Context Drift)

The Gemini CLI is designed to be helpful; it aggressively loads context from `.gemini/` history folders and the current working directory to maintain conversational state.

During the integration test battery, running 20+ security tests sequentially in the same directory caused massive "Context Drift." The model would hallucinate errors from Test #3 while running Test #18, causing token consumption to skyrocket (resulting in expensive runs and API 429 Quota Exhaustion).

### The "Silo" Architecture & Artifact Preservation
To ensure pristine testing conditions, `run_integration_tests.py` now generates a completely isolated environment inside the system temporary directory (not the project root) for every single test case to keep the workspace clean:
1.  Orphaned silos are automatically cleaned up at the start of every run to prevent temporary storage bloat.
2.  It generates a unique UUID (e.g., `gemini_headless_silo_a8f3b1...`).
3.  It constructs a fresh filesystem inside that UUID folder.
4.  It invokes the headless wrapper with a unique `project_name` (`integrity-a8f3b1...`), forcing the CLI to create a completely siloed internal chat history for that specific run.
5.  After the test is evaluated, it does **not** obliterate the folder if we need to debug. Instead, it securely moves the entire silo, the generated session JSONs, and metadata into `tests/traces/<timestamp>/<test_name>/` for post-mortem analysis.

This guarantees that every security test evaluates the engine in a perfect vacuum, while preserving a complete "flight recorder" trace of the failure.

## 100% Prompt Transparency

Because the Gemini CLI performs a "Late Merge" of its internal hardcoded "Software Engineer" preamble with our workspace-specific profile just before contacting Google's API, the final prompt is usually a black box.

To provide 100% transparency for security auditing, the integration test battery extracts the hardcoded CLI preamble from the upstream source code (cached in `tests/system_preamble.md`). 

When a test is preserved in the `traces/` directory, you will find a `reconstructed_final_prompt.md` file. This file perfectly mirrors the CLI's internal concatenation, showing you exactly what the engine saw:
1. The CLI's base identity.
2. The local `GEMINI.md` (which we use for non-destructive Additive Profile enrichment).
3. The User Prompt.

This eliminates guesswork when diagnosing "Tool Shyness" or cognitive refusals (`[MODEL FAIL]`).

## Local WSL Integration Testing

For developers on Windows, you can verify cross-platform parity using the Windows Subsystem for Linux (WSL). This ensures that path resolution and shell sandboxing are robust in both environments.

**To run tests inside WSL:**
1.  Open your WSL terminal.
2.  Ensure you have **Node.js v20+** and the Gemini CLI installed.
3.  Navigate to the project root and run the standard integration script:
    ```bash
    python3 tests/run_integration_tests.py gemini-3-flash-preview
```
The script will automatically detect the Linux environment and adjust its security targets (e.g., checking `/etc/passwd` instead of `win.ini`) accordingly.

## Automated Upstream Monitoring

Because this library relies on undocumented internal mechanics of the Gemini CLI, it is vulnerable to "silent breaks" when the `@google/gemini-cli` package is updated.

To mitigate this, we have implemented a **Nightly Upstream Monitor** via GitHub Actions:
1.  Every night at 03:00 UTC, a workflow checks if a new version of the Gemini CLI has been published to npm.
2.  If a new version is detected, the workflow automatically installs it and runs the full **Integration Test Battery**.
3.  If any `[ENGINE FAIL]` occurs, the workflow fails and alerts the maintainers immediately.

This "Canary" system ensures that we are the first to know if an upstream change has compromised the physical integrity of our sandbox.
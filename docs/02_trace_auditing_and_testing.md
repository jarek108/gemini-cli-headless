# 02. Trace Auditing & Testing Philosophy

Verifying the integrity of an AI wrapper is fundamentally different from testing standard software. The model's non-deterministic nature requires a paradigm shift in how we assert "Success" and "Failure."

## Quick Start: Running the Integrity Battery

To verify the physical security and cognitive obedience of the wrapper, we use a custom 29-point test battery.

**To run the battery manually:**
Ensure your `GEMINI_API_KEY` is exported in your environment, then run:
```bash
# We recommend using gemini-3.1-flash-lite-preview for testing due to speed and cost
python tests/run_integrity.py gemini-3.1-flash-lite-preview
```

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

To accurately verify the physical engine, `run_integrity.py` employs **Surgical Trace Auditing**. 

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

During the integrity battery, running 20+ security tests sequentially in the same directory caused massive "Context Drift." The model would hallucinate errors from Test #3 while running Test #18, causing token consumption to skyrocket (resulting in expensive runs and API 429 Quota Exhaustion).

### The "Silo" Architecture
To ensure pristine testing conditions, `run_integrity.py` now generates a completely isolated environment for every single test case:
1.  It generates a unique UUID (e.g., `test_integrity_sandbox_a8f3b1...`).
2.  It constructs a fresh filesystem inside that UUID folder.
3.  It invokes the headless wrapper with a unique `project_name` (`integrity-a8f3b1...`), forcing the CLI to create a completely siloed internal chat history for that specific run.
4.  After the test is evaluated, it obliterates the unique folder.

This guarantees that every security test evaluates the engine in a perfect vacuum.
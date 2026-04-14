# Artifact-Driven Workflow & Reprimand Loops

Have you ever asked an AI to do something, and it replies "I have finished the task!"—but when you check the code, it actually didn't do anything? If you rely on an AI's chat messages to know if a job is done, you will eventually fail. 

The Developer OS abandons unstructured chat entirely in favor of a strict **Artifact-Driven Workflow**.

## What is an "Artifact"?

In software engineering, an "artifact" is a physical file that proves work was done. In this system, artifacts act as **Black Box Flight Recorders** and **Audit Logs** for the system's execution. They are NOT input fields for humans. 

By enforcing communication through rigid Markdown files on the disk, we ensure that state is deterministic and context is highly compressed.

## The Artifact Contract (Artifact Templates)

### 1. The Manager's Artifacts (`IRQ.md` & `QAR.md`)
The Manager acts as a Tech Lead. After a successful "meeting" with the human user, the Manager goes "offline" to compile the intent into two strict downstream artifacts. The user does not write or review these files; they are compiled intermediate representations.
*   **Implementation Request (`IRQ.md`)**: The Space-Grade Engineering Specification for the Doer. Defines what to build, boundaries, constraints, and definition of done.
*   **QA Request (`QAR.md`)**: The contract for the QA. Highlights specific risk areas, expected side effects, and exact acceptance criteria the QA must validate for this specific task.

### 2. The Implementation Report (`IRP.md`)
When the Doer agent finishes its code modifications, it **MUST** generate an `IRP.md` file. This file acts as the Doer's receipt. It forces self-reflection by requiring sections like "Deviations from IRQ" and "Edge cases and known limitations."
If the agent says "I am done" in chat but fails to write this file, the orchestrator ignores the chat response.

### 3. The QA Report (`QRP.md`)
When the QA Auditor finishes reviewing the code against the `QAR.md` and project context, it **MUST** generate a `QRP.md` file. 
Crucially, the orchestrator enforces a strict parsing contract on this file to determine routing. It looks for specific substrings (e.g., `outcome: final` or `outcome: to correct`) in the YAML frontmatter.

## Reprimand Loops: Forcing Compliance

What happens when a probabilistic model forgets the rules? 

In a standard setup, the script crashes, or the human has to intervene: *"Hey, you forgot to write the file."*

The Developer OS handles this autonomously using **Reprimand Loops**.

If the Doer's run finishes and `IRP.md` does not exist in the workspace, the orchestrator executes the following logic:

1. **Detect Failure**: `os.path.exists("IRP.md") == False`
2. **Halt Progression**: Do not move to the QA phase.
3. **Inject Reprimand**: The orchestrator immediately spawns the Doer again, prefixing its prompt with a hard reprimand:
   > *"ERROR: You claimed to be finished but you did NOT create the 'IRP.md' file. You must create this file now using your tools before the process can continue."*

This self-correcting mechanism is invisible to the human user. The orchestrator acts as a strict supervisor, forcing the LLM to conform to the parser's requirements before advancing the state machine.

## Deterministic Routing

By enforcing the Artifact Contract, the Python orchestrator (`implementation_run.py`) becomes a simple, robust state machine:

```python
# The Router (Simplified)
with open(qrp_dest, 'r', encoding='utf-8') as f:
    content = f.read()
    outcome = "to correct"
    if "outcome: final" in content.lower(): 
        outcome = "final"
    elif "outcome: blocked" in content.lower(): 
        outcome = "blocked"

if outcome == "final":
    state["status"] = "SUCCESS"
    break # Exit loop
else:
    # Proceed to next iteration
```

We do not ask another LLM to "evaluate if the QA was happy." We parse a deterministic string from a physically generated artifact. Limit freedom, increase capability.
# Artifact-Driven Workflow & Reprimand Loops

If you rely on an LLM to parse a chat stream to determine if a task is finished, you will eventually fail. LLMs are prone to hallucinating completion, apologizing endlessly, or entering conversational loops. 

The Developer OS abandons unstructured chat entirely in favor of a strict **Artifact-Driven Workflow**.

## The Artifact Contract (Layer 2 API)

Agents are legally bound to produce and consume physical Markdown files. These files act as the universal API between the human, the Manager, the Doer, and the QA. They are use-case independent.

### 1. The Manager's Artifacts (`IRQ.md` & `QAR.md`)
The Manager agent interacts with the human to determine intent, then compiles it into two strict downstream artifacts:
*   **Implementation Request (`IRQ.md`)**: The contract for the Doer. Defines what to build, boundaries, constraints, and definition of done.
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
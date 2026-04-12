# The Amnesia Engine & Context Injection

Have you ever argued with an AI, and it just keeps apologizing but repeating the exact same broken code? 

This is a well-known AI problem called **Anchoring Bias**. When an AI writes a flawed piece of code in Iteration 1, and you (or the QA agent) point out the flaw, the AI often spends Iterations 2, 3, and 4 stubbornly trying to patch its bad idea rather than taking a step back and rewriting it correctly. The longer the chat history gets, the more "anchored" the AI becomes to its original mistake. Furthermore, a massive context window slows down generation and increases API costs dramatically.

To solve this, the Developer OS implements the **Amnesia Engine**.

By forcing the AI to "go to sleep" and wake up with no memory of its past mistakes, we force it to look at the problem with fresh eyes.

## Hard Resets via Configuration

The system enforces session amnesia by frequently wiping the agent's conversation history. This is controlled via `run_config.json`:

```json
"memory_and_context": {
  "doer_amnesia_frequency": 1,
  "qa_amnesia_frequency": 1
}
```

When frequency is set to `1`, the agent gets a completely fresh session ID on *every single iteration*. It wakes up with zero memory of the conversation that happened in previous rounds.

## Rebuilding Context via XML Injection

If the agent has amnesia, how does it know what to fix?

Instead of relying on the messy, unstructured "train of thought" stored in standard LLM chat histories, the Orchestrator **dynamically rebuilds the agent's context using strictly verified artifacts**.

Before waking the amnesic Doer agent for Iteration 2, the Orchestrator reaches into the Central Registry, grabs the QA's feedback from Iteration 1 (`v1_QRP.md`) and potentially the Doer's own previous report (`v1_IRP.md`), and injects them physically into the system prompt using clear XML tags:

```xml
<active_feedback>
  <QRP round="1">
    [QA feedback regarding the failure...]
  </QRP>
</active_feedback>
```

### Why this is vastly superior:
1. **Curated Signal**: The agent only sees the *final, approved feedback* from the QA, not the messy trial-and-error thoughts it had while writing the bad code.
2. **Cognitive Reset**: By waking up fresh but with a clear "bug report" (the XML payload), the LLM approaches the problem from first principles again, breaking the anchoring bias.
3. **Context Efficiency**: Instead of passing 50,000 tokens of chat history back and forth, we pass a highly compressed, 500-token YAML/Markdown artifact.

## Historical Depth

The Amnesia Engine is configurable. You can dictate how far back the injected memory goes:

```json
"memory_and_context": {
  "qa_past_qrp_count": 2,
  "doer_past_qrp_count": 1
}
```

In this setup:
* The Doer only sees the *immediate* rejection from the last round. It focuses strictly on the immediate fix.
* The QA Auditor sees the last *two* QA reports it generated. This allows the QA agent to perform **Loop Detection**—noticing if the Doer is oscillating between two broken states across multiple rounds.
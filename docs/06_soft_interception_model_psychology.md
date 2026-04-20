# 06. Soft Interception & Model Psychology

Enforcing physical security is only half the battle. If the orchestrator blocks an action, the model must understand *why* it was blocked so it can recover. Furthermore, the model must not be so intimidated by the security rules that it refuses to act at all (the "Alignment Trap").

## The "Soft Interception" Mechanism

In traditional sandboxing, a security violation often results in a hard crash (`Process Terminated: SIGKILL`). This is fatal for autonomous agents—the context window is lost, and the orchestrator receives no explanation.

The Gemini CLI uses a **Soft Interception** model. When the Tier 4 Engine blocks a forbidden tool call, it does not crash the Python process. Instead, it intercepts the call and returns a simulated JSON response directly into the model's context window:

```json
{
  "error": "SECURITY CONTRACT VIOLATION: Access restricted to whitelisted paths.",
  "status": "denied"
}
```

### Why Soft Interception is Powerful:
1.  **Graceful Recovery:** The model sees the "denied" message and can immediately pivot. If it mistakenly requested a relative path, it can apologize, correct the format to an absolute path, and try again within the same session.
2.  **Orchestrator Feedback:** The model can synthesize the failure and report a human-readable explanation back to the orchestrator (e.g., "I cannot complete this task because the requested file is outside my permitted sandbox.").

## Psychological Engineering: Overcoming Paranoia

During the development of `gemini-cli-headless`, we discovered that Gemini models (particularly Gemini 3) are highly sensitive to "punitive" prompting.

If the system prompt dictates:
> *"Any deviation will result in a physical permission error. You are in a strict sandbox."*

The model's internal safety alignment triggers a "Paralysis State." It becomes so terrified of making a mistake that it refuses to use *any* tools, even the ones explicitly whitelisted. It will output text like, "I cannot fulfill this request as it violates my security guidelines."

### The "Invisible Enforcement" Strategy

To achieve 100% compliance without triggering model paranoia, `gemini-cli-headless` employs **Dynamic Context-Aware Prompting** using an "Invisible Enforcement" tone.

Instead of threatening the model with errors, the wrapper injects plain, factual notes into the prompt—and it *only injects them when they apply to the specific run*.

**Example Injection:**
> *"Note: Please use absolute paths starting with 'D:/sandbox/' for all file operations. You have permission to use these tools: ['read_file', 'replace']. Attached files (prefixed with @) are available in your context window for direct analysis without tools."*

By removing the words "Security," "Contract," and "Forbidden," we bypass the model's refusal logic. The model interprets these as helpful configuration notes rather than a cage, allowing it to work confidently and naturally, while the physical Tier 4 Engine silently enforces the actual boundaries in the background.

## Persona Overriding: The `system_instruction_override` Power

The official Gemini CLI comes pre-configured with a "Software Engineering Agent" personality. While useful for coding, this persona can be destructive when using the CLI headlessly for tasks like raw data extraction, RAG, or creative writing.

`gemini-cli-headless` allows for **Full Persona Replacement** using the `system_instruction_override` parameter.

### How it works:
When `system_instruction_override` is provided, the wrapper leverages the `GEMINI_SYSTEM_MD` environment variable. This tells the underlying Node.js engine to **completely abandon** its hardcoded software engineer identity and adopt your custom instruction as the core system prompt.

This is the ultimate level of psychological control: you are not just "suggesting" a behavior to an engineer; you are fundamentally redefining what the agent *is* from the first token.

### Hierarchical Isolation
By default, the Gemini CLI searches for `GEMINI.md` files in parent directories to build context. This can lead to "Hierarchical Memory Pollution" where a project's default rules leak into your headless bot.

`gemini-cli-headless` automatically prevents this by setting `isolate_from_hierarchical_pollution=True` (the default). It achieves this through a surgical combination of `GEMINI_CLI_HOME` redirection to trick the CLI into believing it is in its home directory, and an explicitly injected `GEMINI_SYSTEM_MD` file. This guarantees a perfectly pure persona based solely on your override, while retaining awareness of the actual local workspace through custom root resolution logic.


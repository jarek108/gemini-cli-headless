# 02. Prompt Composition & Soft Interception

To effectively orchestrate the Gemini CLI in a headless environment, you must understand how the library constructs the final prompt and how the engine handles security violations.

## The Problems with Vanilla Prompting

When using the raw Gemini CLI headlessly, you immediately run into three major prompting obstacles:

1.  **The Software Engineer Persona:** The CLI has a hardcoded preamble instructing the model that it is an interactive software engineer. If you want a bot that strictly extracts JSON or translates text, this persona causes it to refuse tasks or hallucinate engineering advice.
2.  **Hierarchical Memory Pollution:** The CLI stealthily crawls upward from your current directory, merging every `GEMINI.md` file it finds into the system prompt. Your headless bot's behavior will mysteriously change depending on which folder it runs in because it's secretly inheriting external project rules.
3.  **Tool Shyness (Paralysis):** LLMs are highly sensitive to punitive prompting. If they are placed in a strict sandbox without knowing what they *are* allowed to do, they become terrified of making mistakes and refuse to execute any tools at all.

`gemini-cli-headless` solves these issues by algorithmically calculating a pristine prompt environment before every run.

## The Prompt Composition Formula

Instead of a simple string pass-through, the library constructs the final prompt dynamically. Here is the logical pseudo-code for how your final instruction set is calculated:

```python
FINAL_PROMPT = ""

# =====================================================================
# 1. SYSTEM IDENTITY & CONTEXT (Solving Persona & Pollution)
# =====================================================================
if system_instruction_override is provided:
    # 100% Mind Wipe. The CLI's internal prompt builder is entirely bypassed 
    # via the undocumented GEMINI_SYSTEM_MD environment variable.
    FINAL_PROMPT += system_instruction_override
else:
    # Retain the default Software Engineer identity.
    FINAL_PROMPT += "<CLI's Hardcoded Default SE Preamble>"
    
    if isolate_from_hierarchical_pollution == True:
        # We redirect GEMINI_CLI_HOME to stop the upward crawl.
        # The model ONLY sees the GEMINI.md in the current working directory.
        FINAL_PROMPT += "<Contents of ./GEMINI.md>" 
    else:
        # Vanilla behavior: The model inherits rules from parent folders.
        FINAL_PROMPT += "<Merged contents of all parent GEMINI.md files>"

# =====================================================================
# 2. ENVIRONMENT GUIDANCE (Solving Tool Shyness)
# =====================================================================
if inject_enforcement_contract == True:
    # We explicitly tell the model its boundaries so it isn't paralyzed by fear.
    # This block dynamically lists the exact tools and paths you whitelisted.
    FINAL_PROMPT += "[ENVIRONMENT CONTEXT] You are in a restricted headless environment."
    FINAL_PROMPT += " Allowed tools: [read_file, replace, ...]."
    FINAL_PROMPT += " File access is restricted to: [...]. ALWAYS use absolute paths."

# =====================================================================
# 3. THE USER TASK
# =====================================================================
FINAL_PROMPT += user_provided_prompt

# Send FINAL_PROMPT to the physical engine...
```

---

## The "Soft Interception" Paradigm

Traditional security systems often use "Hard Enforcement"—if an agent tries to read a forbidden file, the process is killed (`PermissionError`). For autonomous agents, this is catastrophic as the conversational context is lost.

The Gemini CLI engine uses **Soft Interception** at the Tier 4 Policy layer.

### How it Works:
1.  **The Violation:** The model attempts a forbidden tool call (e.g., `read_file(path="/etc/passwd")`).
2.  **The Interception:** The physical engine blocks the execution.
3.  **The Injection:** Instead of crashing, the engine returns a simulated JSON error response directly into the model's chat history:
    ```json
    {
      "error": "SECURITY CONTRACT VIOLATION: Access restricted to whitelisted paths.",
      "status": "denied"
    }
    ```
4.  **The Recovery:** The model "reads" this rejection just like a file content. It can apologize, realize its mistake, and pivot to a different, permitted action without losing the session state.

## Summary of Prompt Parameters

| Parameter | Function |
| :--- | :--- |
| `system_instruction_override` | Defines the base identity. Triggers the `GEMINI_SYSTEM_MD` Mind Wipe. |
| `inject_enforcement_contract` | (Default: `True`) Injects whitelisted tool names and path rules into the prompt. |
| `prompt` | Your primary task instructions. |

By combining a **Mind Wipe** for identity with **Environment Context** for guidance and **Soft Interception** for enforcement, `gemini-cli-headless` creates an environment that is both physically secure and psychologically helpful for autonomous agents.

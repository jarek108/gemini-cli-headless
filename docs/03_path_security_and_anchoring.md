# 03. Path Security & The Static Compiler Bug

Path-based security is notoriously difficult in LLM tool calling. If an AI agent has the ability to read or write files, preventing it from escaping its designated sandbox is critical. 

> **🚨 CRITICAL WARNING: PATH SECURITY IS CURRENTLY BROKEN 🚨**
> Do NOT use the `allowed_paths` parameter in the current version of this library. Due to a static compiler bug in the upstream `gemini-cli` policy engine, attempting to apply path restrictions will permanently delete all tools from the agent's schema, rendering the agent incapable of using tools and causing severe hallucinations. *(See the `canary_tool_presence_baseline` vs `canary_upstream_compiler_bug` tests in our integration suite for reproducible proof of this defect).* 

## The Core Concept

The Gemini CLI uses a TOML-based policy engine to define what actions the model is permitted to take. `gemini-cli-headless` wraps this engine, allowing users to pass `allowed_tools` and `allowed_paths` which it translates into TOML rules.

A standard path restriction requires two conceptual rules:
1. **ALLOW** `read_file` on `/sandbox`.
2. **DENY** `read_file` everywhere else (a Catch-All Deny).

## The Static Compiler Bug (The Catch-22)

The upstream `gemini-cli` contains a bug in how it translates the TOML policy into the JSON "Tool Schema" that is sent to the Gemini API. The schema is what tells the AI what functions it is physically capable of calling.

The CLI's schema generator evaluates rules *statically*, before the model even boots. 

When `gemini-cli-headless` generates the necessary Catch-All DENY rule to protect the rest of your hard drive, the upstream static schema compiler sees "DENY `read_file`" and misinterprets it. It doesn't understand that this is a fallback rule for paths outside the whitelist. It simply concludes: *"This tool is denied,"* and **completely erases it from the API request schema**.

### The Consequence

1. You set `allowed_paths=["/sandbox/ok"]`.
2. The wrapper generates the DENY rule to secure the boundary.
3. The upstream CLI strips all file-system tools from the model's brain.
4. The model attempts to fulfill your request (e.g., "Read the file"), realizes it has no native tools, and hallucinates XML tags to fake the action.

## Workarounds & Capabilities

Until the upstream `gemini-cli` patches its schema generator to gracefully handle conditional `restrictedPaths` annotations without stripping the tool from the schema, true autonomous path security via the policy engine is compromised.

**What you CAN do (The Safe Operating Mode):**
You can perfectly mix, match, and restrict tools as long as you do not apply path limitations. 
* Always leave `allowed_paths=["*"]` (or `None`).
* Freely define `allowed_tools=["read_file", "run_shell_command"]` or specific `allowed_commands=["npm test"]`.

If you specify `allowed_tools=["read_file", "list_directory"]` and leave `allowed_paths=["*"]`, the system works flawlessly. The CLI correctly strips unauthorized tools (like `write_file`) and the model accurately understands its capabilities.

**What you CANNOT do:**
You cannot safely lock an active tool to a specific folder. 

If you need strict path security right now, you must rely on OS-level isolation (e.g., running the Python script inside a Docker container or a severely restricted user account) where the operating system itself rejects unauthorized file access, rather than relying on the Gemini CLI's internal policy engine.

---

~~## The Internal Physics: `stableStringify`~~
~~*(This section previously detailed an undocumented Null-Byte `\0` structural anchoring trick to prevent Parameter Injection. It is now obsolete as the wrapper has migrated to the official `toolAnnotations = { "restrictedPaths" = ... }` schema, which is currently blocked by the bug described above.)*~~

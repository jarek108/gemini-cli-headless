# 09. Persona Overriding & The SYSTEM_MD Bypass

The official Gemini CLI comes pre-configured with a "Software Engineering Agent" personality. While useful for coding, this persona can be destructive when using the CLI headlessly for tasks like raw data extraction, RAG, or creative writing.

`gemini-cli-headless` allows for **Full Persona Replacement** using the `system_instruction_override` parameter.

## The Illusion of Appending

By default, if you simply pass a system prompt to an LLM wrapper, you are often just appending your instructions to an existing, hardcoded preamble. 

In the Gemini CLI, the core system prompt dictates:
> *"You are Gemini CLI, an interactive CLI agent specializing in software engineering tasks..."*

If we were to merely append our instructions, the model would suffer from identity confusion, trying to be a "Software Engineer" and a "Pirate" simultaneously.

## The Technical Reality: The Template Override

`gemini-cli-headless` achieves a true "Mind Wipe" by leveraging a deeply hidden, undocumented feature of the underlying Gemini CLI engine: the `GEMINI_SYSTEM_MD` environment variable.

The CLI engine does not treat `GEMINI_SYSTEM_MD` simply as an extra context file. It treats it as a **Template File Override**.

When `system_instruction_override` is provided, the wrapper does the following:
1. It creates a temporary Markdown file containing *only* your custom instructions.
2. It sets `GEMINI_SYSTEM_MD` to the absolute path of this temporary file.

Inside the CLI engine's TypeScript core, the logic evaluates this variable:
```typescript
if (process.env['GEMINI_SYSTEM_MD']) {
    // 1. The engine completely Abandons its internal prompt composition
    // 2. It reads the file provided by the environment variable
    basePrompt = fs.readFileSync(systemMdPath, 'utf8'); 
} else {
    // 3. ONLY IF NO VARIABLE IS SET, does it build the default SE prompt
    basePrompt = getCoreSystemPrompt(options); 
}
```

Because `gemini-cli-headless` injects this variable, we completely bypass the CLI's standard prompt composition. The hardcoded "Software Engineer" identity, the core mandates, and the default tool usage guidelines are entirely discarded. The model truly starts with a 100% blank slate.

## Hierarchical Isolation (Preventing Context Drift)

By default, the Gemini CLI searches for `GEMINI.md` files in parent directories to build context. This can lead to "Hierarchical Memory Pollution" where a project's default rules (e.g., "Always use TypeScript") leak into your headless bot, corrupting its pure persona.

`gemini-cli-headless` automatically prevents this by setting `isolate_from_hierarchical_pollution=True` (the default). 

It achieves this through a surgical combination of two techniques:
1.  **The System Override:** As described above, using `GEMINI_SYSTEM_MD` forces the CLI to use a specific, isolated file for its project context, skipping the hierarchical crawl.
2.  **The Home Redirection:** The wrapper temporarily redirects `GEMINI_CLI_HOME` to the current working directory. This tricks the CLI into believing it is operating in a sandboxed home environment, further shutting down any global configuration leakage.

This two-pronged approach guarantees a perfectly pure persona based solely on your override, while our custom root resolution logic ensures that session histories are still reliably saved in the correct, actual workspace directory.
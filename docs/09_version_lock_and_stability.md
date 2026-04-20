# 09. Version Lock & System Brittleness

`gemini-cli-headless` achieves its enterprise-grade security by operating as a "parasitic" orchestrator. Rather than relying solely on the public, documented CLI flags, it deeply exploits the undocumented internal mechanics and physics of the Gemini CLI's policy engine.

Because of this tight coupling to internal implementation details, **this wrapper is strictly version-locked to Gemini CLI `v0.38.2`.**

## Why the System is Brittle

The "Zero-Trust Sandbox" is built upon precise observations of how the engine parses, stringifies, and validates data. If the upstream maintainers refactor these internal components, the sandbox may silently fail open (allowing unauthorized access) or fail closed (breaking legitimate functionality).

### Likely Breaking Points

If you attempt to use this wrapper with a newer or older version of the Gemini CLI, watch for failures in these specific areas:

#### 1. `stableStringify` and Null-Byte (`\0`) Anchoring
To prevent path-injection attacks (where a malicious path is hidden inside file content), our TOML policies anchor regexes using escaped Null Bytes (`\\\\0`). This relies entirely on the internal `stableStringify` function wrapping top-level JSON keys in `\0` before regex evaluation.
*   **The Break:** If the CLI developers change the delimiter, alter how JSON is serialized for matching, or remove `stableStringify` entirely, our path security rules will instantly break, allowing massive file system leakage.

#### 2. Pre-Normalization Pathing
Currently, the policy engine matches our `argsPattern` regex against the *raw* string provided by the model, *before* resolving relative paths or standardizing slashes. We counter this by enforcing an "Absolute Path Contract" on the model.
*   **The Break:** If a future version of the CLI begins normalizing paths (e.g., converting `../` to absolute paths or standardizing Windows `\` to `/`) *before* running the policy check, our strict regexes may fail to match legitimate tool calls, or worse, relative path attacks might suddenly bypass our absolute-path filters.

#### 3. Zod Schema Validation (Priority Caps)
Our rules are mounted as `--policy` (Tier 4) with internal priorities specifically kept between `0` and `999`. This is because the internal `toml-loader.ts` uses a strict Zod schema that silently drops rules with priorities outside this range.
*   **The Break:** If the schema is updated—perhaps changing the priority limits, adding new mandatory fields, or altering how `commandPrefix` lists are parsed—our dynamically generated TOML files will be silently rejected. The engine will revert to weak default permissions without throwing a visible error.

## Mitigation Strategy

1.  **Strict Version Pinning:** Systems relying on this orchestrator (like Cortex OS) **must** pin their Gemini CLI installation to exactly `v0.38.2`. Do not use `npm install -g @google/gemini-cli@latest`.
2.  **The Canary in the Coal Mine:** The 29-point Integration Test Battery (`tests/run_integration_tests.py`) is your primary defense. Before upgrading the underlying Gemini CLI binary, you must run the full battery.
3.  **Automated Nightly Monitoring:** We maintain a GitHub Action that checks for new Gemini CLI releases every 24 hours. It automatically installs the new version and runs our integration tests. If a leak is detected, we are alerted immediately.

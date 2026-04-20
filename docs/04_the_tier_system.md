# 04. The Tier System & Priority Caps

To understand how `gemini-cli-headless` enforces its rules, you must understand the internal "physics" of the Gemini CLI policy engine. The engine does not treat all rules equally; it uses a strict **Tier System** combined with a **Priority Formula**.

## The Formula

When a tool call is intercepted, the engine evaluates all active policies to find a matching rule. The "winning" rule is determined by:

`Final Priority = (Tier Value) + (TOML Priority / 1000)`

## The 5 Security Tiers

The CLI assigns a base Tier Value depending on *where* the policy came from. From weakest to strongest:

*   **Tier 1: Built-in Defaults (The "YOLO" Tier)** 
    *   *Base Value:* 1.000
    *   When the user runs `--yolo`, the CLI injects a global "Allow All" rule at Tier 1. It is the weakest form of permission and can be overridden by almost anything.
*   **Tier 2: Project Defaults**
    *   *Base Value:* 2.000
    *   Internal preset rules.
*   **Tier 3: Workspace Configuration**
    *   *Base Value:* 3.000
    *   Rules loaded from `.gemini/` or `settings.json` within the current working directory.
*   **Tier 4: User Policies (The `--policy` flag)**
    *   *Base Value:* 4.000
    *   Any TOML file provided via the standard `--policy` flag. A Tier 4 rule will easily crush a Tier 1 YOLO rule.
*   **Tier 5: Admin Policies (The "Final Authority")**
    *   *Base Value:* 5.000
    *   Policies passed using the **`--admin-policy`** flag. This is designed for system administrators to enforce unbreakable security rules that cannot be overridden by user configs or workspace settings.

## The Priority Cap Discovery

During an audit of the CLI's internal `toml-loader.ts`, we discovered a critical limitation: **The TOML parser uses a strict Zod schema that silently rejects any `priority` value greater than 999.**

Early iterations of `gemini-cli-headless` attempted to enforce rules using `priority = 70000`. Because this exceeded the schema cap, the rules were silently dropped, and the engine defaulted to its lower-tier behaviors.

## The Solution: The "Tier 5 Structural Kernel"

To achieve a 100% unbreakable sandbox, `gemini-cli-headless` mounts its dynamically generated TOML rules using the **`--admin-policy`** flag (Tier 5), while keeping internal TOML priorities strictly between `0` and `999`.

### Why this matters

By occupying the ultimate Tier 5 layer, we prevent two massive attack vectors:
1.  **The Malicious Prompt:** An agent cannot prompt the engine into a YOLO state, because our Tier 5 rules explicitly DENY actions that lack a specific ALLOW rule.
2.  **The Rogue Workspace:** If the orchestrator runs an agent in an untrusted directory containing a malicious `.gemini/settings.json` (Tier 3) attempting to grant global access, our Tier 5 Admin Policy will immediately override it.

We are not "hacking" the CLI; we are leveraging its highest intended security mechanism.

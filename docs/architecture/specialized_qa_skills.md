# Specialized QA & The Evolution of Skills

One of the most profound failures of early coding agents was the assumption that "validation" is a generic, universally understood process. 

You tell an agent to fix a bug, and it responds: *"I have modified the code and verified it works. The tests pass."*

In reality, the agent likely just ran `pytest` or `npm test`. But real-world software engineering is rarely that simple.

## The Illusion of "I Ran the Tests"

"Verify it works" means something fundamentally different depending on the domain, the project, and even the specific developer's style:

*   **A Unity 3D Game:** Verification requires launching a headless Unity instance, waiting for assembly compilation, polling for specific C# exceptions in the Editor log, and potentially parsing visual outputs or custom diagnostics scripts (e.g., `python tools/diagnose_unity.py`).
*   **A Web Frontend:** Verification might require spinning up a browser via Puppeteer, clicking through a specific user flow, and performing visual regression checks on CSS layouts.
*   **A Financial Backend:** Verification might require strictly enforcing specific architectural invariants, verifying ledger balances, or checking against a massive suite of property-based tests.

A general-purpose agent does not know how to test *your* specific app. If you have to spend 15 prompts explaining the intricate ritual of how to compile, run, and visually inspect your Unity project every time you want a feature built, you are still trapped in the **Terminal Babysitting Loop**.

## Separation of Duties: The Maker vs. The Checker

To solve this, the Developer OS strictly enforces a **Separation of Duties**. We do not allow the agent that wrote the code (the "Doer") to grade its own exam.

Instead, we introduce dedicated **QA Auditors**. But crucially, these QA agents are not generic LLMs; they are augmented with **SKILLS**.

## What are "Skills"?

A Skill is a deeply specialized, project-specific module loaded by the QA Auditor. It contains the exact rituals, tools, and domain knowledge required to validate code in that specific environment.

Instead of a generic system prompt, a QA Auditor assigned to a Unity project loads the **"Unity Automated Diagnostician" Skill**. 

This Skill equips the agent with:
1.  **Domain Knowledge:** Understanding that C# compilation in Unity is asynchronous and requires polling timestamps before running tests.
2.  **Tooling:** Access to project-specific diagnostic scripts (`capture_unity.py`, `diagnose_unity.py`).
3.  **Stylistic Awareness:** Knowledge of the team's specific architectural mandates (e.g., "Always ensure logic is strictly separated from MonoBehaviour views").

When the Doer finishes its work, the specialized QA Auditor takes over, running a gauntlet of targeted, domain-aware checks that a generic agent would never think to perform.

## The Evolution of QA Agents

Skills are not static. The Developer OS views QA Agents as entities that must continuously learn and adapt to the specific developer they serve.

This is where the concept of **Persistent Memory** comes into play. 

If the human Tech Lead rejects a QA Report (`QRP.md`) with feedback like: *"You approved this, but you forgot to check if the new UI elements overlap with the hex grid on a 16:9 aspect ratio,"* the system does not just fix the immediate bug.

The system updates the QA Agent's **Project-Specific Skill Profile**. The QA Agent "learns" this new constraint. The next time it audits a UI change, it will autonomously incorporate a visual layout check into its validation routine. 

By treating QA as an evolving set of highly specialized Skills, the Developer OS transforms agents from generic typists into seasoned, project-aware engineering partners who understand exactly what "done" looks like in your specific codebase.
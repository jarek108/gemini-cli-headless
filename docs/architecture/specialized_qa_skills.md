# Specialized QA & The Evolution of Skills

One of the most profound failures of early coding agents was the assumption that "validation" is a generic, universally understood process. 

You tell an agent to fix a bug, and it responds: *"I have modified the code and verified it works. The tests pass."*

In reality, the agent likely just ran `pytest` or `npm test`. But real-world software engineering is rarely that simple.

## The Illusion of "I Ran the Tests"

"Verify it works" means something fundamentally different depending on the domain, the project, and even the specific developer's style:

*   **A Unity 3D Game:** Verification requires launching a headless Unity instance, waiting for compilation, polling for exceptions in the Editor log, and potentially parsing visual outputs.
*   **A Web Frontend:** Verification might require spinning up a browser via Puppeteer, clicking through a specific user flow, and performing visual regression checks on CSS layouts.
*   **A Financial Backend:** Verification might require strictly enforcing specific architectural invariants or checking against a massive suite of property-based tests.

A generic "QA prompt" cannot know how to test *your* specific app. 

## The Separation of Duties: Policy Formulation vs. Execution

To solve this, the Developer OS relies on the **3-Layer Prompting Stack**. 

We do not write a massive prompt telling the QA agent how to test a Unity game. The QA Agent (Layer 1) is a **generic, blind execution engine**. It has zero authority to invent testing philosophy. 

Instead, "QA Skills" live in the target project's `GEMINI.md` file (Layer 3), under a strict `## QA Rituals & Testing` header. 

When the QA Agent wakes up, its generic prompt instructs it to:
1. Locate the `## QA Rituals & Testing` section in `GEMINI.md`.
2. Explicitly and blindly execute every script, invariant check, and tool listed there.
3. Provide a checklist in the `QRP.md` proving the rituals were followed.

## The Evolution of QA Agents (Skill Growth)

How do these project-specific "Skills" get authored? They are written by the **Manager Agent** based on human feedback. 

If the human Tech Lead rejects a completed task because *"The UI looks broken on mobile,"* the system does not just fix the immediate bug.

1. **Human Feedback:** "You approved this, but the UI overlaps the hex grid."
2. **Manager Synthesis:** The Manager agent realizes the QA system has a blind spot.
3. **Skill Update:** The Manager autonomously updates the project's `GEMINI.md` file: *"New Visual Check: QA MUST always use `capture_unity.py` to visually verify UI does not occlude the central hex grid."*

The next time the generic QA Agent wakes up (even for a completely different feature), it reads the updated `GEMINI.md`. **The system has permanently learned how to test your UI.**

By treating QA as a strict separation between **Policy Formulation (Manager -> Layer 3)** and **Policy Execution (QA -> Layer 1)**, the Developer OS transforms generic agents into seasoned, project-aware engineering partners who understand exactly what "done" looks like in your codebase.
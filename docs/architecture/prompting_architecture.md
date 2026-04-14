# The Prompting Architecture

The current trend in "AI coding" is to constantly tweak custom prompts for every new task. This causes prompt explosion and forces you to micromanage agents instead of engineering software.

To solve this, we abandon custom prompt engineering entirely. Instead, we use a rigid, distributed prompting stack divided into three parts:

1. **Role Prompts:** Who the agents are and what authority they have (OS Kernel).
2. **Artifact Templates:** How the agents communicate and transition states (Universal API).
3. **Project Knowledge:** The specific technical rules and testing rituals for your codebase (Project Brain).

---

## Role Prompts
*Location: Workspace Root (`GEMINI.md`) for the Interactive Manager, Orchestrator Source (`templates/roles/`) for Headless modes.*  

We restrict the system to exactly **three universal agent roles**. However, to bridge the gap between human conversation and machine execution, the Manager role operates in two distinct modes—much like a real Tech Lead who talks to you in a meeting room, and then goes back to their desk to write the Jira tickets.

### 1. The Manager (The Tech Lead)
The Manager sits between the human and the execution plane. It operates in two modes:
*   **Interactive (The Meeting Room)**: The CLI agent you talk to. It asks sharp questions, probes edge cases, and seeks to reach a "Certainty Threshold" regarding your intent.
*   **Headless (The Desk Work)**: Once certainty is reached, the Manager uses the `implement_feature()` tool to go offline. In this headless mode, it acts as a bureaucratic clerk, compiling the meeting notes into rigid, Space-Grade Engineering Specifications (`IRQ.md` and `QAR.md`) without bothering the human with the formatting.

### 2. The Doer (The Builder)
The blind builder. It reads the tasks and project rules, writes the code, and produces an Implementation Report (`IRP.md`). It is forbidden from expanding scope.

### 3. The QA (The Enforcer)
The strict enforcer. It reads the QA Request (`QAR.md`) and project rules, blindly executes the required tests, and produces a QA Report (`QRP.md`). It rejects the work if any rule is broken.

---

## Artifact Templates
*Location: Orchestrator Source (`templates/artifacts/`)*  

We don't rely on chat messages to know if a job is done. Agents must structure their thoughts and outputs using strict Markdown templates. These artifacts are essentially "Black Box Flight Recorders"—you only need to read them if something crashes.

*   **Implementation Request (IRQ):** The Manager's compiled contract telling the Doer what to build and what not to touch.
*   **QA Request (QAR):** The Manager's compiled contract telling the QA what specific risk areas to test.
*   **Implementation Report (IRP):** The Doer's receipt proving it finished the work and noting any edge cases.
*   **QA Report (QRP):** The QA's final verdict (`final` or `to correct`). The Python orchestrator reads this to advance the loop.

---

## Project Knowledge
*Location: Target Workspace (`projects/my-app/GEMINI.md`, `designs/`)*  

This is where **100% of the project specificity lives**. When the generic Doer and QA agents wake up, they read this layer to understand your tech stack, architectural rules, and testing rituals. 

Crucially, **Project Knowledge is a learning system managed by the Manager.**

### The Skill Growth Lifecycle:
Instead of rewriting agent prompts when a mistake happens, the system learns like a real engineering team:

1. **The Failure:** The Doer and QA finish a task, but you notice a UI element overlaps on mobile screens. 
2. **The Intervention:** You tell the Manager CLI: *"You both missed the UI overlap on the mobile viewport."*
3. **Policy Formulation:** The Manager autonomously updates your project's `GEMINI.md` file, adding a new rule under `## QA Rituals`: *"Mobile Viewport Check: QA must run `mobile_test.sh`."*
4. **Permanent Hardening:** The system has permanently learned. The next time the QA agent boots up for a UI task, it reads the updated Project Knowledge and ruthlessly enforces the new mobile test.
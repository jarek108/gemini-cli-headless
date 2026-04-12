# The 3-Layer Prompting Architecture

The current meta of "AI coding" relies heavily on prompt engineering: users constantly tweak custom personas, system instructions, and ad-hoc rules for every new task or project. This causes **role and prompt explosion**, forcing the human to spend their limited attention micromanaging agent behavior rather than engineering software.

To maximize **Productivity per Human Attention (PHA)**, this system abandons custom prompt engineering entirely. Instead, we use a rigid, distributed **3-Layer Prompting Stack**. 

Layers 1 and 2 act as the immutable "OS Kernel." They contain **zero project-specific information** and the user never edits them. Layer 3 acts as the "Project Brain," evolving autonomously based on human feedback.

---

## Layer 1: The OS Kernel (Stable Role Prompts)
*Location: Orchestrator Source (`templates/roles/`)*  
*Purpose: Defines Identity, Authority, and System-Level Boundaries.*

We restrict the system to exactly three universal agent roles. Their prompts are entirely generic and use-case independent. They define *how the agents relate to the artifacts and to each other*, not how to code.

1. **The Manager (The Architect & Policymaker):**
   - **Authority:** High. The only agent permitted to interact with the human and modify Layer 3.
   - **Directive:** Translates human intent into concrete execution artifacts (`IRQ` and `QAR`). Synthesizes human feedback into systemic, project-wide rules.
   - **Constraint:** Does not write implementation code. 
2. **The Doer (The Builder):**
   - **Authority:** Low. 
   - **Directive:** Reads the `IRQ` and Layer 3 context, performs surgical implementation, and produces an `IRP`.
   - **Constraint:** Blind executor. Actively forbidden from expanding scope, inventing features, or performing unprompted refactoring.
3. **The QA (The Enforcer):**
   - **Authority:** Absolute over the Doer; Zero over project policy.
   - **Directive:** Adversarial checker. Reads the `QAR`, `IRP`, and Layer 3 rules. Blindly executes the required validation rituals. Produces the `QRP`.
   - **Constraint:** Cannot invent testing philosophies. If a Doer violates a Layer 3 invariant, the QA rejects the implementation.

---

## Layer 2: The Universal API (Artifact Templates)
*Location: Orchestrator Source (`templates/artifacts/`)*  
*Purpose: Forces Deterministic State Transitions.*

We do not parse chat streams to determine if a task is done. The orchestrator requires agents to structure their thoughts and outputs using strict Markdown templates. Like Layer 1, these templates are universal and never modified by the user.

- **IRQ (Implementation Request):** The Manager's contract for the Doer (What to build, boundaries, constraints).
- **QAR (QA Request):** The Manager's contract for the QA (Specific risk areas to check for this particular feature).
- **IRP (Implementation Report):** The Doer's receipt. Prompts the Doer to self-reflect (e.g., forcing a "Known Edge Cases" section) *before* handing off.
- **QRP (QA Report):** The QA's deterministic verdict. It forces a strict YAML header (`outcome: final | to correct | blocked`) that the Python orchestrator uses to safely advance the state machine.

---

## Layer 3: The Project Brain (Evolving Local Context)
*Location: Target Workspace (`projects/my-app/GEMINI.md`, `designs/`)*  
*Purpose: Defines Project-Specific Physics, Skills, and QA Rituals.*

This is where **100% of the project specificity lives**. When the OS boots up the generic Doer and QA, it mounts Layer 3 into their context window. This layer contains tech stacks, architectural mandates, and testing rituals. 

Crucially, **Layer 3 is not static—it is a learning system managed by the Manager Agent.**

### The Skill Growth Lifecycle:
Instead of rewriting prompts when the system makes a mistake, the system learns like a real engineering team:

1. **The Failure:** The Doer and QA complete a loop. The QA outputs `[STATUS: FINAL]`. However, the human reviews the work and notices a UI element overlaps on mobile screens. 
2. **The Intervention:** The human does not open the code or edit agent prompts. The human tells the Manager: *"You both missed the UI overlap on the mobile viewport."*
3. **Policy Formulation:** The Manager agent realizes the system has a blind spot. It autonomously updates the project's `GEMINI.md` file, adding a new rule under `## QA Rituals`: *"Mobile Viewport Check: QA must run `mobile_layout_test.sh` and verify no overlapping bounding boxes."*
4. **Permanent Hardening:** The system has permanently learned. The next time the generic QA agent is booted for *any* UI task, it reads the updated Layer 3 context, sees the new mobile viewport mandate, and ruthlessly enforces it.

By locking Layers 1 and 2, and automating the growth of Layer 3, we elevate the human from a "terminal babysitter" to a **Tech Lead**. When errors happen, you don't fix the code—you instruct the Manager to update the Standard Operating Procedure, permanently hardening your automated CI pipeline.
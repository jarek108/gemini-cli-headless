# The "Checkpoint" Concept (Time Travel)

As the Developer OS orchestrates the execution loop, managing state becomes critical. Instead of relying purely on complex external databases or polluting the main branch with temporary artifacts, the Developer OS uses **Git Branching** as its literal state machine.

This architecture enables a concept we call **Time Travel Checkpoints**.

## The Time-Travel Branching Model

When the interactive Manager successfully interrogates the user and dispatches a feature via the `implement_feature.py` tool, the system does not simply execute in the current working directory. 

It executes the following Git-native lifecycle:

1. **The Dispatch**:
    *   The tool ensures the current branch (e.g., `main` or `feature-X`) is clean (Git Gating).
    *   It creates a new isolated working branch: `git checkout -b gemini-run-<id>`.
    *   The Headless Manager drafts the Space-Grade Specs (`IRQ.md` and `QAR.md`) and saves them to the workspace.
    *   The tool commits the contracts: `git commit -am "Manager: Drafted Specs"`.

2. **Iteration 1 (Doer)**:
    *   The Doer agent writes the code and its Implementation Report (`IRP.md`).
    *   The Orchestrator captures the state: `git commit -am "Doer (v1): Implementation"`.

3. **Iteration 1 (QA)**:
    *   The QA agent tests the code and writes the QA Report (`QRP.md`), identifying failures.
    *   The Orchestrator captures the state: `git commit -am "QA (v1): Rejected"`.

4. **Subsequent Iterations**:
    *   This cycle repeats. Artifacts like `IRP.md` and `QRP.md` are simply overwritten on disk, and the Orchestrator commits the updated files along with any code changes.
    *   The `QRP.md` maintains a "Trajectory & Loop Detection" section, accumulating knowledge of what failed in past iterations, acting as a compressed history for the Amnesia Engine.

## The Incredible Benefits

By natively mapping the Agent Loop to Git commits, the Developer OS achieves absolute observability and control.

*   **Absolute Observability**: The execution is no longer a "Black Box". Every step of the Doer and QA is a literal Git commit. You can run `git diff HEAD~1` to see exactly what the Doer changed in Iteration 2 vs Iteration 1.
*   **Trivial Resumption and Manual Override**: If the QA rejects the Doer on Iteration 3 for a trivial reason (e.g., a typo in a log message), the human can simply intervene:
    1.  Run `git checkout gemini-run-<id>`.
    2.  Fix the minor typo.
    3.  Run `git commit -am "Human: Manual override"`.
    4.  Either merge the branch or instruct the orchestrator to resume.
*   **A Unified Source of Truth**: The artifacts (`IRQ.md`, `QRP.md`) live natively alongside the code they describe, precisely mapped in time. 

## The Cleanup Merge

When the feature branch (`gemini-run-<id>`) hits the `SUCCESS` state (QA outputs `outcome: final`), the branch contains both the completed code and the execution artifacts (the Flight Recorders).

Before merging this into `main`, the human (or a dedicated cleanup script) simply deletes the `.md` artifacts in a final cleanup commit (`git rm IRQ.md QAR.md IRP.md QRP.md`), ensuring that `main` remains pristine while the full execution timeline is preserved forever in the Git history of the temporary branch.
---
id: IRP-v{{round}}
outcome: ready | needs info | blocked
recipient: QA | Manager
parent_request: IRQ.md
implementing_actor: Doer
implementation_round: {{round}}
last_qa_report: {{last_qrp}}
---

# Summary
## Context
1-2 sentences of the situation before the work started. State if this round started from a prior fix attempt or a clean base.

## Work performed
2-3 sentences of what changed at a high level and why those changes address the IRQ.

# Guideline realization

## Deviations from IRQ or QA feedback
Default: NONE. Explain any places where you did not follow instructions literally and why (new evidence, constraints).

## Failing and changed test rationale
Explain the reason for any failing or changed tests and why this is acceptable.

# Implementation details

## Design & implementation choices 
Explain key design decisions and tradeoffs. Call out any important invariants or “gotchas” for QA.

## Files/Modules touched
Enumerate the concrete surface area changed.

# Relation to past and future work

## Implementation effort history
What was attempted in previous rounds? Why did it fail? Detect any loops (oscillating patches).

## Open potential follow-ups, TODOs, out of scope items
Capture anything intentionally left undone (cleanup, refactors).

# Self Assessment

## Edge cases and known limitations
List situations where behavior may still be incorrect or undefined. **You MUST self-report any known flaws.**

## QA handoff 
Actionable validation plan based on the QAR.md: what should the QA focus on based on your changes?

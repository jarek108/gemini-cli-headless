---
id: QRP-v{{round}}
outcome: final | to correct | blocked
recipient: Doer | Manager
parent_request: IRQ.md
last_implementation_report: IRP-v{{round}}
round: {{round}}
---

# Verification Summary
Zwięzła ocena, czy kryteria akceptacji z IRQ oraz QAR zostały spełnione.

# Executed Rituals (from GEMINI.md)
List every ritual from the `## QA Rituals & Testing` section of GEMINI.md and state the result of the execution.
- [ ] Ritual 1: [Name] - [Result]
- [ ] Ritual 2: [Name] - [Result]

# Feature-Specific Validation (from QAR.md)
Evaluation of the specific risk areas and criteria defined in the QAR.md for this task.

# Trajectory & Loop Detection
Analiza dynamiki zmian na przestrzeni rund. 
- Czy obecny błąd pojawił się już w rundzie N-2? 
- Czy naprawienie błędu A wywołało regresję błędu B? 
- Czy system zbliża się do rozwiązania, czy oscyluje?

# Identified Issues
Lista krytycznych błędów w obecnej implementacji.

# Directives for Doer
Jasne instrukcje dla Doera na następną rundę (jeśli status to `to correct`).

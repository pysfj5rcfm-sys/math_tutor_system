# Handoff v0.1.9-pretrial

Status: Prompt Protocol Upgrade + Minimal Evidence Persistence.

Version metadata:

- `schema_version`: `0.1.7`
- `registry_version`: `0.1.8.1`
- `registry_mode`: `no_legacy`

Completed:

- Added additive DB migration columns for mistake diagnosis evidence and worksheet item roles.
- Kept the existing `mistakes.yaml` and `worksheet.yaml` root structures.
- Added validation and import support for `diagnosis_confidence`, `needs_human_review`, `secondary_mistake_tags`, `diagnosis_evidence`, and `alternative_diagnoses`.
- Added validation and import support for `primary_target_id`, `question_role`, `teaching_purpose`, and `expected_error_mechanism`.
- Updated marking, worksheet, YAML parse repair, and validation repair prompt templates for v0.1.9-pretrial.
- Added lightweight prompt-facing target priority helper in `src/core/target_priority_light.py`.
- Kept `mastery_update_signal` as a prompt/review protocol only; no mastery state table or state machine was added.
- Added UAT fixtures:
  - `samples/uat_v019_pretrial_mistakes_evidence.yaml`
  - `samples/uat_v019_pretrial_worksheet_roles.yaml`
- Added pytest coverage in `tests/test_v019_pretrial_protocol.py`.

Non-goals preserved:

- No v0.2 Subject Rendering Layer.
- No visuals, diagrams, render blocks, SVG, PDF, OCR, API, or server work.
- No `target_state`, `mastery_state`, `attempts`, worksheet result, review schedule, or spaced repetition tables.
- No automatic UAT sample import.
- No X/Y registry change.
- No legacy runtime restore.

Operational notes:

- The student worksheet HTML remains free of teacher-purpose fields.
- The answer sheet can display `question_role` and `teaching_purpose`.
- `target_matrix` remains primary-only by default.
- `secondary_mistake_tags` are stored for explanation, review, and future profiling only.

Residual risk:

- `target_priority_light` is intentionally simple and should remain prompt input, not final mastery state.
- `diagnosis_evidence` accepts flexible mapping content; downstream consumers should tolerate missing subfields.

# Minimal Evidence Persistence v0.1.9-pretrial

Scope: small additive persistence for trial-readiness. This is not a full attempts/results, target_state, or mastery_state system.

## DB Migration

`schema_version` is `0.1.7`.

New `mistakes` columns:

- `diagnosis_confidence REAL`
- `needs_human_review INTEGER DEFAULT 0`
- `secondary_mistake_tags_json TEXT`
- `diagnosis_evidence_json TEXT`
- `alternative_diagnoses_json TEXT`

New `worksheet_items` columns:

- `primary_target_id TEXT`
- `question_role TEXT`
- `teaching_purpose TEXT`
- `expected_error_mechanism TEXT`

Migration is additive and idempotent through `src.db.migrate_schema`.

## mistakes.yaml Optional Fields

Accepted optional fields:

- `diagnosis_confidence`
- `needs_human_review`
- `secondary_mistake_tags`
- `diagnosis_evidence`
- `alternative_diagnoses`

Import behavior:

- `diagnosis_confidence` must be numeric from 0.0 to 1.0.
- `needs_human_review` is parsed as boolean and stored as integer.
- `secondary_mistake_tags` must be a list of at most 3 current allowed mistake tags.
- `diagnosis_evidence` must be a mapping and is stored as JSON.
- `alternative_diagnoses` must be a list; each item code must be an allowed current mistake tag, and confidence must be 0.0 to 1.0 when present.

## worksheet.yaml Optional Fields

Accepted per-question optional fields:

- `primary_target_id`
- `question_role`
- `teaching_purpose`
- `expected_error_mechanism`

Import behavior:

- `question_role` must be `repair`, `variant`, `transfer`, or `mixed_review` when present.
- `primary_target_id`, `teaching_purpose`, and `expected_error_mechanism` may be empty strings.
- Student worksheet HTML does not expose teacher-purpose fields.
- Answer sheet HTML may display `question_role` and `teaching_purpose`.

## Explicit Non-Goals

Not added in this release:

- `target_state`
- `mastery_state`
- `attempts`
- `worksheet_attempts`
- `worksheet_item_results`
- `review_schedule`
- `spaced_repetition_schedule`

`secondary_mistake_tags` and `alternative_diagnoses` are review evidence only. `target_matrix` continues to use primary mistake tags by default.

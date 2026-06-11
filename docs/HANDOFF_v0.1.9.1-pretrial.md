# Handoff v0.1.9.1-pretrial

Status: G5B Math Knowledge Registry Backfill.

Version metadata:

- `schema_version`: `0.1.7`
- `registry_version`: `0.1.8.1`
- `registry_mode`: `no_legacy`
- G5B registry version: `v0.1.9.1-pretrial`

Completed:

- Registered 沪教版五年级下数学 X-axis knowledge points as `math_g5b_*`.
- Kept the current daughter mainline at grade 6A math / chinese / english.
- Preserved grade 6A default prompt boundary: `math_g5b_*` is not injected into default grade 6 math prompts.
- Added grade-aware prompt alias rendering so G5B aliases do not appear in grade 6 prompt alias lists.
- Added G5B UAT fixtures:
  - `samples/uat_v0191_math_g5b_mistakes.yaml`
  - `samples/uat_v0191_math_g5b_worksheet.yaml`
- Added source and audit docs:
  - `docs/research/source/五年级下数学_knowledge_point_id候选命名.md`
  - `docs/research/math_g5b_knowledge_registry_audit_v0.1.9.1.md`
- Added schema integrity checks for the `math_g5b_*` contract.
- Added pytest coverage for registry loading, prompt boundary, samples, integrity, and v0.1.9-pretrial optional fields.

Registry counts:

- G5B units: 6
- G5B lessons: 15
- G5B knowledge points: 23
- `core_active`: 16
- `review_active`: 7
- `review_only_for_hujiao_g5b`: 2

Non-goals preserved:

- No Y-axis math mistake taxonomy change.
- No DB schema change.
- No v0.2 Subject Rendering Layer.
- No visuals, render blocks, diagrams, PDF, OCR, API, or UI work.
- No automatic UAT sample import.
- No legacy runtime restore.

Operational notes:

- G5B is for historical grade 5B mistakes, grade 5B paper review, and old-foundation remediation.
- G6A remains the default current math registry for daughter.
- Review-only G5B points are active and `review_active`, with `metadata.scope_note: review_only_for_hujiao_g5b`.
- Existing grade 5 representative skeleton rows remain untouched; the v0.1.9.1 contract is enforced only for `math_g5b_*` rows.

Residual risk:

- The original separate candidate-naming attachment was not present in the attachment directory; the source md records the reconstructed candidate table used for this implementation.

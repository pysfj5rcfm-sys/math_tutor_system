# Handoff v0.1.8

Status: stable candidate for Math G6A X/Y registry and target-matrix prompt protocol.

Version metadata:

- `schema_version`: `0.1.6`
- `registry_version`: `0.1.8`
- `registry_mode`: `no_legacy`

Completed:

- Registered沪教版六年级上 math X-axis knowledge registry in `config/curriculum/cn_k12_2022/math/grade_6.yaml`.
- Registered the initial 28 math-visible Y-axis mistake tags in `config/education/mistake_taxonomy.yaml`.
- Added `sign_symbol` category.
- Kept `MATH_EQUALITY_RELATION_ERROR` independent.
- Kept `MATH_QUANTITATIVE_RELATION_ERROR` and `MATH_MODEL_CONSTRUCTION_ERROR` distinct.
- Kept `MATH_UNIT_MEANING_ERROR` and `MATH_UNIT_CONVERSION_ERROR` distinct.
- Updated subject-scoped math aliases.
- Added read-only target matrix helper.
- Updated marking and worksheet prompt protocol.
- Added v0.1.8 UAT samples.
- Added v0.1.8 registry tests and schema-integrity checks.

Non-goals preserved:

- No DB schema change.
- No DB rebuild beyond normal `src.db` initialization/seed.
- No automatic UAT sample import.
- No v0.2 rendering layer.
- No visuals, diagrams, render blocks, PDF, OCR, API, or server work.

v0.1.8.1 follow-up:

- Full research sources were added under `docs/research/source/`.
- See `docs/HANDOFF_v0.1.8.1.md` and the v0.1.8.1 X/Y audit docs for the source completion audit.

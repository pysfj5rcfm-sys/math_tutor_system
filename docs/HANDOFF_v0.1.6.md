# HANDOFF v0.1.6

## Project

Project name: `edu_tutor_system`

Formerly: `math_tutor_system`

Current version: `v0.1.6`

Positioning: Clean Schema Cutover & Cross-subject Text Exam Validation.

## What v0.1.6 Did

- Switched default runtime DB to `data/edu_tutor.db`.
- Added clean schema with `schema_meta`, `import_batches`, canonical `mistakes`, `worksheets`, and `worksheet_items`.
- Archived old `data/math_tutor.db` before first clean cutover when needed.
- Stopped creating old fields: `question_type`, `knowledge_point`, `mistake_tag`, `target_mistake_tag`, `difficulty`.
- Added normalize layer for legacy Chinese inputs.
- Updated import preview/confirm to write only canonical fields.
- Updated duplicate guard, stats, data governance, backup/export, display resolver, prompts, app UI, UAT samples, and tests.
- Added `src/core/schema_integrity.py`.
- Added `scripts/uat_db.py`.
- Added `docs/SCHEMA_AUDIT_v0.1.6.md`.

## What v0.1.6 Did Not Do

- No v0.2 rendering.
- No visuals.
- No math geometry renderer.
- No physics formula or diagram renderer.
- No chemical formula/equation renderer.
- No PDF.
- No OCR.
- No OpenAI API call.
- No service/cloud/SaaS permission layer.
- No migration of old business data.

## DB

Runtime DB:

```text
data/edu_tutor.db
```

Legacy DB:

```text
data/math_tutor.db
```

Archive target:

```text
backups/pre_v016_clean_cutover/YYYYMMDD_HHMMSS/math_tutor.db
```

## Schema Summary

Key tables:

- `schema_meta`
- `import_batches`
- `mistake_tags`
- `mistakes`
- `worksheets`
- `worksheet_items`
- `training_prompts`
- `weekly_reviews`
- `llm_call_logs`

Canonical fields:

- `question_type_code`
- `knowledge_point_id`
- `primary_mistake_tag_code`
- `target_mistake_tag_code`
- `difficulty_code`

## Normalize Layer

Entry: `src/core/normalization.py`

Accepts:

- canonical fields
- legacy Chinese fields as input aliases only

Writes:

- canonical DB fields only

Unknown knowledge points do not write free text into `knowledge_point_id`.

## Display Resolver

Entry: `src/core/display.py`

Examples:

- `物理计算 (physics_calculation)`
- `速度 (physics_g8_speed)`
- `物理公式选错 (PHY_F1)`
- `基础 (basic)`

## Export

Entry: `src/core/backup_export.py`

Mistakes and worksheet exports include code + display fields and no old ambiguous field names.

## UAT Samples

- `samples/uat_v016_math_g6_mistakes.yaml`
- `samples/uat_v016_math_g7_mistakes.yaml`
- `samples/uat_v016_physics_g8_mistakes.yaml`
- `samples/uat_v016_chemistry_g9_mistakes.yaml`
- `samples/uat_v016_math_g6_worksheet.yaml`
- `samples/uat_v016_math_g7_worksheet.yaml`
- `samples/uat_v016_physics_g8_worksheet.yaml`
- `samples/uat_v016_chemistry_g9_worksheet.yaml`

## Multi-student / Multi-grade / Multi-subject Validation

Inactive UAT students:

- `uat_math_g6`
- `uat_math_g7`
- `uat_physics_g8`
- `uat_chemistry_g9`

Default active student remains `daughter`.

Tests verify math G6/G7, physics G8, and chemistry G9 preview/confirm flows and plain-text HTML worksheet export.

## Schema Integrity

Use:

```bash
python scripts/uat_db.py status
```

or:

```python
from src.core.schema_integrity import check_schema_integrity
report = check_schema_integrity()
```

Report keys: `errors`, `warnings`, `info`.

## Public Functions Not To Delete

- `preview_mistakes_payload`
- `confirm_mistakes_import`
- `preview_worksheet_payload`
- `confirm_worksheet_import`

## v0.2 Stable Interfaces

v0.2 may rely on:

- Rule Registry scoped by student / subject / grade / curriculum
- clean canonical DB fields
- normalize preview boundary
- display resolver
- YAML preview/confirm imports
- duplicate guard
- plain-text worksheet HTML bundle/export

## v0.2 Rendering Boundary

Still to implement:

- visuals
- math_geometry
- formula_block
- physics_formula
- physics_diagram
- chemical_formula
- chemical_equation

## Known Risks

- Curriculum is representative only.
- Legacy runtime data is archived but not migrated.
- UAT data must not be imported into the formal DB unless intentionally tested.
- `training_prompts`, `weekly_reviews`, and `llm_call_logs` are retained workflow tables and may need another review before v0.2 if rendering logs become richer.

## Commands

Initialize:

```bash
python -m src.db
```

Run app:

```bash
streamlit run src/app.py
```

Test:

```bash
python -m pytest
python -c "import src.app; print('APP_IMPORT_OK')"
```

UAT DB:

```bash
python scripts/uat_db.py status
python scripts/uat_db.py init
python scripts/uat_db.py restore
```

## Do Not Commit

- `data/*.db`
- `backups/`
- `outputs/exports/*`
- `outputs/prompts/*`
- `outputs/worksheets/*`
- `outputs/answer_sheets/*`
- `outputs/reviews/*`
- `.pytest_cache/`
- `__pycache__/`

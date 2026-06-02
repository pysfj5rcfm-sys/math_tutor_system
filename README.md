# edu_tutor_system

Formerly math_tutor_system.

Local-first K12 multi-student, multi-grade, multi-subject tutoring system for curriculum-aware mistake tracking, worksheet generation, data governance, and future subject rendering.

## v0.1.6 Positioning

v0.1.6 is **Clean Schema Cutover & Cross-subject Text Exam Validation**.

This version intentionally stops carrying old runtime data and old schema fields forward:

- Default runtime DB is now `data/edu_tutor.db`.
- Legacy runtime DB `data/math_tutor.db` is deprecated and archived before first clean cutover.
- Old mistakes / worksheets / worksheet_items data is not migrated.
- The clean DB stores canonical code / id fields only.
- The import layer still accepts Chinese names and legacy input fields, but preview normalizes them before confirm.
- v0.1.6 still does not call any API, does not do OCR, does not generate PDF, and does not render math geometry / physics diagrams / chemical formulas.

## Database

Initialize:

```bash
python -m src.db
```

Behavior:

- Ensures `data/` and output folders exist.
- If `data/math_tutor.db` exists and `data/edu_tutor.db` does not, backs it up to `backups/pre_v016_clean_cutover/YYYYMMDD_HHMMSS/math_tutor.db`.
- Creates `data/edu_tutor.db` with clean v0.1.6 schema.
- Writes `schema_meta`:
  - `project_name=edu_tutor_system`
  - `schema_version=0.1.6`
  - `db_name=edu_tutor.db`
- Seeds `mistake_tags` from `config/education/mistake_taxonomy.yaml`.
- Is idempotent and does not clear existing `edu_tutor.db` data.

## Canonical Schema

Removed DB columns:

- `question_type`
- `knowledge_point`
- `mistake_tag`
- `target_mistake_tag`
- `difficulty`

Canonical fields:

- mistakes: `question_type_code`, `knowledge_point_id`, `primary_mistake_tag_code`, `difficulty_code`
- worksheet_items: `question_type_code`, `knowledge_point_id`, `target_mistake_tag_code`, `difficulty_code`

Difficulty codes:

- `basic` = 基础
- `medium` = 中等
- `advanced` = 提高
- `challenge` = 浅奥

## Normalize Input

Recommended mistakes YAML uses canonical fields:

```yaml
mistakes:
  - student_id: "daughter"
    subject_id: "physics"
    grade_at_time: 8
    term_at_time: "八年级上"
    curriculum_version_at_time: "cn_k12_2022"
    date: "2026-06-01"
    question_type_code: "physics_calculation"
    knowledge_point_id: "physics_g8_speed"
    primary_mistake_tag_code: "PHY_F1"
    difficulty_code: "basic"
    question_summary: "速度公式应用错误"
```

Legacy input aliases are accepted only at import-preview time:

- `question_type`
- `knowledge_point`
- `mistake_tag`
- `target_mistake_tag`
- `difficulty`

Preview normalizes them inside current `student_id + subject_id + grade_at_time + curriculum_version_at_time` scope. Confirm import writes only canonical fields.

## Display And Export

UI display uses `src/core/display.py`:

- `应用题 (math_application)`
- `速度 (physics_g8_speed)`
- `物理公式选错 (PHY_F1)`
- `基础 (basic)`

Exports include both code and display columns, for example:

- `question_type_code`
- `question_type_display`
- `knowledge_point_id`
- `knowledge_point_display`
- `primary_mistake_tag_code`
- `mistake_tag_display`
- `difficulty_code`
- `difficulty_display`

Exports no longer output old field names except as explicit `*_display` fields.

## UAT Samples

Canonical v0.1.6 samples:

- `samples/uat_v016_math_g6_mistakes.yaml`
- `samples/uat_v016_math_g7_mistakes.yaml`
- `samples/uat_v016_physics_g8_mistakes.yaml`
- `samples/uat_v016_chemistry_g9_mistakes.yaml`
- `samples/uat_v016_math_g6_worksheet.yaml`
- `samples/uat_v016_math_g7_worksheet.yaml`
- `samples/uat_v016_physics_g8_worksheet.yaml`
- `samples/uat_v016_chemistry_g9_worksheet.yaml`

UAT students are inactive and do not affect default active student `daughter`:

- `config/students/uat_student_math_g6.yaml`
- `config/students/uat_student_math_g7.yaml`
- `config/students/uat_student_physics_g8.yaml`
- `config/students/uat_student_chemistry_g9.yaml`

## UAT DB Helper

```bash
python scripts/uat_db.py status
python scripts/uat_db.py init
python scripts/uat_db.py restore
```

`init` backs up current `data/edu_tutor.db`, deletes it, and rebuilds a clean UAT DB. UAT sample data must still be imported through YAML preview -> confirm.

## Schema Integrity

Programmatic use:

```python
from src.core.schema_integrity import check_schema_integrity
report = check_schema_integrity()
```

The report contains `errors`, `warnings`, and `info`, including DB path, schema meta, legacy-column checks, canonical-field checks, domain validation, orphan worksheet items, duplicate hashes, and confirmed sample-data warnings.

## Public APIs Kept

These import paths remain stable:

- `preview_mistakes_payload`
- `confirm_mistakes_import`
- `preview_worksheet_payload`
- `confirm_worksheet_import`

## Streamlit

Run:

```bash
streamlit run src/app.py
```

Home shows `edu_tutor_system v0.1.6`, DB path, schema version, and clean schema cutover status. Data management uses `data/edu_tutor.db` for backup/export and can show schema integrity.

## Tests

```bash
python -m pytest
python -c "import src.app; print('APP_IMPORT_OK')"
```

## Docs

- `docs/SCHEMA_AUDIT_v0.1.6.md`
- `docs/HANDOFF_v0.1.6.md`

## v0.2 Boundary

v0.2 may build on this clean schema for Subject Rendering Layer:

- visuals
- math_geometry
- formula_block
- physics_formula
- physics_diagram
- chemical_formula
- chemical_equation

v0.1.6 deliberately does not implement those renderers.

# SCHEMA_AUDIT v0.1.6

## Summary

v0.1.6 is the clean schema cutover for `edu_tutor_system`. The runtime DB is now `data/edu_tutor.db`. The old `data/math_tutor.db` is treated as legacy and is archived before the first clean DB initialization when no `edu_tutor.db` exists.

No old mistakes / worksheets / worksheet_items business data is migrated.

## Legacy Archive Strategy

If `data/math_tutor.db` exists and `data/edu_tutor.db` does not, `python -m src.db` copies the old DB to:

```text
backups/pre_v016_clean_cutover/YYYYMMDD_HHMMSS/math_tutor.db
```

The legacy DB is not deleted by the initializer.

## New Runtime DB

Default DB:

```text
data/edu_tutor.db
```

`schema_meta` contains:

- `project_name = edu_tutor_system`
- `schema_version = 0.1.6`
- `db_name = edu_tutor.db`

## Tables

### schema_meta

Purpose: schema identity and version metadata.

Fields: `key`, `value`, `updated_at`.

### import_batches

Purpose: audit preview/confirm import batches.

Fields: `id`, `import_type`, `student_id`, `subject_id`, `grade_at_time`, `source_name`, `source_hash`, `status`, `total_count`, `imported_count`, `skipped_duplicate_count`, `warning_count`, `error_count`, `created_at`, `updated_at`.

### mistake_tags

Purpose: seeded tag registry cache from `config/education/mistake_taxonomy.yaml`.

Fields: `code`, `name`, `scope`, `subjects`, `active`, `description`, `created_at`, `updated_at`.

### mistakes

Purpose: clean canonical mistake records.

Fields: `id`, `student_id`, `subject_id`, `grade_at_time`, `term_at_time`, `curriculum_version_at_time`, `textbook_version_at_time`, `date`, `question_type_code`, `knowledge_point_id`, `primary_mistake_tag_code`, `difficulty_code`, `question_summary`, `wrong_answer_summary`, `correct_answer_summary`, `training_needed`, `source`, `status`, `import_batch_id`, `record_hash`, `created_at`, `updated_at`.

### worksheets

Purpose: worksheet headers.

Fields: `id`, `student_id`, `subject_id`, `grade_at_time`, `term_at_time`, `curriculum_version_at_time`, `textbook_version_at_time`, `title`, `date`, `source`, `status`, `worksheet_hash`, `import_batch_id`, `created_at`, `updated_at`.

### worksheet_items

Purpose: worksheet questions.

Fields: `id`, `worksheet_id`, `question_no`, `section_name`, `section_layout`, `question_type_code`, `knowledge_point_id`, `target_mistake_tag_code`, `difficulty_code`, `question`, `answer`, `explanation`, `created_at`, `updated_at`.

### training_prompts / weekly_reviews / llm_call_logs

Purpose: retained mature workflow tables. They are active compatibility tables, not old mistake schema tables.

## Deprecated Fields

These fields are not created in the clean DB:

- `question_type`
- `knowledge_point`
- `mistake_tag`
- `target_mistake_tag`
- `difficulty`

## Canonical Fields

The DB stores:

- `question_type_code`
- `knowledge_point_id`
- `primary_mistake_tag_code`
- `target_mistake_tag_code`
- `difficulty_code`

## Normalize Layer

`src/core/normalization.py` accepts canonical inputs and legacy Chinese inputs. Legacy fields are aliases only. Matching is exact and scoped:

- question type: current subject plus general types
- knowledge point: current subject, grade, curriculum version
- mistake tag: general plus current subject
- difficulty: `basic`, `medium`, `advanced`, `challenge`

Unknown knowledge points are warnings and are not written as free text ids.

## UI Display Strategy

`src/core/display.py` resolves code/id to display text:

- `应用题 (math_application)`
- `速度 (physics_g8_speed)`
- `物理公式选错 (PHY_F1)`
- `基础 (basic)`

## Export Strategy

Exports contain code + display fields and do not output old field names. CSV/YAML export is implemented in `src/core/backup_export.py`.

## Public API

Kept stable:

- `preview_mistakes_payload`
- `confirm_mistakes_import`
- `preview_worksheet_payload`
- `confirm_worksheet_import`

## v0.2 Stable Base

v0.2 can rely on:

- clean canonical DB fields
- normalized import preview
- subject/grade/curriculum scoped registry
- display resolver
- YAML preview/confirm boundary
- duplicate guard
- HTML worksheet export for plain text

## Known Risks

- Curriculum remains representative, not full textbook coverage.
- Existing old runtime data is intentionally not migrated.
- UAT samples are for validation and should not be treated as real student statistics.
- Rendering capabilities are declared but not implemented until v0.2.

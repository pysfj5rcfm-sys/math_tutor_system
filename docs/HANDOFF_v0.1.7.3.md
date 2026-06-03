# HANDOFF v0.1.7.3

Version: v0.1.7.3

Positioning: Clean Registry Rebuild & No-Legacy Cutover.

## Completed

- Removed `config/knowledge_points.yaml` from active runtime and archived old root registry files.
- Rebuilt Grade 6 math, Chinese, and English curriculum scope as the only active knowledge point source.
- Removed `legacy_names` from active question type and difficulty configs.
- Rebuilt `config/alias_mappings.yaml` as subject-scoped aliases.
- Rebuilt `config/education/mistake_taxonomy.yaml` with namespaced active tags.
- Removed old bare active tags from registry and DB seed.
- Fixed `config/worksheet_policy.yaml` by moving subject ratios into `subject_difficulty_policy`.
- Added `src/core/display_contract.py` for filter labels, DataFrame formatting, duplicate display, and export display.
- Updated prompt generation to require subject scope and avoid all-subject default prompts.
- Cleaned UAT samples for v0.1.7.3 and archived earlier samples.
- Added `scripts/audit_registry_health.py`.
- Added v0.1.7.3 pytest coverage.

## Active Knowledge Point Source

Only curriculum files are active:

- `config/curriculum/cn_k12_2022/math/grade_6.yaml`
- `config/curriculum/cn_k12_2022/chinese/grade_6.yaml`
- `config/curriculum/cn_k12_2022/english/grade_6.yaml`

`config/knowledge_points.yaml` is not in active runtime.

## Database

The clean schema remains v0.1.6. Registry metadata is expected to be:

- `registry_version = 0.1.7.3`
- `registry_mode = no_legacy`

Before rebuilding the real DB, back up `data/edu_tutor.db` under:

- `backups/pre_v0173_no_legacy_cutover/{timestamp}/edu_tutor.db`

Do not migrate old mistakes, worksheets, worksheet items, or old mistake tags.

## Prompt Rules

Prompt generation now requires a selected subject when the student has multiple active subjects.

Default prompts inject only:

- active student profile
- selected subject question types
- selected subject Grade 6 curriculum scope
- general plus selected subject mistake tags
- selected subject worksheet policy
- selected subject difficulty guidance

Prompts do not inject archived knowledge points, old aliases, old bare tags, or rendering fields.

## Display And Export

Business pages and export helpers should use `src/core/display_contract.py`.

Filter option values are canonical code/id values. Labels are display strings such as `文本证据 (chinese_g6_text_evidence)`.

## UAT Samples

Current samples are:

- `samples/uat_v0173_math_g6_mistakes.yaml`
- `samples/uat_v0173_math_g6_worksheet.yaml`
- `samples/uat_v0173_chinese_g6_mistakes.yaml`
- `samples/uat_v0173_chinese_g6_worksheet.yaml`
- `samples/uat_v0173_english_g6_mistakes.yaml`
- `samples/uat_v0173_english_g6_worksheet.yaml`
- `samples/uat_v0173_cross_subject_alias_ambiguous.yaml`
- `samples/uat_v0173_invalid_cross_subject_knowledge_point.yaml`

They are fixtures only and are not automatically imported.

## Still Not v0.2

No Subject Rendering Layer, visuals, render blocks, diagrams, formula rendering, chemical equation rendering, PDF, OCR, API, Agent SDK, server, cloud sync, or SaaS permissions were added.

The registry is representative, not a complete Grade 6 textbook library.

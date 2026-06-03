# edu_tutor_system

Current version: v0.1.8.1

Positioning: Math G6A X/Y Registry Registration & Target Matrix Prompt Protocol.

`edu_tutor_system` is a local-first tutoring data system for plain-text K12 mistake records, worksheet YAML validation, prompt generation, duplicate checks, backup, export, and schema integrity checks.

## Active Scope

- Active student: `daughter` / 陈照雨
- Current grade: 6
- Current term: 六年级上
- Active subjects: `math`, `chinese`, `english`
- Curriculum version: `cn_k12_2022`
- Textbook version: math Grade 6A uses `沪教版`; other subject textbook versions remain as configured
- School context: 上海市闵行区，上宝中学

The current registry keeps the existing three-subject runtime, and v0.1.8.1 completes the research-source audit for the metadata-rich沪教版六年级上数学 X/Y registry. It does not claim any unpublished school-specific content.

## No-Legacy Cutover

v0.1.8.1 keeps the v0.1.7.3 no-legacy runtime path.

- Active knowledge point source of truth: `config/curriculum/cn_k12_2022/{subject}/grade_*.yaml`
- `config/knowledge_points.yaml` has been removed from active runtime and archived under `archive/deprecated_v0173/`
- Root-level old registry files were archived and are not loaded by `RuleRegistry`
- `legacy_names` was removed from question type and difficulty configs
- `alias_mappings.yaml` was rebuilt as subject-scoped aliases only
- Old bare mistake tags such as `C3`, `F3`, `R4`, `M2`, `U1`, and `G1` are not active canonical codes
- The database is rebuilt from the clean schema and seeded only with active namespaced tags

Active math v0.1.8.1 mistake tags use explicit codes such as `MATH_SIGN_RULE_ERROR`, `MATH_QUANTITATIVE_RELATION_ERROR`, and `MATH_EQUALITY_RELATION_ERROR`, plus report-scoped `GEN_*` tags for reading/checking mechanisms. Existing non-math subject tags remain subject-scoped.

## Plain Text Boundary

v0.1.8.1 is still not v0.2.

The system does not implement Subject Rendering Layer, visuals, render blocks, diagrams, SVG rendering, formula rendering, chemical equation rendering, PDF generation, OCR, API calls, Agent SDK integration, server features, cloud sync, or SaaS permissions.

Prompt templates explicitly ask GPT to output plain-text YAML only and not invent visual/rendering fields.

## Registry Files

Active registry:

- `config/students/daughter.yaml`
- `config/education/subjects.yaml`
- `config/education/grades.yaml`
- `config/education/stages.yaml`
- `config/education/question_types.yaml`
- `config/education/mistake_taxonomy.yaml`
- `config/education/difficulty_levels.yaml`
- `config/alias_mappings.yaml`
- `config/worksheet_policy.yaml`
- `config/curriculum/cn_k12_2022/math/grade_6.yaml`
- `config/curriculum/cn_k12_2022/chinese/grade_6.yaml`
- `config/curriculum/cn_k12_2022/english/grade_6.yaml`

Archived historical files:

- `archive/deprecated_v0173/config/`
- `archive/deprecated_v0173/samples/`
- `archive/deprecated_v0173/tests/`

Archived files are not scanned as active runtime sources.

## Prompt Generation

Prompt generation is subject-scoped by default.

Required scope:

- `student_id`
- `subject_id`
- `grade_at_time`
- `curriculum_version_at_time`

For `daughter`, `subject_id` must be selected because the active student has three active subjects. The system does not generate a default all-subject giant prompt.

Subject prompts inject only:

- the selected subject's question types
- the selected subject and grade curriculum knowledge points
- general tags plus selected subject tags
- the selected subject worksheet policy
- the selected subject difficulty guidance
- the active student profile

Math v0.1.8.1 prompts also inject knowledge-point metadata such as `micro_skill`, `typical_question_forms`, `usage_status`, `suitable_difficulty`, and `suitable_mistake_tags`; and mistake-tag metadata such as `definition`, `use_when`, `do_not_use_when`, `typical_symptoms`, `next_training_strategy`, `severity`, `allowed_secondary`, and `primary_priority`.

## Math X/Y Target Matrix

v0.1.8.1 defines:

- X axis: `knowledge_point_id`
- Y axis: `primary_mistake_tag_code`
- Target pair: `knowledge_point_id x primary_mistake_tag_code`

`src/core/target_matrix.py` can build a read-only target matrix from confirmed mistakes using existing canonical columns. It does not create a table or change the import schema.

School training方式 is not registered as a third schema axis. Worksheet prompts ask GPT to retrieve similar school examples from the project knowledge base and extract only question structure, training steps, asking style, and difficulty rhythm. GPT must not copy original school questions or write school question numbers into YAML.

Prompt files saved under `outputs/prompts/` are written as UTF-8 and include subject id in the filename.

## Display And Filter Contract

Business UI and export formatting use `src/core/display_contract.py`.

Filter option contract:

- value: canonical code/id
- label: Chinese name plus canonical code/id

Examples:

- `chinese_g6_text_evidence` -> `文本证据 (chinese_g6_text_evidence)`
- `english_g6_reading_detail` -> `阅读细节定位 (english_g6_reading_detail)`
- `MATH_SIGN_RULE_ERROR` -> `符号规则错误 (MATH_SIGN_RULE_ERROR)`

DataFrames and exports separate canonical fields from display fields:

- `knowledge_point_id`
- `knowledge_point_display`
- `question_type_code`
- `question_type_display`
- `primary_mistake_tag_code` or `target_mistake_tag_code`
- `mistake_tag_display`
- `difficulty_code`
- `difficulty_display`

## Samples

UAT fixtures:

- `samples/uat_v0173_math_g6_mistakes.yaml`
- `samples/uat_v0173_math_g6_worksheet.yaml`
- `samples/uat_v018_math_g6a_xy_mistakes.yaml`
- `samples/uat_v018_math_g6a_xy_worksheet.yaml`
- `samples/uat_v0173_chinese_g6_mistakes.yaml`
- `samples/uat_v0173_chinese_g6_worksheet.yaml`
- `samples/uat_v0173_english_g6_mistakes.yaml`
- `samples/uat_v0173_english_g6_worksheet.yaml`
- `samples/uat_v0173_cross_subject_alias_ambiguous.yaml`
- `samples/uat_v0173_invalid_cross_subject_knowledge_point.yaml`

Samples are fixtures only. They are not automatically imported and are not default learning statistics.

## Database

Runtime DB:

- `data/edu_tutor.db`

Clean schema remains v0.1.6. v0.1.8.1 changes registry configuration, prompt protocol, docs, samples, and seed data, not table structure.

Expected `schema_meta`:

- `schema_version = 0.1.6`
- `project_name = edu_tutor_system`
- `db_name = edu_tutor.db`
- `registry_version = 0.1.8.1`
- `registry_mode = no_legacy`

## Validation Commands

Use the available Python interpreter for the environment:

```powershell
python -m src.db
python -m pytest
python -c "import src.app; print('APP_IMPORT_OK')"
python scripts/uat_db.py status
python scripts/audit_registry_health.py
```

If the shell does not expose `python`, run the same commands with the full interpreter path.

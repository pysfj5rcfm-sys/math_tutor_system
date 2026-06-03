# HANDOFF v0.1.7

## Project

Project name: `edu_tutor_system`

Formerly: `math_tutor_system`

Current version: `v0.1.7`

Positioning: Grade 6 Three-subject Rule Registry Initialization.

## What v0.1.7 Did

- Upgraded active student `daughter` to Grade 6 / `六年级上`.
- Set active subjects to `math`, `chinese`, and `english`.
- Marked Chinese and English as `supported_now: true`.
- Registered representative Grade 6 math/chinese/english question types.
- Registered representative Grade 6 math/chinese/english knowledge points in curriculum files.
- Added math-specific, Chinese-specific, and English-specific mistake tags.
- Kept general tags such as `R4` and `M2` usable across the three active subjects.
- Added Grade 6 worksheet policies for math/chinese/english.
- Added subject-scoped alias lookup and ambiguity handling.
- Updated normalization, display resolver, prompts, schema examples, and schema integrity checks.
- Added v0.1.7 UAT samples and pytest coverage.
- Kept v0.1.6 clean schema intact.

## v0.1.7.1 Patch

Positioning: Registry UI Cleanup & Legacy Knowledge Points Demotion.

What changed:

- Clarified that active v0.1.7+ knowledge point source of truth is `config/curriculum/cn_k12_2022/{subject}/grade_*.yaml`.
- Demoted `config/knowledge_points.yaml` to legacy compatibility.
- Updated the Rule Registry page so Current Student Scope and Global Curriculum Registry appear before legacy values.
- Renamed the old page section to Legacy Knowledge Points / 历史兼容知识点.
- Added Registry Source Debug showing curriculum files plus `config/knowledge_points.yaml legacy compatibility`.
- Added explicit registry APIs for curriculum vs legacy knowledge points.
- Updated validation repair prompts to use subject/grade scoped curriculum knowledge points by default.
- Missing `subject_id` or `grade_at_time` in repair context now asks for context instead of falling back to legacy knowledge points.

No DB schema changes were made. `schema_meta.schema_version` remains `0.1.6`.

## v0.1.7.2 Patch

Positioning: Prompt Scope & Display Consistency Cleanup.

What changed:

- Marking and worksheet prompt generation is now subject-scoped by default.
- Prompt generation requires an explicit `subject_id` when the active student has multiple active subjects.
- Streamlit prompt pages now choose `student_id` and one `subject_id`, then show the resolved prompt scope before rendering the copy area.
- Default prompts inject only the selected subject's question types, curriculum knowledge points, general + subject-specific mistake tags, subject-scoped aliases, and matching Grade 6 worksheet policy.
- The app may still show all-subject overview/debug sections, but those are not the default copy prompt.
- Repair prompts continue to use curriculum-scoped context and do not fall back to legacy knowledge points when `subject_id` or `grade_at_time` is missing.
- Prompt templates are loaded with UTF-8, saved prompt files are UTF-8, and HTML templates contain `<meta charset="utf-8">`.
- Added mojibake regression checks for generated marking, worksheet, and repair prompts.
- Business display now uses canonical id/code plus display columns for mistakes, exports, and duplicate summaries.
- `knowledge_point_display` resolves active curriculum labels first and marks legacy compatibility fallback with `[legacy]`.
- CSV exports use `utf-8-sig`; YAML exports keep `allow_unicode=True` and `sort_keys=False`.

No DB schema changes were made. `schema_meta.schema_version` remains `0.1.6`. v0.1.7.2 still does not implement v0.2 rendering fields.

## Updated Config

- `config/students/daughter.yaml`
- `config/education/subjects.yaml`
- `config/education/question_types.yaml`
- `config/education/difficulty_levels.yaml`
- `config/education/mistake_taxonomy.yaml`
- `config/worksheet_policy.yaml`
- `config/alias_mappings.yaml`
- `config/curriculum/cn_k12_2022/math/grade_6.yaml`
- `config/curriculum/cn_k12_2022/chinese/grade_6.yaml`
- `config/curriculum/cn_k12_2022/english/grade_6.yaml`

## Knowledge Point Source Layers

Active source of truth:

- `config/curriculum/cn_k12_2022/math/grade_6.yaml`
- `config/curriculum/cn_k12_2022/chinese/grade_6.yaml`
- `config/curriculum/cn_k12_2022/english/grade_6.yaml`
- other `config/curriculum/**/grade_*.yaml` files for registered subjects/grades

Legacy compatibility:

- `config/knowledge_points.yaml`

The legacy file is retained for early `math_tutor_system` compatibility, old samples, and alias target validation fallback. It is not the active current-student knowledge point scope.

## New Question Type Codes

Math:

- `math_calculation`
- `math_equation`
- `math_unit_conversion`
- `math_geometry_calculation`
- `math_application`
- `math_reading_application`

Chinese:

- `chinese_reading`
- `chinese_summary`
- `chinese_text_evidence`
- `chinese_poetry`
- `chinese_language_expression`
- `chinese_composition_outline`
- `chinese_composition_fragment`
- `chinese_revision`

English:

- `english_vocabulary`
- `english_grammar`
- `english_reading`
- `english_listening_dictation`
- `english_sentence_rewrite`
- `english_writing_short`
- `english_cloze`
- `english_speaking_prompt`

## New Knowledge Point IDs

Math:

- `math_g6_number_operations`
- `math_g6_fraction_decimal_percent`
- `math_g6_equation_basic`
- `math_g6_algebra_expression`
- `math_g6_application_modeling`
- `math_g6_geometry_measurement`
- `math_g6_unit_conversion`
- `math_g6_statistics_average`
- `math_g6_ratio_percent_intro`
- `math_g6_negative_number_intro`

Chinese:

- `chinese_g6_reading_summary`
- `chinese_g6_reading_inference`
- `chinese_g6_text_evidence`
- `chinese_g6_answer_structure`
- `chinese_g6_poetry_intro`
- `chinese_g6_classical_intro`
- `chinese_g6_composition_structure`
- `chinese_g6_composition_detail`
- `chinese_g6_language_expression`
- `chinese_g6_reading_stamina`

English:

- `english_g6_vocabulary_core`
- `english_g6_word_chunks`
- `english_g6_tense_basic`
- `english_g6_subject_verb_agreement`
- `english_g6_preposition_article`
- `english_g6_reading_detail`
- `english_g6_reading_inference`
- `english_g6_listening_dictation`
- `english_g6_sentence_writing`
- `english_g6_short_composition`
- `english_g6_speaking_retell`

## New Mistake Tag Codes

Math:

- `MATH_MODEL_1`
- `MATH_CHECK_1`
- `MATH_EXPR_1`

Chinese:

- `CHN_SUM_1`
- `CHN_EVD_1`
- `CHN_Q_1`
- `CHN_STRUCT_1`
- `CHN_POE_1`
- `CHN_COMP_1`
- `CHN_COMP_2`
- `CHN_LANG_1`

English:

- `ENG_VOC_1`
- `ENG_CHUNK_1`
- `ENG_GRAM_1`
- `ENG_GRAM_2`
- `ENG_GRAM_3`
- `ENG_READ_1`
- `ENG_READ_2`
- `ENG_LISTEN_1`
- `ENG_WRITE_1`
- `ENG_WRITE_2`
- `ENG_SPEAK_1`

## Subject-scoped Aliases

`config/alias_mappings.yaml` now supports scoped sections such as:

- `question_type_aliases.chinese.阅读理解 -> chinese_reading`
- `question_type_aliases.english.阅读理解 -> english_reading`

If a caller omits `subject_id` and the alias has multiple subject-specific targets, normalization reports ambiguity instead of guessing.

## Prompt Use

Prompts now inject:

- active student `daughter`
- current Grade 6 context
- active subject registry
- subject-specific `question_type_code`
- subject+grade `knowledge_point_id`
- general + subject-specific mistake tags
- difficulty codes
- worksheet policy templates
- subject-scoped alias mappings

Prompts continue to forbid v0.2 render fields and require plain text YAML only.

Repair prompts now use curriculum-scoped knowledge points when the original YAML contains `subject_id` and `grade_at_time`. They no longer inject `config/knowledge_points.yaml` by default.

## UAT Samples

Added:

- `samples/uat_v017_math_g6_mistakes.yaml`
- `samples/uat_v017_math_g6_worksheet.yaml`
- `samples/uat_v017_chinese_g6_mistakes.yaml`
- `samples/uat_v017_chinese_g6_worksheet.yaml`
- `samples/uat_v017_english_g6_mistakes.yaml`
- `samples/uat_v017_english_g6_worksheet.yaml`
- `samples/uat_v017_cross_subject_alias_ambiguous.yaml`
- `samples/uat_v017_invalid_cross_subject_knowledge_point.yaml`

They are fixtures only and are not automatically imported.

## Still Not Done

- No v0.2 Subject Rendering Layer.
- No visuals or render blocks.
- No diagram/formula/chemical equation rendering.
- No PDF/OCR/API/service/cloud/SaaS layer.
- No destructive DB migration.
- No old `math_tutor.db` migration.
- No full textbook knowledge base.
- No confirmed 上宝中学校本 material registry.

## v0.2 Notes

v0.2 can build on:

- clean canonical DB fields
- subject/grade/curriculum scoped Rule Registry
- subject-scoped alias handling
- preview normalization boundary
- display resolver
- schema integrity checks
- plain-text worksheet import/export

Before v0.2 rendering, do not add render fields to YAML samples or prompts as accepted output.

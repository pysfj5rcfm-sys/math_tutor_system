# Math G5B Knowledge Registry Audit v0.1.9.1-pretrial

Source file: `docs/research/source/五年级下数学_knowledge_point_id候选命名.md`

Purpose: register 沪教版五年级下数学 X-axis knowledge points for historical mistake backfill, grade 5B paper review, and old-foundation remediation before grade 6A. This audit does not change the Y-axis math mistake taxonomy, DB schema, or v0.2 rendering boundary.

## Registered Scope

- Curriculum config: `config/curriculum/cn_k12_2022/math/grade_5.yaml`
- Registry name: `math_g5b_knowledge_registry`
- Registry version: `v0.1.9.1-pretrial`
- Unit count: 6
- Lesson count: 15
- Registered `math_g5b_*` knowledge_point count: 23
- New-teaching mainline points: 16 `core_active`
- Review/backfill points: 7 `review_active`
- Review-only points: 2, preserved with `metadata.scope_note: review_only_for_hujiao_g5b`

## New Teaching Mainline

- 正数和负数的初步认识: `math_g5b_positive_negative_context_meaning`, `math_g5b_positive_negative_number_line_basic`, `math_g5b_positive_negative_size_comparison`, `math_g5b_temperature_change_context`
- 简易方程（二）: `math_g5b_equal_relation_from_text`, `math_g5b_equation_model_from_word_problem`, `math_g5b_equation_solution_check`
- 几何小实践: `math_g5b_cubic_unit_recognition`, `math_g5b_rectangular_prism_volume_formula`, `math_g5b_cube_volume_formula`, `math_g5b_composite_solid_volume_decomposition`, `math_g5b_surface_area_concept`, `math_g5b_volume_capacity_distinction`
- 问题解决: `math_g5b_speed_time_distance_relation`, `math_g5b_multi_step_problem_strategy`
- 可能性: `math_g5b_probability_likelihood_comparison`

## Review And Review-Only

Review/backfill points:

- `math_g5b_decimal_mixed_operation_order`
- `math_g5b_decimal_simplified_calculation`
- `math_g5b_equation_concept_review`
- `math_g5b_area_estimation_review`
- `math_g5b_natural_number_property_review`
- `math_g5b_data_table_reading_review`
- `math_g5b_fraction_concept_calculation_review`

Review-only handling:

- `math_g5b_data_table_reading_review`
- `math_g5b_fraction_concept_calculation_review`

Both are active, `review_active`, and carry `metadata.scope_note: review_only_for_hujiao_g5b`, so they can be used for grade 5B historical mistake attribution without being treated as new-teaching mainline points.

## Not Registered

- 总复习、错题诊所、单元检测、综合小卷: not knowledge points; assessment or activity wrappers.
- 同桌互批、小组讲题: classroom workflow, not X-axis curriculum content.
- Week/group/stage labels: school scheduling/prototype metadata, not registry ids.
- Student-specific wrong-cause labels and difficulty labels: belong to mistake records, worksheet items, or Y-axis taxonomy, not knowledge_point_id.

## Boundary Notes

五下正负数 / 数轴 vs 六上有理数 / 数轴:

- G5B keeps context meaning, direction, basic number-line placement, comparison, and temperature-change applications.
- G6A keeps the systematic rational-number layer: rational number concept, opposite number, absolute value, richer distance/position relations, and later algebraic reasoning.
- `math_g5b_positive_negative_context_meaning` intentionally does not merge into `math_g6a_rational_number_concept`.

五下简易方程 vs 六上方程 / 代数表达:

- G5B focuses on finding equal relations from text, setting an unknown, and solving grade 5 application problems.
- G6A keeps algebraic expression, one-step equation, rational-number sign handling, and more formal equation concepts.
- G5B equation ids use `review`, `from_text`, and `word_problem` wording to avoid implying full grade 6 algebra scope.

五下体积 / 表面积 / 容积 vs 六上几何 / 应用建模:

- G5B registers volume units, rectangular-prism/cube volume formulas, simple composite solids, surface area, and capacity distinction.
- G6A keeps broader geometry/data/unit support and later application-modeling connections.
- G5B spatial content remains practical and formula-oriented, not a v0.2 visual/rendering layer.

五下可能性 / 统计复习 vs later data reading:

- G5B probability is relative likelihood comparison in simple contexts.
- G5B statistics is review-only table/graph reading for historical attribution.
- G6A data reading remains the later current-grade target when the student is in grade 6A.

## Prompt And Alias Boundary

- Default daughter math prompt remains grade 6A and does not inject `math_g5b_*` knowledge points.
- Grade 5 math context can use `math_g5b_*` allowed points.
- Subject-scoped aliases were added for unambiguous G5B names; prompt rendering now filters aliases by current grade.
- No mistake-tag aliases were added.

## Integrity Expectations

- All registered ids start with `math_g5b_`.
- All ids are snake_case and contain no question number, week, group, school-stage marker, student cause, difficulty, or mistake tag.
- All `suitable_mistake_tags` come from the current active math-visible taxonomy.
- No `math_g6a_*` registry row was edited.
- No Y-axis taxonomy file was edited.
- No DB schema was edited.
- v0.2 remains out of scope.

# Math G6A X Registry Audit v0.1.8.1

Source:

- `docs/research/source/沪教版六年级上数学知识点体系深度研究报告(2).md`

## Conclusion

The source report states that the original candidate registry contains 35 knowledge points. The current v0.1.8.1 active config registers 18 math G6A knowledge point rows. This is an intentional MVP compression, not a claim that the 35-point candidate system is fully active.

The 18-row registry is sufficient for MVP target-matrix prompting because it preserves the highest-frequency X-axis training targets: rational number concepts, number-line representation, rational addition/subtraction, percentage modeling, and introductory equations. It is not sufficient as a full textbook registry. The omitted candidate points remain documented as review-only, merged, too fine for active MVP statistics, or future needs-review.

## Counts

- Source candidate knowledge points: 35
- Current registered knowledge point rows: 18
- Boolean `active: true`: 17
- `reserved_inactive`: 1

Current `usage_status` distribution:

- `core_active`: 13
- `review_active`: 2
- `intro_active`: 2
- `reserved_inactive`: 1

## Active Source Mapping

| active knowledge_point_id | source basis | audit note |
|---|---|---|
| `math_g6a_rational_number_concept` | `rational_number_concept`, `positive_negative_number_meaning` | merged_into; keeps positive/negative meaning in metadata |
| `math_g6a_number_line_representation` | `number_line_representation`, `order_comparison_on_number_line` | merged_into; order comparison is represented as typical question form |
| `math_g6a_opposite_absolute_value` | `opposite_number_definition`, `absolute_value_basic` | merged_into; source recommends both as core |
| `math_g6a_rational_add_same_sign` | `rational_add_same_sign` | direct |
| `math_g6a_rational_add_different_sign` | `rational_add_different_sign` | direct; key X target for sign errors |
| `math_g6a_rational_subtract_as_add_opposite` | `rational_subtract_as_add_opposite` | direct |
| `math_g6a_rational_mixed_operations` | `rational_mixed_operations` | direct, with bracket/sign issues kept in metadata |
| `math_g6a_letter_expression` | `algebraic_expression_meaning`, `substitute_value_evaluation` | merged_into; source marks as intro_active |
| `math_g6a_equation_concept` | `equation_concept` | direct |
| `math_g6a_one_step_equation_solving` | `one_step_equation_solving` | direct but flagged too_coarse_needs_split_later |
| `math_g6a_equation_word_problem` | report discussion of equation/modeling bridge | needs_review; retained for target matrix coverage but not one of the 35 direct candidate ids |
| `math_g6a_ratio_meaning` | `ratio_concept`, `ratio_simplification` | merged_into |
| `math_g6a_percentage_meaning` | `percentage_meaning` | direct |
| `math_g6a_percentage_word_problem_model` | `percentage_word_problem_model` | direct but flagged too_coarse_needs_split_later |
| `math_g6a_line_angle_basic` | not in 35-point source table | needs_review; retained from v0.1.8 support registry |
| `math_g6a_circle_sector_basic` | not in 35-point source table | reserved_inactive; should stay inactive until source confirmation |
| `math_g6a_data_table_graph_reading` | training/report discussion of data extraction, not direct 35-point candidate | review_only |
| `math_g6a_unit_conversion_measurement` | Y-axis unit/measurement taxonomy support, not direct 35-point candidate | review_only |

## Unregistered Candidate Points

| source candidate | reason | target handling |
|---|---|---|
| `positive_negative_number_meaning` | merged_into | `math_g6a_rational_number_concept` metadata |
| `order_comparison_on_number_line` | merged_into | `math_g6a_number_line_representation` metadata |
| `distance_on_number_line` | too_fine_for_active | future `needs_review`; do not activate until enough data |
| `midpoint_on_number_line` | too_fine_for_active | future `needs_review`; keep as review doc item |
| `opposite_number_definition` | merged_into | `math_g6a_opposite_absolute_value` |
| `absolute_value_basic` | merged_into | `math_g6a_opposite_absolute_value` |
| `absolute_value_with_condition` | too_fine_for_active | future `reserved_inactive` candidate |
| `remove_brackets_with_sign` | review_only | currently represented inside rational mixed operations metadata |
| `absolute_value_in_operations` | review_only | currently represented inside rational mixed operations metadata |
| `factor_multiple_concept` | review_only | not active MVP because v0.1.8 target matrix focuses rational/percentage/equation |
| `prime_composite_identification` | review_only | not active MVP |
| `common_factor_gcd` | review_only | bridge for fraction review, not active MVP |
| `common_multiple_lcm` | review_only | bridge for fraction review, not active MVP |
| `fraction_simplification` | review_only | keep in review docs; candidate for later review_active |
| `fraction_comparison` | review_only | keep in review docs |
| `fraction_add_subtract` | too_coarse_needs_split_later | source says split into same-denominator, common-denominator, word-problem |
| `fraction_multiply_divide` | too_coarse_needs_split_later | source says split multiplication basic and division as reciprocal |
| `ratio_simplification` | merged_into | `math_g6a_ratio_meaning` metadata |
| `proportion_definition` | review_only | future candidate if proportion unit becomes active target |
| `proportion_cross_multiplication` | review_only | future candidate if proportion unit becomes active target |
| `percentage_fraction_decimal_conversion` | review_only | should be considered for expansion before full release |
| `percentage_increase_decrease` | too_coarse_needs_split_later | source says distinguish increased by / increased to / decreased by / decreased to |
| `algebraic_expression_meaning` | merged_into | `math_g6a_letter_expression` |
| `substitute_value_evaluation` | merged_into | `math_g6a_letter_expression` |

## Required Issue Checks

- `fraction_add_subtract`: not active. Source says it is too coarse and should be split before activation.
- `fraction_multiply_divide`: not active. Source says it is too coarse and should be split before activation.
- `percentage_word_problem_model`: active, but too coarse. MVP keeps it because target-matrix examples require it; future split should include find percentage, find part, find whole.
- `one_step_equation_solving`: active, but too coarse. MVP keeps it as intro/core bridge; future split should separate additive, subtractive, multiplicative, divisive equations and checking.
- `distance_on_number_line`: not active. Too fine for MVP statistics unless enough school examples accumulate.
- `midpoint_on_number_line`: not active. Too fine for MVP statistics; candidate `needs_review`.
- `absolute_value_with_condition`: not active. Better as `reserved_inactive` or challenge extension.
- `usage_status`: current config uses the required vocabulary and keeps `reserved_inactive` inactive.

## Expansion Decision

Do not expand in v0.1.8.1. The 18-row active registry is enough for MVP X/Y prompt targeting, and expanding now would create a false sense of precision before split decisions are reviewed. The next high-value expansion should be:

- `math_g6a_percentage_fraction_decimal_conversion`
- split `math_g6a_percentage_word_problem_model`
- split `math_g6a_one_step_equation_solving`
- add fraction review points only after they are split as the source recommends

## Risk

Four current support nodes are not direct rows from the 35-point candidate table: `math_g6a_equation_word_problem`, `math_g6a_line_angle_basic`, `math_g6a_data_table_graph_reading`, and `math_g6a_unit_conversion_measurement`. They are retained for v0.1.8 compatibility and target coverage, but should be reviewed if the next release enforces a strict source-only X registry.

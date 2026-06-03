# Math Y Taxonomy Audit v0.1.8.1

Source:

- `docs/research/source/edu_tutor_system 数学 Mistake Tag Taxonomy 深度研究.md`

## Conclusion

The source report recommends 28 active math-relevant mechanism tags. v0.1.8.1 registers those 28 as the math-visible Y-axis taxonomy:

- 25 `MATH_*` tags
- 3 `GEN_*` tags scoped to math: `GEN_CONDITION_OMISSION`, `GEN_READING_KEYWORD_MISUNDERSTANDING`, `GEN_CHECKING_OMISSION`

Existing older `GEN_R*`, `GEN_M*`, and `GEN_CHECK_1` tags remain available for non-math subjects where already used, but they are no longer part of the math-visible v0.1.8.1 taxonomy.

## Registered Report Tags

| code | registered |
|---|---|
| `MATH_CONCEPT_DEFINITION_ERROR` | yes |
| `MATH_PREREQUISITE_CONCEPT_GAP` | yes |
| `MATH_RULE_APPLICATION_ERROR` | yes |
| `MATH_ALGORITHM_PROCEDURE_ERROR` | yes |
| `MATH_CALCULATION_EXECUTION_ERROR` | yes |
| `MATH_SIGN_RULE_ERROR` | yes |
| `MATH_SYMBOL_NOTATION_ERROR` | yes |
| `MATH_EQUALITY_RELATION_ERROR` | yes |
| `MATH_CONDITION_JUDGEMENT_ERROR` | yes |
| `GEN_CONDITION_OMISSION` | yes |
| `GEN_READING_KEYWORD_MISUNDERSTANDING` | yes |
| `MATH_REPRESENTATION_TRANSFER_ERROR` | yes |
| `MATH_QUANTITATIVE_RELATION_ERROR` | yes |
| `MATH_MODEL_CONSTRUCTION_ERROR` | yes |
| `MATH_METHOD_SELECTION_ERROR` | yes |
| `MATH_FORMULA_SELECTION_ERROR` | yes |
| `MATH_FORMULA_APPLICATION_ERROR` | yes |
| `MATH_MULTI_STEP_PLANNING_ERROR` | yes |
| `MATH_UNIT_MEANING_ERROR` | yes |
| `MATH_UNIT_CONVERSION_ERROR` | yes |
| `MATH_UNIT_LABEL_ERROR` | yes |
| `MATH_GEOMETRIC_PROPERTY_ERROR` | yes |
| `MATH_SPATIAL_VISUALIZATION_ERROR` | yes |
| `MATH_DATA_GRAPH_READING_ERROR` | yes |
| `MATH_PROCESS_EXPRESSION_ERROR` | yes |
| `MATH_MATHEMATICAL_LANGUAGE_ERROR` | yes |
| `MATH_ESTIMATION_NUMBER_SENSE_ERROR` | yes |
| `GEN_CHECKING_OMISSION` | yes |

## Required Boundary Checks

- `sign_symbol` category exists.
- `MATH_EQUALITY_RELATION_ERROR` exists independently and is not merged into concept-definition.
- `MATH_QUANTITATIVE_RELATION_ERROR` and `MATH_MODEL_CONSTRUCTION_ERROR` both exist. Relation extraction and model construction remain separate.
- `MATH_UNIT_MEANING_ERROR` and `MATH_UNIT_CONVERSION_ERROR` both exist. Unit meaning and conversion execution remain separate.
- Old bare tags such as `C3`, `R4`, `M2`, `F3`, `U1`, and `G1` are not active canonical tags.
- `YV-*` tags do not exist in active config.
- `allowed_secondary`, `conflict_with`, and `primary_priority` remain metadata only. No DB schema changes were made.

## GEN Tags

The report uses `GEN_*` for cross-mechanism behaviors that are not uniquely mathematical:

- condition omission
- reading keyword misunderstanding
- checking omission

In v0.1.8.1 these three are scoped to math for the math-visible taxonomy. Older generic tags remain available to Chinese/English only, preserving existing non-math samples while avoiding duplicate math Y-axis choices.

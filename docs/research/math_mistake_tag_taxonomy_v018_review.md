# Math Mistake Tag Taxonomy v0.1.8 Review

Active config:

- `config/education/mistake_taxonomy.yaml`

Registration summary:

- Math-visible report tags: 28
- Composition: 25 `MATH_*` tags plus 3 report `GEN_*` tags scoped to math.
- Older general tags remain available for non-math subjects where already used.
- No old bare canonical math tags are active.
- No `YV-*` tags are active.

Categories:

- `concept_definition`
- `rule_application`
- `calculation_execution`
- `sign_symbol`
- `condition_judgement`
- `representation_transfer`
- `modeling_relation`
- `method_formula_selection`
- `unit_measurement`
- `geometry_spatial`
- `data_graph_reading`
- `process_expression`
- `checking_estimation`
- `reading_comprehension`

Required retained distinctions:

- `MATH_EQUALITY_RELATION_ERROR` exists separately from `MATH_CONCEPT_DEFINITION_ERROR`.
- `MATH_QUANTITATIVE_RELATION_ERROR` and `MATH_MODEL_CONSTRUCTION_ERROR` are both retained. The former means relation extraction failed; the latter means extracted relations were organized into the wrong model.
- `MATH_UNIT_MEANING_ERROR` and `MATH_UNIT_CONVERSION_ERROR` are both retained. The former means量义/维度理解 error; the latter means进率/方向/换算 execution error.

Metadata handling:

- `allowed_secondary`: prompt/review metadata only.
- `conflict_with`: prompt/review metadata only.
- `primary_priority`: prompt selection guidance only.
- No DB schema fields were added.

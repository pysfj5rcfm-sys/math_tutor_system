# Target Matrix Protocol v0.1.8

Scope:

- X axis: `knowledge_point_id`
- Y axis: `primary_mistake_tag_code`
- Target pair: `knowledge_point_id x primary_mistake_tag_code`

Runtime helper:

- `src/core/target_matrix.py`
- `build_target_matrix_from_confirmed_mistakes(...)`
- `render_target_matrix_for_prompt(...)`

The helper reads existing confirmed `mistakes` rows and aggregates:

- `knowledge_point_id`
- `primary_mistake_tag_code`
- `count_7d`
- `count_30d`
- `latest_date`
- `priority`

No schema changes:

- No target matrix table.
- No secondary tag column.
- No school style registry.
- No worksheet prototype registry.

Prompt protocol:

Worksheet generation may use `target_matrix.items` as the canonical X/Y training target list. GPT may retrieve similar school training examples from the project knowledge base, but only to infer structure, scaffolding, asking style, and difficulty rhythm. GPT must not copy original questions, write school question numbers, or override the canonical X/Y targets.

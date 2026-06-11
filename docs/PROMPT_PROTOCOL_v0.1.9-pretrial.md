# Prompt Protocol v0.1.9-pretrial

Scope: trial-readiness upgrades for marking, worksheet generation, and repair prompts.

## Common Boundaries

- Use only runtime-injected `RuleRegistry` values for allowed question types, knowledge points, mistake tags, and difficulty codes.
- Do not invent code/id values.
- Do not restore legacy codes or aliases.
- Output valid YAML only, without Markdown fences.
- Keep the current plain-text schema boundary. Do not output visuals, diagrams, render blocks, SVG, PDF, OCR, or API fields.

## Marking Prompt

Each mistake row still has exactly one `primary_mistake_tag_code`.

Optional evidence fields:

- `diagnosis_confidence`: number from 0.0 to 1.0.
- `needs_human_review`: boolean.
- `secondary_mistake_tags`: 0-3 current allowed mistake tags.
- `diagnosis_evidence`: mapping of visible evidence and teaching diagnosis rationale.
- `alternative_diagnoses`: list of backup diagnoses with `code`, `reason`, and `confidence`.

Diagnosis order:

1. Reading and conditions.
2. Quantitative relation.
3. Model or expression construction.
4. Method or formula selection.
5. Rule or algorithm procedure.
6. Calculation execution.

If evidence is missing or ambiguous, lower confidence and set `needs_human_review: true`. Do not output private chain-of-thought; only output visible evidence and reviewable teaching rationale.

## Worksheet Prompt

Each question should keep the existing section-based schema and add:

- `primary_target_id`
- `question_role`
- `teaching_purpose`
- `expected_error_mechanism`

Allowed `question_role` values:

- `repair`: direct repair for the target mistake.
- `variant`: same knowledge point and mistake mechanism with changed context or representation.
- `transfer`: core structure moved to a new or lightly integrated context.
- `mixed_review`: low-priority spiral review.

Worksheet rules:

- Include at least one `repair` question.
- For 4 or more questions, try to include `repair`, `variant`, and `transfer`.
- Give each high-priority or main target at least one `repair` question.
- Do not generate only same-pattern drills.
- School examples may influence style and scaffolding only, not canonical X/Y targets or validation.

## Target Priority Light

Worksheet prompts may consume `target_priority_light.items[*].priority_band`.

GPT must not recalculate final priority. The helper is read-only prompt input and does not create `target_state`.

## Mastery Signal

Review prompts may output:

```yaml
mastery_update_signal:
  suggested_direction: "increase"
  suggested_status: "improving"
  confidence: 0.7
  reason: "Based on repair/variant/transfer performance."
```

This signal is not a formal `mastery_state` update in v0.1.9-pretrial.

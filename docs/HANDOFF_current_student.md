# Current Student Handoff

## Single Source of Truth

Runtime current student is resolved only by `src/core/current_student.py`.

Canonical entry points:

- `get_current_student_id(task_scope=None, registry=None)`
- `resolve_current_student(task_scope=None, registry=None)`
- `set_current_student(student_id, allow_uat=False, registry=None)`
- `resolve_task_scope(task_scope=None, subject_id=None, registry=None)`

The switching key is only `student_id`. `display_name`, `current_grade`, `current_term`, `school`, and `active_subjects` are never used as switching keys.

## active vs session_state

Strategy: `streamlit.session_state.current_student_id` is the runtime source of truth. The YAML `active: true` field is only a startup default for the resolver.

Resolver priority:

1. Explicit `task_scope.student_id` override.
2. `streamlit.session_state.current_student_id`.
3. In-memory runtime current student for tests/CLI/non-Streamlit calls.
4. First real student in config with `active: true`.
5. Fallback `student_id = "daughter"`.

`set_current_student(student_id)` validates the real student, updates runtime memory, and updates `streamlit.session_state.current_student_id` when Streamlit is active. It does not rewrite student YAML files or mutate DB active flags.

## Scope Derivation

`current_student` determines the default scope, not the registry itself.

Default scope:

`current_student_id -> student profile -> current_grade -> current_term -> curriculum_version -> textbook_version -> subject_id -> allowed knowledge points`

Math defaults:

- `daughter`: grade 6, term `六年级上`, subject `math`, default knowledge points from the grade 6A math curriculum (`math_g6a_*` scope).
- `sally`: grade 5, term `五年级下`, subject `math`, default knowledge points from the grade 5B math curriculum (`math_g5b_*` and other legal grade 5B scope entries).

`school` and `display_name` do not route registry scope. `active_subjects` only controls default subject choices. `curriculum_version` and `textbook_version` filter the curriculum scope; current textbook support is `generic`.

## Followed Call Paths

UI:

- Sidebar current student selector updates only `current_student_id`.
- Home/profile/rule registry pages use `registry.get_active_student()`, which delegates to the resolver.
- Mistake list and data-management filters default to current student/default subject/current grade.
- Marking prompt and worksheet prompt pages default to current student and update the same resolver if the page selector changes.
- Stats page filters by current student.
- Worksheet export selectors default to current student worksheets.

Prompt/YAML:

- Marking prompt, worksheet prompt, parse repair prompt, and validation repair prompt resolve through current student or explicit task scope.
- Allowed question type codes, mistake tags, knowledge points, alias mappings, worksheet policy, target matrix, and target priority light use the same resolved context.
- Missing YAML `student_id` defaults to the resolver current student.
- Explicit YAML `student_id` is preserved.
- If YAML `student_id` differs from current student, preview emits `yaml_student_id_differs_from_current_student`; confirm import still writes the YAML student.

Stats and targets:

- `stats_summary`, `tag_frequency`, `cross_stat`, `top_tags`, and `missing_data_alerts` accept `student_id` and are called with current student in UI/workflows.
- `build_target_matrix_from_confirmed_mistakes` and `build_target_priority_light` already filter by `student_id`.
- Weekly review filters stats by the profile student.
- Worksheet history/export defaults to current student and export rendering uses the worksheet record student, not the current UI student.

HTML/export:

- `get_worksheet_bundle()` enriches the worksheet record with `student_display_name` from the stored `student_id`.
- Student worksheet and answer sheet templates render `worksheet.student_id` / `student_display_name`; current UI student is not used for historical worksheet identity.

## task_scope Override

Backend support is implemented with `resolve_task_scope()` and optional `task_scope` parameters on marking and worksheet prompt builders.

Priority:

1. Explicit `task_scope` fields.
2. Current student default scope.

A historical review can pass:

```yaml
student_id: "daughter"
grade_at_time: 5
term_at_time: "五年级下"
subject_id: "math"
```

This injects grade 5B math scope for that task only. It does not modify `daughter.current_grade`.

Full UI controls for task-scope override are not yet built.

## UAT Isolation

Student configs now use `student_type: "real" | "uat"` where possible. The resolver also treats `student_id` starting with `uat_` or display names starting with `UAT` as UAT.

- `daughter` and `sally` are real students.
- UAT students are excluded from selectors by default.
- `show_uat_students=true` in the sidebar exposes UAT fixtures for manual testing.
- `set_current_student()` rejects UAT unless `allow_uat=True`.
- UAT rows do not enter real stats unless explicitly queried by UAT `student_id`.

## Remaining Hardcoding Audit

- Runtime fallback remains `DEFAULT_FALLBACK_STUDENT_ID = "daughter"` in `src/core/current_student.py`, by requirement.
- Tests and historical docs still contain `daughter` and grade 6 examples.
- `config/app_config.yaml` still contains a legacy default `student_id: "daughter"` but it is not the runtime resolver.
- No prompt path should display student A while injecting student B allowed lists: prompt builders resolve student, subject, context, allowed lists, alias mappings, and target payload from one context before rendering.

## Verification

- `pytest tests/test_current_student_chain.py -q`: 7 passed.
- `pytest tests/test_current_student_chain.py tests/test_v0173_prompt_scope.py -q`: 12 passed.
- `pytest -q`: 54 passed.
- `pytest --pyargs src.app -q`: imports `src.app` successfully; no tests are defined in that module.

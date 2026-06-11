# Registry Health Audit v0.1.8.1

Mode: no-legacy cutover.

- Total hits: 29
- Active unfixed hits: 0
- Inactive historical hits: 29

## Active Runtime Result

Active runtime scan passed: no unfixed mojibake, legacy runtime references, old bare active tags, prompt source leaks, or display/filter bypasses were detected.

## Inactive Historical Notes

- `legacy` `docs\HANDOFF_v0.1.5.md:7` marker=`math_tutor_system` active=False fixed=True: 旧名：math_tutor_system
- `legacy` `docs\HANDOFF_v0.1.5.md:15` marker=`math_tutor_system` active=False fixed=True: - 将项目说明、README、Streamlit 页面标题升级为 edu_tutor_system，并保留 formerly math_tutor_system 说明。
- `legacy` `docs\HANDOFF_v0.1.5.md:16` marker=`daughter_grade5` active=False fixed=True: - 新增 `config/students/daughter.yaml`，使用稳定 `student_id: daughter`，并通过 `legacy_student_ids` 兼容旧 `daughter_grade5`。
- `legacy` `docs\HANDOFF_v0.1.5.md:138` marker=`daughter_grade5` active=False fixed=True: - `daughter.yaml` 中 `legacy_student_ids: ["daughter_grade5"]` 用于兼容旧样例和历史数据。
- `legacy` `docs\HANDOFF_v0.1.5.md:155` marker=`legacy_names` active=False fixed=True: - 旧中文题型名通过 `name` / `legacy_names` 兼容。
- `legacy` `docs\HANDOFF_v0.1.5.md:292` marker=`daughter_grade5` active=False fixed=True: 旧样例中显式 `student_id: daughter_grade5` 通过 `legacy_student_ids` 兼容，不要求用户立即修改历史数据。
- `legacy` `docs\HANDOFF_v0.1.5.md:309` marker=`daughter_grade5` active=False fixed=True: - 明确处理 `daughter_grade5` 到 `daughter` 的历史身份兼容策略。
- `legacy` `docs\HANDOFF_v0.1.6.md:7` marker=`math_tutor_system` active=False fixed=True: Formerly: `math_tutor_system`
- `legacy` `docs\HANDOFF_v0.1.7.md:7` marker=`math_tutor_system` active=False fixed=True: Formerly: `math_tutor_system`
- `legacy` `docs\HANDOFF_v0.1.7.md:35` marker=`config/knowledge_points.yaml` active=False fixed=True: - Demoted `config/knowledge_points.yaml` to legacy compatibility.
- `legacy` `docs\HANDOFF_v0.1.7.md:38` marker=`config/knowledge_points.yaml` active=False fixed=True: - Added Registry Source Debug showing curriculum files plus `config/knowledge_points.yaml legacy compatibility`.
- `legacy` `docs\HANDOFF_v0.1.7.md:89` marker=`config/knowledge_points.yaml` active=False fixed=True: - `config/knowledge_points.yaml`
- `legacy` `docs\HANDOFF_v0.1.7.md:91` marker=`math_tutor_system` active=False fixed=True: The legacy file is retained for early `math_tutor_system` compatibility, old samples, and alias target validation fallback. It is not the ac
- `legacy` `docs\HANDOFF_v0.1.7.md:226` marker=`config/knowledge_points.yaml` active=False fixed=True: Repair prompts now use curriculum-scoped knowledge points when the original YAML contains `subject_id` and `grade_at_time`. They no longer i
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:15` marker=`math_tutor_system` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:7` marker=`math_tutor_system` active=False fixed=True: 旧名：math_tutor_system
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:16` marker=`math_tutor_system` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:15` marker=`math_tutor_system` active=False fixed=True: - 将项目说明、README、Streamlit 页面标题升级为 edu_tutor_system
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:17` marker=`daughter_grade5` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:16` marker=`daughter_grade5` active=False fixed=True: - 新增 `config/students/daughter.yaml`，使用稳定 `student_
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:18` marker=`daughter_grade5` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:138` marker=`daughter_grade5` active=False fixed=True: - `daughter.yaml` 中 `legacy_student_ids: ["daughte
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:19` marker=`legacy_names` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:155` marker=`legacy_names` active=False fixed=True: - 旧中文题型名通过 `name` / `legacy_names` 兼容。
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:20` marker=`daughter_grade5` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:292` marker=`daughter_grade5` active=False fixed=True: 旧样例中显式 `student_id: daughter_grade5` 通过 `legacy_st
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:21` marker=`daughter_grade5` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.5.md:309` marker=`daughter_grade5` active=False fixed=True: - 明确处理 `daughter_grade5` 到 `daughter` 的历史身份兼容策略。
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:22` marker=`math_tutor_system` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.6.md:7` marker=`math_tutor_system` active=False fixed=True: Formerly: `math_tutor_system`
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:23` marker=`math_tutor_system` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:7` marker=`math_tutor_system` active=False fixed=True: Formerly: `math_tutor_system`
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:24` marker=`config/knowledge_points.yaml` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:35` marker=`config/knowledge_points.yaml` active=False fixed=True: - Demoted `config/knowledge_points.yam
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:25` marker=`config/knowledge_points.yaml` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:38` marker=`config/knowledge_points.yaml` active=False fixed=True: - Added Registry Source Debug showing 
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:26` marker=`config/knowledge_points.yaml` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:89` marker=`config/knowledge_points.yaml` active=False fixed=True: - `config/knowledge_points.yaml`
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:27` marker=`math_tutor_system` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:91` marker=`math_tutor_system` active=False fixed=True: The legacy file is retained for early `math_tutor
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:28` marker=`config/knowledge_points.yaml` active=False fixed=True: - `legacy` `docs\HANDOFF_v0.1.7.md:226` marker=`config/knowledge_points.yaml` active=False fixed=True: Repair prompts now use curriculum-sco
- `legacy` `docs\REGISTRY_HEALTH_AUDIT_v0.1.7.3.md:37` marker=`config/knowledge_points.yaml` active=False fixed=True: - `config/knowledge_points.yaml` is not present in active runtime.

## Source Of Truth

- Active knowledge points: `config/curriculum/cn_k12_2022/{subject}/grade_*.yaml`
- Active question types: `config/education/question_types.yaml`
- Active mistake tags: `config/education/mistake_taxonomy.yaml`
- Active aliases: `config/alias_mappings.yaml`
- Active worksheet policy: `config/worksheet_policy.yaml`
- `config/knowledge_points.yaml` is not present in active runtime.

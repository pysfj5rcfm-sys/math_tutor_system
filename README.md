# edu_tutor_system

Formerly math_tutor_system.

A local-first K12 multi-subject tutoring system for student profiles, curriculum-aware mistake tracking, worksheet generation, and future subject rendering.

本项目原为 math_tutor_system，自 v0.1.5 起升级为 edu_tutor_system。目标是支持 K12 多学生、多年级、多学科的错因管理、课程范围管理、试卷生成与未来学科表达渲染。

## v0.1.5 定位

v0.1.5 是 Teaching Domain Model，不是渲染层。

本轮完成：

- 多学生配置入口：`config/students/*.yaml`。
- K12 学段、年级、学科配置：`config/education/`。
- 通用 + 学科专属 question_types。
- 通用 + 学科专属 mistake taxonomy，保留原 24 个数学错因 code。
- 跨学科 skills。
- subject expression capabilities 声明，为 v0.2 渲染层铺路。
- `cn_k12_2022` 多学科多年级课程骨架。
- Rule Registry 按 student / subject / grade 过滤知识点、题型、错因、能力声明。
- 批改 Prompt 和出题 Prompt 自动注入当前学生、学科、年级、课程范围。
- `mistakes.yaml` / `worksheet.yaml` 兼容旧格式，并可选带 student/subject/grade context。

本轮仍不做：

- 不接 OpenAI API，不产生 API 费用。
- 不做 OCR、照片识别、自动批改、自动出题。
- 不做 PDF。
- 不做数学几何 SVG、物理图示、化学结构式渲染。
- 不做公式渲染器。
- 不做服务端、云同步、SaaS 多租户权限。
- 不删除用户历史数据，不做破坏性数据库迁移。

## 版本路线

- v0.1.5：Teaching Domain Model。完成 K12 多学生、多年级、多学科教学体系的数据建模与配置骨架。
- v0.1.6：Schema Cleanup & Cross-subject Text Exam Validation。清理历史包袱，验证多学生、多年级、多学科文字类试卷拓展。
- v0.2：Subject Rendering Layer。支持数学图形、物理公式/图示、化学式/方程式/配方表达。

## 配置目录

```text
config/
  students/
    daughter.yaml
  education/
    subjects.yaml
    stages.yaml
    grades.yaml
    question_types.yaml
    skills.yaml
    mistake_taxonomy.yaml
    expression_capabilities.yaml
  curriculum/
    cn_k12_2022/
      math/grade_5.yaml ... grade_12.yaml
      physics/grade_8.yaml ... grade_12.yaml
      chemistry/grade_9.yaml ... grade_12.yaml
  student_profile.yaml
```

`config/student_profile.yaml` 已进入兼容层，推荐新配置使用 `config/students/*.yaml`。旧文件保留读取，旧 YAML 样例仍可用。

## 学生配置

新增学生：在 `config/students/` 下新增一个 YAML 文件，必须包含稳定的 `student_id`、`display_name`、`active`、`current_grade`、`current_term`、`curriculum_version`、`textbook_version`、`default_subjects`。

修改学生年级：直接修改同一个学生文件里的 `current_grade` 和 `current_term`。不要因为升年级新建割裂身份。

active student：当前 `active: true` 的学生作为默认学生。若多个学生同时 active，Rule Registry 会给出 warning，并默认使用第一个。

当前默认学生：

```yaml
student_id: "daughter"
current_grade: 6
current_term: "六年级上"
curriculum_version: "cn_k12_2022"
default_subjects:
  - "math"
```

## 学科与课程

新增学科：

1. 在 `config/education/subjects.yaml` 添加 `subject_id`。
2. 在 `question_types.yaml`、`skills.yaml`、`mistake_taxonomy.yaml`、`expression_capabilities.yaml` 中按需声明该学科可用项。
3. 如当前要支持课程范围，在 `config/curriculum/<version>/<subject_id>/grade_<n>.yaml` 添加课程骨架。

新增课程文件：

- `subject_id` 必须存在于 `subjects.yaml`。
- `grade` 使用数字 1-12。
- `stage_id` 必须匹配该年级所在学段。
- `units` 可以是粗粒度骨架，不要伪造全量精细教材。

新增知识点：

- 在对应课程文件的 `units[].knowledge_points[]` 下添加。
- `knowledge_point_id` 必须全局唯一。
- `question_types` 必须引用 `config/education/question_types.yaml` 中的 canonical code。
- `skills` 必须引用 `config/education/skills.yaml` 中的 `skill_id`。

新增学科错因：

- 在 `config/education/mistake_taxonomy.yaml` 添加 `mistake_tags`。
- 通用错因用 `scope: "general"` 并列出适用学科。
- 学科专属错因用 `scope: "subject_specific"`。
- 原 24 个数学错因 code 继续保留并可用。

## Rule Registry

`src/core/rule_registry.py` 是 v0.1.5 的教学领域模型入口。

新增或增强的接口包括：

- Student：`get_students()`、`get_active_student()`、`get_student(student_id)`、`get_active_student_id()`。
- Subject：`get_subjects()`、`get_subject(subject_id)`、`get_supported_subjects()`。
- Stage / Grade：`get_stages()`、`get_grades()`、`get_stage_for_grade(grade)`、`get_grade_display_name(grade)`。
- Curriculum：`get_curriculum_for()`、`get_curriculum_for_student()`、`get_units_for_student()`、`get_knowledge_points_for_student()`。
- Education：`get_question_types_for_subject()`、`get_mistake_tags_for_subject()`、`get_skills_for_subject()`、`get_expression_capabilities_for_subject()`。
- Prompt：`render_student_profile_for_prompt()`、`render_curriculum_scope_for_prompt()`、`render_question_types_for_prompt()`、`render_mistake_tags_for_prompt()`、`render_expression_capabilities_for_prompt()`。
- Validation：`validate_education_config()`、`validate_curriculum_config()`、`validate_student_config()`。

旧接口如 `get_question_type_codes()`、`get_knowledge_point_codes()`、`get_mistake_tag_codes()` 继续可用。为兼容旧 worksheet，中文题型名如“递等式计算”“方程”“单位换算”“几何计算”“应用题”仍可通过校验。

## YAML 兼容

旧 `mistakes.yaml` 仍合法：

```yaml
mistakes:
  - date: "2026-05-27"
    question_type: "应用题"
    knowledge_point: "阅读理解型应用题"
    mistake_tag: "R4"
    difficulty: "中等"
    question_summary: "..."
```

v0.1.5 可选字段：

```yaml
student_id: "daughter"
subject_id: "math"
grade_at_time: 6
term_at_time: "六年级上"
curriculum_version_at_time: "cn_k12_2022"
```

缺省策略：

- `student_id` 默认 active student。
- `subject_id` 默认 active student 的第一个 `default_subjects`。
- `grade_at_time` 默认 active student 的 `current_grade`。
- `term_at_time` 默认 active student 的 `current_term`。
- `curriculum_version_at_time` 默认 active student 的 `curriculum_version`。

v0.1.5 不做破坏性数据库重构。上述上下文会在 preview / validation 的内部记录中补齐；数据库 schema hardening 留到 v0.1.6。

## Prompt 范围

生成批改用 Prompt 会注入：

- 当前学生、年级、学期、学段、学科、课程版本。
- 当前学生的当前学科/年级课程范围。
- 当前学科可用 question_types。
- 当前学科可用 mistake_tags。
- 当前学科 expression_capabilities。
- 最近 confirmed 错因统计。

生成出题用 Prompt 会强调：

- 根据当前学生、当前学科、当前年级课程范围出题。
- 不默认跨年级，除非用户明确要求复习或预习。
- 不默认跨学科。
- 当前 v0.1.5 不输出 visuals / diagram / formula blocks。
- 文字类题目必须保持 `worksheet.yaml` 可导入。

## 数据治理

v0.1.4 的能力继续保留：

- YAML parse / business validation / repair prompt。
- dry-run / preview 后再确认写库。
- exact duplicate guard。
- backup/export。
- UAT / sample / invalid warning。
- 批量确认、撤销、删除。

v0.1.5 不清空 `data/math_tutor.db`，不删除旧表，不做 DROP TABLE。

## 启动与测试

安装依赖：

```bash
pip install -r requirements.txt
```

初始化数据库：

```bash
python -m src.db
```

启动 Streamlit：

```bash
streamlit run src/app.py
```

运行测试：

```bash
python -m pytest
```

如果本机 `python` 不在 PATH，请使用项目可用解释器运行等价命令。

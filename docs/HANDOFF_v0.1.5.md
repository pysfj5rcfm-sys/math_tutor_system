# HANDOFF v0.1.5

## 项目名称

当前名称：edu_tutor_system

旧名：math_tutor_system

当前版本：v0.1.5

定位：K12 多学生、多年级、多学科个性化教培系统底座。本版本是 Teaching Domain Model，不是渲染层。

## v0.1.5 做了什么

- 将项目说明、README、Streamlit 页面标题升级为 edu_tutor_system，并保留 formerly math_tutor_system 说明。
- 新增 `config/students/daughter.yaml`，使用稳定 `student_id: daughter`，并通过 `legacy_student_ids` 兼容旧 `daughter_grade5`。
- 新增 `config/education/`：
  - `subjects.yaml`
  - `stages.yaml`
  - `grades.yaml`
  - `question_types.yaml`
  - `skills.yaml`
  - `mistake_taxonomy.yaml`
  - `expression_capabilities.yaml`
- 新增 `config/curriculum/cn_k12_2022/` 多学科多年级课程骨架：
  - math grade 5-12
  - physics grade 8-12
  - chemistry grade 9-12
- 扩展 Rule Registry，支持 student / subject / grade / curriculum filtering。
- 批改 Prompt 和出题 Prompt 注入当前学生、学科、年级、学段、学期、课程版本和课程范围。
- YAML 校验兼容旧 `mistakes.yaml` / `worksheet.yaml`，并补齐可选上下文字段。
- 保留 v0.1.4 dry-run / duplicate guard / backup / export / sample warning 能力。

## v0.1.5.1 Hotfix Note

v0.1.5.1 修复了 Streamlit 启动时的 ImportError。

`src/core/import_preview.py` 依赖 `src.core.mistakes` 中的 public compatibility functions：

- `preview_mistakes_payload`
- `confirm_mistakes_import`

这些函数用于保持 v0.1.4 的 dry-run / preview / confirm import 工作流，不应在后续重构中删除。

新增测试：

- `tests/test_v0151_hotfix_import_preview_compat.py`

后续 v0.1.6 做 schema cleanup 时，必须保留或显式迁移这些 public import paths，并保证：

- `import src.app` 成功；
- `import src.core.import_preview` 成功；
- mistakes preview 不写库；
- confirm import 才写库；
- duplicate guard 不失效。

## v0.1.5.2 Hotfix Note

v0.1.5.2 修复了多学生、多学科上下文在 UI 和校验中的两个轻量回归点。

错题记录列表和“数据管理 / 备份 / 导出 / 重复检测”页面现在会显示：

- `student_id`
- `subject_id`
- `grade_at_time`
- `term_at_time`

当前数据库 schema 仍主要是 v0.1.4 结构。如果 `mistakes` 表暂时没有 `subject_id`、`grade_at_time`、`term_at_time`、`curriculum_version_at_time`，页面和导出会使用 active student 默认上下文补齐显示，不会崩溃。v0.1.6 仍需做 schema cleanup/hardening，把这些上下文字段正式落库或迁移到稳定关联结构。

`knowledge_point` 校验现在支持当前课程范围内的精确匹配：

- canonical `knowledge_point_id`
- 当前 `subject_id + grade_at_time + curriculum_version_at_time` scope 内的 `knowledge_point.name`
- 当前 scope 内 alias 指向的合法值

示例：当 context 为 `subject_id: physics`、`grade_at_time: 8`、`curriculum_version_at_time: cn_k12_2022`，且课程文件存在 `knowledge_point_id: physics_g8_speed`、`name: 速度` 时，`knowledge_point: 速度` 不再触发 `unknown_knowledge_point` warning。

此匹配是精确匹配，不做模糊匹配，不跨学科匹配。如果多个知识点同名，应返回 warning，提示歧义。

新增测试：

- `tests/test_v0152_context_and_knowledge_point_hotfix.py`

后续 v0.1.6 做 schema cleanup 时，仍必须保留或显式迁移：

- `preview_mistakes_payload`
- `confirm_mistakes_import`
- `preview_worksheet_payload`
- `confirm_worksheet_import`

## v0.1.5 没做什么

- 没有接 OpenAI API。
- 没有做 OCR。
- 没有做 PDF。
- 没有做数学几何 SVG 渲染。
- 没有做物理公式或图示渲染。
- 没有做化学式、化学方程式或结构式渲染。
- 没有做服务端、云同步、SaaS 多租户权限。
- 没有做破坏性数据库迁移。
- 没有删除用户历史数据。
- 没有伪造全量精细教材内容库。

## 新配置目录结构

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
      math/
        grade_5.yaml ... grade_12.yaml
      physics/
        grade_8.yaml ... grade_12.yaml
      chemistry/
        grade_9.yaml ... grade_12.yaml
```

`config/student_profile.yaml` 仍保留兼容读取，但新开发应优先使用 `config/students/*.yaml`。

## 配置说明

students：

- 每个学生一个 YAML。
- `student_id` 是稳定身份，不应随升年级变化。
- `current_grade` / `current_term` 表示当前状态。
- 当前 active student 是默认学生。
- `daughter.yaml` 中 `legacy_student_ids: ["daughter_grade5"]` 用于兼容旧样例和历史数据。

subjects：

- math / physics / chemistry 为 active 且 supported_now。
- chinese / english / biology / geography / history 已预留，但 `supported_now: false`。

stages / grades：

- grades 使用数字 1-12。
- primary: 1-6。
- junior_high: 7-9。
- senior_high: 10-12。

question_types：

- canonical code 使用英文，如 `math_calculation`、`physics_calculation`、`chem_equation_balancing`。
- 旧中文题型名通过 `name` / `legacy_names` 兼容。
- 旧 worksheet 中的“递等式计算”“方程”“单位换算”“几何计算”“应用题”仍能通过。

skills：

- 表示跨学科能力点，例如题意理解、计算准确性、公式应用、实验分析。
- v0.1.5 先用于 Prompt 和 schema 表达。

mistake taxonomy：

- 原 24 个数学错因 code 全部保留。
- 新增 physics / chemistry 代表性错因：
  - `PHY_F1`
  - `PHY_U1`
  - `PHY_E1`
  - `CHEM_F1`
  - `CHEM_E1`
  - `CHEM_EXP1`
- Prompt 会按当前 subject 过滤相关错因。

expression capabilities：

- `plain_text` implemented=true。
- 数学公式、数学几何图、坐标图像、物理公式、物理图示、化学式、化学方程式、简单结构式均仅声明，implemented=false。
- v0.2 将基于这些能力实现 Subject Rendering Layer。

curriculum：

- `cn_k12_2022` 是当前课程版本。
- 当前只是代表性骨架，不是全量教材目录。
- 每个课程文件有 `subject_id`、`grade`、`stage_id`、`textbook_version`、`units`。
- `knowledge_point_id` 必须全局唯一。
- `question_types` 引用 canonical question type code。
- `skills` 引用 `skill_id`。

## Rule Registry 新接口摘要

入口：`src/core/rule_registry.py`

Student：

- `get_students(active_only=False)`
- `get_active_student()`
- `get_student(student_id)`
- `get_active_student_id()`

Subject：

- `get_subjects(active_only=True)`
- `get_subject(subject_id)`
- `get_supported_subjects()`

Stage / Grade：

- `get_stages()`
- `get_grades()`
- `get_stage_for_grade(grade)`
- `get_grade_display_name(grade)`

Curriculum：

- `get_curriculum_versions()`
- `get_curriculum_for(subject_id, grade, curriculum_version="cn_k12_2022")`
- `get_curriculum_for_student(student_id, subject_id=None)`
- `get_units_for_student(student_id, subject_id=None)`
- `get_knowledge_points_for_student(student_id, subject_id=None)`
- `get_knowledge_points_for_subject_grade(subject_id, grade)`

Education：

- `get_question_types_for_subject(subject_id)`
- `get_mistake_tags_for_subject(subject_id)`
- `get_skills_for_subject(subject_id)`
- `get_expression_capabilities_for_subject(subject_id)`

Prompt rendering：

- `render_student_profile_for_prompt(student_id=None)`
- `render_curriculum_scope_for_prompt(student_id, subject_id)`
- `render_question_types_for_prompt(subject_id=None)`
- `render_mistake_tags_for_prompt(subject_id=None)`
- `render_expression_capabilities_for_prompt(subject_id=None)`

Validation：

- `validate_education_config()`
- `validate_curriculum_config()`
- `validate_student_config()`

旧接口：

- `get_question_type_codes()`
- `get_knowledge_point_codes()`
- `get_difficulty_codes()`
- `get_mistake_tag_codes()`
- `render_worksheet_policies_for_prompt()`

这些仍保留。

## Prompt Scope Filtering

批改 Prompt：

- 使用 active student。
- 注入当前年级、学期、学段、学科、课程版本。
- 注入当前课程范围。
- 只展示当前 subject 的 question_types / mistake_tags / expression_capabilities。
- 明确 v0.1.5 不要求输出 diagram / visuals。

出题 Prompt：

- 根据当前学生、当前学科、当前年级课程范围出题。
- 不默认跨年级。
- 不默认跨学科。
- 不输出 visuals / diagram / formula blocks。
- 保持 worksheet.yaml 可导入。

## YAML 兼容策略

`mistakes.yaml` 每条记录可选：

- `student_id`
- `subject_id`
- `grade_at_time`
- `term_at_time`
- `curriculum_version_at_time`

`worksheet.yaml` 的 `worksheet` 下可选同样字段。

缺省策略：

- `student_id` 默认 active student。
- `subject_id` 默认 active student 的第一个 default subject。
- `grade_at_time` 默认 active student.current_grade。
- `term_at_time` 默认 active student.current_term。
- `curriculum_version_at_time` 默认 active student.curriculum_version。

旧样例中显式 `student_id: daughter_grade5` 通过 `legacy_student_ids` 兼容，不要求用户立即修改历史数据。

## 数据库历史包袱

v0.1.5 没有做完整 schema cleanup。数据库仍主要是 v0.1.4 结构：

- `mistakes` 表没有 subject_id / grade_at_time 等字段。
- `worksheets` 表没有 subject_id / grade_at_time 等字段。
- context 会在 preview / validation 内部记录补齐，但不会做破坏性写库。
- `mistake_tags` seed 会同步新增的物理/化学错因，不会清空用户数据。

v0.1.6 必须处理 schema hardening。

## v0.1.6 必须做的事情

- Schema cleanup。
- History compatibility cleanup。
- 明确处理 `daughter_grade5` 到 `daughter` 的历史身份兼容策略。
- 为 `mistakes` / `worksheets` / `worksheet_items` 增加非破坏性 subject / grade / curriculum context 字段，或建立上下文关联表。
- Multi-student / multi-grade / multi-subject text exam validation。
- 数学 / 物理 / 化学文字类试卷导入 UAT。
- Data model integrity checks。
- 导出格式纳入 subject / grade / curriculum context。

## v0.2 预留

- Subject Rendering Layer。
- visuals。
- math geometry。
- physics formula / diagram。
- chemical formula / equation。
- render_blocks。

能力声明在 `config/education/expression_capabilities.yaml`。

## 本轮测试结果

开发过程中使用：

```bash
C:\Users\11028\AppData\Local\Programs\Python\Python314\python.exe -m pytest
```

最终结果需以本轮交付报告为准。

## 已知风险

- 数据库 schema 尚未硬化，多学科上下文目前主要存在于 YAML preview / validation 和 Prompt scope 中。
- 课程文件是代表性骨架，不是完整教材库。
- 旧 `config/student_profile.yaml` 与新 `config/students/daughter.yaml` 会并存一个版本周期。
- question_type 同时支持 canonical code 和中文 legacy name，v0.1.6 应进一步明确导入后存储规范。

## 启动命令

```bash
python -m src.db
streamlit run src/app.py
python -m pytest
```

本机若没有裸 `python`，使用：

```bash
C:\Users\11028\AppData\Local\Programs\Python\Python314\python.exe -m pytest
```

## 不应提交的文件

- `data/*.db`
- `backups/`
- `outputs/exports/*`
- `outputs/prompts/*`
- `outputs/worksheets/*`
- `outputs/answer_sheets/*`
- `outputs/reviews/*`
- `.pytest_cache/`
- `__pycache__/`

## v0.1.5.2 Hotfix Note

v0.1.5.2 修复了多学科导入上下文丢失的问题：`mistakes.yaml` 中显式传入 `subject_id: "physics"` 时，确认导入后不应再因为旧表缺少上下文字段而在列表、筛选或导出中显示为默认 `math`。

本 hotfix 做了最小非破坏性持久化：

- `src/db.py` 在 `create_tables()` 后通过 `ALTER TABLE ... ADD COLUMN` 兼容补齐 `mistakes` / `worksheets` 的学习上下文字段；
- 新增字段为 `subject_id`、`grade_at_time`、`term_at_time`、`curriculum_version_at_time`；
- `src/core/mistakes.py` 的确认导入会写入这些字段；
- `src/core/worksheets.py` 的确认导入也会写入 worksheet 顶层上下文；
- 错题记录列表、数据管理筛选、CSV/YAML 导出会优先显示数据库中真实保存的上下文。

同时 v0.1.5.2 保留了上一版修复：

- 错题记录列表和数据管理页面显示 `student_id` / `subject_id` / `grade_at_time`；
- `knowledge_point` 支持在当前 `subject_id + grade_at_time + curriculum_version_at_time` 课程范围内通过 `knowledge_point_id` 或中文 `name` 精确匹配；
- 不做模糊匹配，不跨学科匹配；
- 后续不要删除 `preview_mistakes_payload` / `confirm_mistakes_import` 等兼容接口。

v0.1.6 仍需做 schema cleanup / hardening：统一历史字段、迁移策略、跨版本兼容报告、worksheet item 级上下文策略，以及多学生/多学科文字试卷 UAT。

## v0.1.5.3 Hotfix Note

v0.1.5.3 修复了 v0.1.5.2 人工 UAT 中发现的显示层回归：

- `mistakes.yaml` 显式传入 `subject_id: "physics"` / `grade_at_time: 8` 时，preview、confirm import、列表、筛选、CSV/YAML 导出都必须保留真实上下文；
- active student 的默认 `math` / `6` 只用于旧 YAML 缺失上下文时补齐，不得覆盖 YAML 显式值；
- 错题记录列表和数据管理页面的筛选项会从数据库真实 `subject_id` / `grade_at_time` 中取值，因此 `physics` 和 `8` 会出现在筛选列表中；
- 表格新增 `question_type_display` 与 `knowledge_point_display`，采用 display name + code/id 策略，例如 `物理计算 (physics_calculation)`、`速度 (physics_g8_speed)`；
- `knowledge_point_display` 只在当前记录自己的 `subject_id + grade_at_time + curriculum_version_at_time` scope 内精确匹配，不跨学科、不模糊匹配。

实现入口：

- `src/core/display.py`：轻量 UI display helper；
- `src/app.py::_mistake_table_rows()`：为错题列表和数据管理表格补 display 字段；
- `src/app.py::_mistake_filter_controls()`：筛选项读取真实数据库值；
- `tests/test_v0153_context_display_hotfix.py`：覆盖 explicit context 不被覆盖、真实筛选/导出、display name + code、knowledge point scope regression。

v0.1.6 仍需做正式 schema cleanup/hardening。后续重构必须保留或显式迁移 `preview_mistakes_payload` / `confirm_mistakes_import` public import paths，并继续保证 preview 不写库、confirm 才写库、duplicate guard 不失效。

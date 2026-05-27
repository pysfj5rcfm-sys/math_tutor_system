# math_tutor_system v0.1.2

小学五年级数学错因训练与试卷生成系统。本项目是一个本地 MVP：GPT 负责看卷、批改、判断错因、生成 YAML；本地系统负责记录、校验、统计、Prompt 生成和 HTML 排版。

## v0.1.x 边界

- 不接 OpenAI API，不产生 API 费用。
- 不做 OCR、照片识别、自动批改、自动出题。
- 不做 Agent SDK、服务端、多用户、支付、云同步。
- 不做 PDF 和复杂几何 SVG。
- GPT 通过手动复制 `mistakes.yaml` / `worksheet.yaml` 与本地系统协作。
- 本地系统负责保存学生画像、错因标签、导入校验、统计、Prompt 生成、学生卷 HTML、答案页 HTML、周复盘 Markdown。

## Python 版本

- 目标兼容版本：Python 3.11+。
- 当前验证环境：Python 3.14.4 on Windows。
- 建议复测版本：Python 3.11 或 Python 3.12。
- 项目不得隐式依赖 Python 3.14；如发现版本差异，应优先修复到 Python 3.11+ 可运行。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 初始化数据库

```bash
python -m src.db
```

这会创建 `data/math_tutor.db` 并初始化 24 个错因标签。数据库初始化是幂等的：多次运行不会重复插入标签，不会清空用户数据，也不会破坏已有记录。

初始化时也会确保以下输出目录存在：

- `outputs/worksheets`
- `outputs/answer_sheets`
- `outputs/prompts`
- `outputs/reviews`

## 启动 Streamlit

```bash
streamlit run src/app.py
```

请在项目根目录运行该命令，不需要手动设置 `PYTHONPATH`。

## v0.1.2 YAML 错误分层

YAML Parse Error：语法、缩进、列表层级、冒号、Markdown 代码块标记等问题。此时 YAML 尚未解析成 dict/list，不会进入业务校验，不会写库。页面会显示行号、列号、附近文本、中文解释和 GPT YAML 语法修复 Prompt。

Business Validation Error：YAML 能解析，但字段、枚举、必填项不合法，例如非法 `question_type`、非法 `difficulty`、缺 `answer`、空 `question_summary`。页面会显示位置、字段、当前值、建议修复值和 GPT 业务校验修复 Prompt。存在 error 时不会写库。

Policy Warning：可以导入但需要人工确认的问题，例如 unknown `knowledge_point`。warning 记录仍按原机制导入为 `needs_confirmation`，默认统计不纳入，只有家长确认成 `confirmed` 后才进入默认统计。

## 修复 Prompt 使用方式

在 `mistakes.yaml 导入与校验` 或 `worksheet.yaml 导入与校验` 页面：

1. 粘贴 GPT 输出的 YAML。
2. 点击校验并导入。
3. 如果出现 YAML Parse Error，复制“GPT YAML 语法修复 Prompt”给 GPT。
4. 如果出现 Business Validation Error，复制“GPT 业务校验修复 Prompt”给 GPT。
5. GPT 修复后，把新的完整 YAML 再粘贴回来校验。

修复 Prompt 会要求 GPT 不重新批改、不重新出题、不输出 Markdown、不输出 ```yaml，只输出完整 YAML。

## mistakes.yaml 标准结构

当前 v0.1.x 只接受 `mistakes` 下直接列表：

```yaml
mistakes:
  - date: "2026-05-27"
    question_type: "应用题"
    knowledge_point: "阅读理解型应用题"
    mistake_tag: "R4"
    difficulty: "中等"
    question_summary: "..."
    wrong_answer_summary: "..."
    correct_answer_summary: "..."
    training_needed: true
    source: "GPT批改"
    note: "..."
```

当前不接受：

```yaml
mistakes:
  student_id: ...
  date: ...
  source: ...
  items:
    - ...
```

## worksheet.yaml 标准结构

```yaml
worksheet:
  title: "五年级数学专项训练"
  date: "2026-05-27"
  student_id: "daughter_grade5"
  sections:
    - name: "一、递等式计算"
      layout: "two_columns"
      questions:
        - question_type: "递等式计算"
          knowledge_point: "小数计算"
          target_mistake_tag: "C3"
          difficulty: "基础"
          question: "..."
          answer: "..."
          explanation: "..."
```

v0.1.2 暂不输出 `diagram`、`diagram_json`、`svg_primitives`，也不要写“如图”但没有图。

## alias_mappings.yaml

`config/alias_mappings.yaml` 用来给可读校验报告提供建议值，例如：

- `解方程 -> 方程`
- `小数混合运算 -> 小数计算`
- `简单 -> 基础`
- `R4 关键词理解弱 -> R4`

v0.1.2 只用 alias 生成 `suggested_value`，不会自动修改 YAML，不会自动写回，也不会改变数据库记录。

## 重复导入策略

v0.1.2 暂允许重复导入 `mistakes.yaml` 和 `worksheet.yaml`。系统不会按 hash、日期或题目摘要自动去重。家长在确认 `needs_confirmation` 记录时需要留意重复记录；正式去重策略留到后续版本。

## UAT 样例说明

`samples/uat_*.yaml` 是测试夹具，不是真实学生数据：

- 不会在 `python -m src.db` 时自动导入。
- 不会在 Streamlit 启动时自动导入。
- 不参与默认统计。
- 不影响常规 GPT 出题 Prompt。
- 不写入真实学生档案，除非用户在页面手动粘贴或选择并导入。

如需测试 UAT 样例，建议使用临时数据库或先备份数据库。

## v0.1 验收流程

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 初始化数据库：

```bash
python -m src.db
```

3. 启动 Streamlit：

```bash
streamlit run src/app.py
```

4. 打开“mistakes.yaml 导入与校验”，导入 `samples/sample_mistakes.yaml`。
5. 打开“错题记录列表”，将导入的 `needs_confirmation` 记录确认为 `confirmed`。
6. 打开“错因统计”，确认默认统计只展示 `confirmed` 数据。
7. 打开“GPT 批改 Prompt 生成”，生成并保存 Prompt 到 `outputs/prompts/`。
8. 打开“GPT 出题 Prompt 生成”，生成并保存 Prompt 到 `outputs/prompts/`。
9. 打开“worksheet.yaml 导入与校验”，导入 `samples/sample_worksheet.yaml`。
10. 打开“学生卷 HTML 导出”，选择 `worksheet_id` 并导出 HTML 到 `outputs/worksheets/`。
11. 打开“答案页 HTML 导出”，选择同一个 `worksheet_id` 并导出 HTML 到 `outputs/answer_sheets/`。
12. 打开“周复盘生成”，生成 `weekly_review.md` 到 `outputs/reviews/`。
13. 运行测试：

```bash
python -m pytest
```

14. 确认 v0.1 不接 API、不产生 API 费用；所有 GPT 协作都通过手动复制 YAML 和 Prompt 完成。

## 后续计划

- v0.1.3：将 `question_types`、`knowledge_points`、`mistake_tags`、`difficulty_levels`、`worksheet_policy` 完整 registry 化。
- v0.2：基础几何 SVG。
- v0.3：PDF、趋势、能力雷达。
- v0.4+：API 半自动、多用户服务端、客户端付费、Agent SDK 候选。

这些方向本轮不实现。

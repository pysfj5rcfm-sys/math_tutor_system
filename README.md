# math_tutor_system v0.1.4

小学五年级数学错因训练与试卷生成系统。本项目是一个本地 MVP：GPT 负责看卷、批改、判断错因、生成 YAML；本地系统负责记录、校验、统计、Prompt 生成、HTML 排版、备份和导出。

## v0.1.4 定位

v0.1.4 的定位是 Workflow UX + Data Governance。

本轮重点：

- 主菜单按真实家长使用流程重排。
- 页面名改为“生成批改用 Prompt”和“生成出题用 Prompt”。
- “错因标签库”合并进“规则库查看”。
- `mistakes.yaml` 和 `worksheet.yaml` 导入前先 dry-run / preview，再确认写库。
- 导入前做 exact duplicate 检测，用户可跳过重复或仍然导入。
- 支持错题记录筛选、批量确认、批量撤销、批量删除。
- 支持一键备份 SQLite。
- 支持导出 mistakes CSV、mistakes YAML、worksheets YAML。
- UAT / sample / invalid 数据导入时给出醒目提示。

v0.1.4 仍不接真实 API，仍不做 OCR，仍不做自动批改，仍不做几何 SVG / diagram schema，仍不做 PDF。

## v0.1.x 边界

- 不接 OpenAI API，不产生 API 费用。
- 不做 OCR、照片识别、自动批改、自动出题。
- 不做 Agent SDK、服务端、多用户、支付、云同步。
- 不做 PDF 和复杂几何 SVG。
- GPT 通过手动复制 `mistakes.yaml` / `worksheet.yaml` 与本地系统协作。
- 本地系统负责保存学生画像、规则库、导入校验、重复检测、统计、Prompt 生成、HTML 导出、周复盘、备份和导出。

## 主菜单顺序

一、开始与规则

1. 首页 / 使用说明
2. 学生画像查看
3. 规则库查看
4. 出卷质量验收清单

二、批改与错因入库

5. 生成批改用 Prompt
6. mistakes.yaml 导入与校验
7. 错题记录列表
8. 错因统计

三、出题与试卷导入

9. 生成出题用 Prompt
10. worksheet.yaml 导入与校验

四、打印与复盘

11. 学生卷 HTML 导出
12. 答案页 HTML 导出
13. 周复盘生成

五、数据管理

14. 数据管理 / 备份 / 导出 / 重复检测

六、系统说明

15. 系统扩展预留说明

## 规则库查看

v0.1.3 引入 Rule Registry；v0.1.4 起，错因标签统一在“规则库查看”中查看，不再作为主菜单独立入口。

“规则库查看”展示：

- `question_types`
- `knowledge_points`
- `difficulty_levels`
- `mistake_tags`
- `alias_mappings`
- `worksheet_policies`
- registry 加载状态
- 配置校验结果
- registry 与数据库 `mistake_tags` 数量对比

`config/*.yaml` 是规则事实源，数据库 `mistake_tags` 表是落地副本。`python -m src.db` 会 seed / sync 标签，不会清空用户数据。

## mistakes.yaml 导入流程

v0.1.4 起，导入流程是：

```text
粘贴 YAML
↓
safe_parse_yaml
↓
business validation
↓
duplicate detection
↓
导入预览
↓
用户确认
↓
真正写库
```

规则：

- parse fail 不写库。
- business validation error 不写库。
- warning-only 可以进入预览。
- 用户未点击“确认导入”前不写库。
- 默认策略是只导入非重复记录。
- 用户也可以选择仍然导入全部。

mistake exact duplicate hash 使用稳定字段：

- `student_id`，缺省为 `daughter_grade5`
- `date`
- `question_type`
- `knowledge_point`
- `mistake_tag`
- `difficulty`
- `question_summary`
- `wrong_answer_summary`
- `correct_answer_summary`

hash 对字段顺序不敏感，并会做基础空白 normalize。

## worksheet.yaml 导入流程

worksheet 导入同样先 dry-run / preview，再确认写库。

规则：

- parse fail 不写库。
- business validation error 不写库。
- warning-only 可以进入预览。
- 检测到重复 worksheet 时，默认跳过导入。
- 只有用户明确选择“仍然导入”时，才生成新的 `worksheet_id`。

worksheet hash 基于题卷标题、日期、学生、section 名称、题目、答案、解析、题型、知识点、目标错因和难度等持久化内容计算，不改变原有 `worksheets` / `worksheet_items` 表结构。

## 数据管理

“数据管理 / 备份 / 导出 / 重复检测”页面包含：

- 数据概览：mistakes 总数、needs_confirmation、confirmed、worksheets、worksheet_items、最近导入、最近备份。
- 筛选错因记录：支持 `status`、`source`、date range、`mistake_tag`、`question_type`、`knowledge_point`、`difficulty`。
- 批量操作：批量确认、批量撤销、批量删除。
- 重复检测：扫描重复 mistakes 和重复 worksheets，只展示，不自动删除。
- 数据备份：一键备份 `data/math_tutor.db` 到 `backups/`。
- 数据导出：导出到 `outputs/exports/`。

批量删除必须二次确认，并会提示建议先备份数据库。

## 备份与导出

备份文件：

```text
backups/math_tutor_YYYYMMDD_HHMMSS.db
```

导出文件：

```text
outputs/exports/mistakes_YYYYMMDD_HHMMSS.csv
outputs/exports/mistakes_YYYYMMDD_HHMMSS.yaml
outputs/exports/worksheets_YYYYMMDD_HHMMSS.yaml
```

CSV 使用 `utf-8-sig`，方便 Windows Excel 打开中文。YAML 使用 `allow_unicode=True`。

`backups/` 和 `outputs/exports/*` 是本地运行产物，不应提交到 git；仓库只保留 `outputs/exports/.gitkeep`。

## UAT / sample 数据边界

当文件名包含 `uat_`、`sample_`、`invalid_`，或 `source` 字段包含 UAT / sample / 测试时，页面会提示：

```text
这是测试 / 样例数据，不建议导入正式学习库。
如果只是验收功能，请使用临时数据库或先备份数据库。
```

该提示不强制阻止导入，用户仍可手动确认。系统不会自动导入 UAT 数据，也不会把 UAT 样例作为默认统计数据；只有用户主动确认导入后，才会进入本地库。

## YAML 错误分层

YAML Parse Error：语法、缩进、列表层级、冒号、Markdown 代码块标记等问题。此时 YAML 尚未解析成 dict/list，不会进入业务校验，不会写库。页面会显示行号、列号、附近文本、中文解释和 GPT YAML 语法修复 Prompt。

Business Validation Error：YAML 能解析，但字段、枚举、必填项不合法，例如非法 `question_type`、非法 `difficulty`、缺 `answer`、空 `question_summary`。页面会显示位置、字段、当前值、建议修复值和 GPT 业务校验修复 Prompt。存在 error 时不会写库。

Policy Warning：可以导入但需要人工确认的问题，例如 unknown `knowledge_point`。warning 记录仍按原机制导入为 `needs_confirmation`，默认统计不纳入，只有家长确认成 `confirmed` 后才进入默认统计。

## 标准 YAML 结构

`mistakes.yaml`：

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

`worksheet.yaml`：

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

v0.1.4 仍不输出 `diagram`、`diagram_json`、`svg_primitives`，也不要写“如图”但没有图。

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

## 后续计划

- v0.2：基础几何 SVG。
- v0.3：PDF、趋势、能力雷达。
- v0.4+：API 半自动、多用户服务端、客户端付费、Agent SDK 候选。

这些方向本轮不实现。

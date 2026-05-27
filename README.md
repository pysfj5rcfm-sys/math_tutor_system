# math_tutor_system v0.1

小学五年级数学错因训练与试卷生成系统。本项目是一个本地 MVP：GPT 负责看卷、批改、判断错因、生成 YAML；本地系统负责记录、校验、统计、Prompt 生成和 HTML 排版。

## v0.1 边界

- 不接 OpenAI API，不产生 API 费用。
- 不做 OCR、照片识别、自动批改、自动出题。
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

这会创建 `data/math_tutor.db` 并初始化 24 个错因标签。

数据库初始化是幂等的：多次运行不会重复插入 24 个错因标签，不会清空用户数据，也不会破坏已有记录。初始化时也会确保以下输出目录存在：

- `outputs/worksheets`
- `outputs/answer_sheets`
- `outputs/prompts`
- `outputs/reviews`

## 启动 Streamlit

```bash
streamlit run src/app.py
```

请在项目根目录运行该命令，不需要手动设置 `PYTHONPATH`。

## 重复导入策略

v0.1.1 暂允许重复导入 `mistakes.yaml` 和 `worksheet.yaml`。系统不会按 hash、日期或题目摘要自动去重。家长在确认 `needs_confirmation` 记录时需要留意重复记录；正式去重策略留到后续版本。

## v0.1 使用流程

1. 在“学生画像查看”确认 `config/student_profile.yaml`。
2. 在“错因标签库”确认 24 个错因标签已初始化。
3. 将 GPT 生成的错题 YAML 粘贴到“mistakes.yaml 导入与校验”，或直接加载 `samples/sample_mistakes.yaml`。
4. 导入后记录默认是 `needs_confirmation`，需要在“错题记录列表”中点击确认，才会变为 `confirmed`。
5. “错因统计”默认只统计 `confirmed` 记录；可勾选 `include_unconfirmed` 做调试。
6. 在“GPT 出题 Prompt 生成”生成 Prompt，系统会注入学生画像、错因统计、题量限制和 `worksheet.yaml` schema，并落盘到 `outputs/prompts/`。
7. 将 GPT 返回的 `worksheet.yaml` 粘贴到“worksheet.yaml 导入与校验”，或加载 `samples/sample_worksheet.yaml`。
8. 在“学生卷 HTML 导出”和“答案页 HTML 导出”分别生成文件，输出到 `outputs/worksheets/` 和 `outputs/answer_sheets/`。
9. 在“周复盘生成”生成 `weekly_review.md`，输出到 `outputs/reviews/`。

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

## 命令行示例

```bash
python -m src.db
pytest
```

## 后续计划

- v0.2：支持基础几何 SVG 渲染。
- v0.3：支持 PDF 导出、趋势统计、能力雷达图。
- v0.4 之后候选方向：API 半自动、多用户服务端、客户端付费、Agent SDK。

这些方向本轮不实现。

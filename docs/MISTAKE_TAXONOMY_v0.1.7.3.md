# Mistake Taxonomy v0.1.7.3

v0.1.7.3 uses namespaced active mistake tags only.

Old bare tags such as `C3`, `F3`, `R4`, `M2`, `U1`, and `G1` are not active canonical codes and are not seeded into the rebuilt database.

## General Tags

- `GEN_R1` 读题遗漏
- `GEN_R2` 题意理解偏差
- `GEN_R3` 条件提取不完整
- `GEN_R4` 关键词理解弱
- `GEN_M1` 方法选择不当
- `GEN_M2` 多步骤拆解弱
- `GEN_STEP_1` 步骤不规范
- `GEN_EXPR_1` 表达不完整
- `GEN_CHECK_1` 缺少检验

## Math Tags

- `MATH_C1` 计算抄写错误
- `MATH_C2` 运算顺序错误
- `MATH_C3` 小数点 / 位数错误
- `MATH_C4` 分数处理错误
- `MATH_F1` 等量关系错误
- `MATH_F2` 解方程步骤错误
- `MATH_F3` 方程格式不规范
- `MATH_U1` 单位换算错误
- `MATH_G1` 几何图形 / 公式错误
- `MATH_K1` 概念混淆
- `MATH_K2` 知识点迁移失败
- `MATH_K3` 公式不会应用
- `MATH_MODEL_1` 等量关系找不到
- `MATH_CHECK_1` 未检验答案
- `MATH_EXPR_1` 过程表达不完整

## Chinese Tags

- `CHN_SUM_1` 概括空泛
- `CHN_EVD_1` 文本证据不足
- `CHN_Q_1` 审题偏移
- `CHN_STRUCT_1` 答题结构不规范
- `CHN_POE_1` 古诗文词义不稳
- `CHN_COMP_1` 作文结构松
- `CHN_COMP_2` 作文细节不足
- `CHN_LANG_1` 语言表达不准确

## English Tags

- `ENG_VOC_1` 词汇回忆不稳
- `ENG_CHUNK_1` 搭配错误
- `ENG_GRAM_1` 时态错误
- `ENG_GRAM_2` 主谓一致错误
- `ENG_GRAM_3` 介词 / 冠词错误
- `ENG_READ_1` 阅读定位不准
- `ENG_READ_2` 推断过度
- `ENG_LISTEN_1` 听写音形不连通
- `ENG_WRITE_1` 句式单一
- `ENG_WRITE_2` 语法影响写作
- `ENG_SPEAK_1` 复述不完整

## Physics And Chemistry

Physics and chemistry text-only tags are retained as namespaced tags for registry continuity, but v0.1.7.3 active worksheet UAT focuses on Grade 6 math, Chinese, and English.


# edu_tutor_system 数学 Mistake Tag Taxonomy 深度研究

## 核心结论

这份提示词的大方向是对的，关键点也抓到了：**稳定的数学错因标签不能按知识点、题型、学校训练台阶或单题生长**，否则统计价值和出题价值都会迅速坍缩。更合理的做法，是让 `knowledge_point_id` 承担“内容定位”，让 `mistake_tag_code` 承担“错误机制定位”，两者相乘形成训练矩阵。之所以这样设计，不是拍脑袋，而是因为课程标准和高质量教学研究长期都在区分概念理解、程序与规则、数学语言、表征、数量关系、模型建构、单位与度量、几何空间、数据读取、检验与估算等不同维度；这些维度跨题、跨单元、跨年级反复出现，天然就更适合做稳定标签，而不是跟着章节命名。教育部 2022 版义务教育课程标准已正式印发实施；数学课程核心素养里也明确强调数感、量感、符号意识、运算能力、推理意识、模型意识和应用意识。IES 的数学实践指南则把“系统化理解数学思想”“数学语言”“视觉表征”“数轴与分数”分别作为独立的教学抓手。citeturn5view0turn6search0turn18view0turn18view1turn18view4

我建议第一版 active taxonomy 采用 **28 个标签**。这个规模足够覆盖你提示词里要求的六年级上核心范围，也足够向七到九年级延展，但还没有膨胀到失控。最关键的拆分，不是“分数再多拆一个”“有理数再多拆一个”，而是把最容易被混成一团的几类错误硬拆开：**概念定义、规则应用、运算执行、符号记号、审题漏读、表征转化、数量关系提取、模型构造、方法/公式选择、单位与量义、过程表达、检验估算**。这几个边界如果不立住，后面统计一定会重新退化成“粗心”“不会”“应用题错”这类废标签。citeturn0search1turn14view0turn12view4turn23view3

还有两点我明确建议你改。第一，**建议把 `sign_symbol` 单独升格为一级 category**。负数、去括号、变号、等号、变量替代、括号合法性，这些问题在研究里并不是普通的“规则应用小尾巴”，而是独立、高频、强迁移的失误源；负数学习中的符号障碍、记号语法问题、等号的关系性理解，都会持续影响整数、代数、方程和比例。第二，**建议把 `MATH_EQUALITY_RELATION_ERROR` 独立出来**，不要粗暴并入概念错误。等号被理解成“答案将出现”而不是“两边等值”，会直接伤到方程概念、等式变形和比例式理解；这类问题的训练方式也和普通概念缺失不同。citeturn13view5turn12view10turn15search3turn15search7

下面这份 YAML 是一套**no-legacy、可统计、可出题、可人工 review 的草案**。我没有在这次对话里拿到可检索的项目文件或 live registry，因此其中关于 `no_legacy`、`MATH_`/`GEN_` 命名规则、`allowed_secondary`、`primary_priority` 等，都是按你给定的系统约束来设计的，**不是声称项目已经采用了这些 code**。这点必须说清。外部研究能告诉你的，是“哪些错误机制值得独立追踪”；真正的 active config 仍需要你的人审和系统落地。对这一点，数学教育研究本身也没有提供一套全球通用的惟一标签标准；现有研究更多是围绕具体错误机制、具体内容域和具体诊断框架展开。citeturn0search7turn13view2

## 研究依据与边界

你这份 taxonomy 要服务的不是“讲义目录”，而是**批改—确诊—统计—target matrix—再出题**这条生产链。因此，标签的标准不是“命名得像教材”，而是它是否满足三个条件：**能重复命中、能指导训练、能稳定统计**。从这个标准看，按章节命名的错因几乎都该被否掉。例如，整数研究中的问题并不只表现为“有理数异号加法错”，而更常回收到符号意义、先决概念不足、规则机械套用和表征不稳；分数研究则反复出现前置概念缺口、概念—程序脱节和规则误套；比例研究里又持续出现把 ratio 和 fraction/division 混同、把加性比较和乘性比较混同的问题。也就是说，**内容不同，机制未必不同**。citeturn13view3turn23view0turn13view4turn13view6

与此同时，**审题、阅读、模型和计算绝不能揉成一标签**。关于文字题，较强证据已经表明，表现不只是“会不会算”决定的，文本理解与算术能力都会显著影响结果；更高难度的题目往往要求两者同时在线。Newman 型错误分析也长期把阅读、理解、转化、过程技能和结果编码分开看，因为这些环节对应的干预方式根本不同。再往前一步，针对小学生建模的研究也发现，错误高发点集中在错误关系、遗漏关键信息、结构与关系判断失败，以及图示不正确，而不是一个笼统的“应用题不会”。这正是为什么我把 `GEN_READING_KEYWORD_MISUNDERSTANDING`、`GEN_CONDITION_OMISSION`、`MATH_QUANTITATIVE_RELATION_ERROR`、`MATH_MODEL_CONSTRUCTION_ERROR` 和 `MATH_CALCULATION_EXECUTION_ERROR` 严格拆开。citeturn12view4turn13view2turn13view0turn14view0

我还保留了**单位与度量、几何与空间、数据与图表读取**三个看似“内容味”较重、但其实很值得独立保留的 category。原因很硬：单位理解是度量学习的地基，研究反复指出 identical units、iteration、unit meaning 之类的理解是测量任务能否站稳的前提；几何里空间能力又不是花活，而是实际影响图形理解和立体任务处理的关键能力；数据展示与图表阅读则直接属于统计素养的一部分，图表错并不等于审题错，很多时候是刻度、轴、表头或数据—结论映射读错。citeturn19search0turn19search9turn12view8turn23view2turn20search1

最后，**过程表达、数学语言、检验估算**不能被轻视为“形式问题”。IES 的指南把数学语言单独写成一条 recommendation，不是偶然；小学数学书写研究也发现，缺少术语/短语、符号误用、写法不合法等问题会真实干扰数学交流和判分。另一方面，number sense 研究把理解数、理解运算、形成合理估计视为一个基本整体；如果学生对范围、量级和合理性没有感觉，许多“计算错”其实只是更深层的数感错。citeturn18view1turn12view9turn11search11turn23view3

## 设计判断

我对你原始分类体系做了一个实质性修正：在保留 `concept_definition`、`rule_application`、`calculation_execution`、`condition_judgement`、`representation_transfer`、`modeling_relation`、`method_formula_selection`、`unit_measurement`、`geometry_spatial`、`data_graph_reading`、`process_expression`、`checking_estimation`、`reading_comprehension` 的同时，**新增 `sign_symbol`**。这不是为了“多一个分类更整齐”，而是因为负数学习、记号语法、等号关系理解、代入括号、变号与去括号这些问题，在证据上和普通规则误用并不等价。研究里既能看到负号理解障碍，也能看到数学记号语法问题，还能看到等号关系理解直接关联到后续代数胜任力。把它们硬并回 `rule_application`，会让六年级到预初过渡阶段最有训练价值的一类错误被冲掉。citeturn13view5turn12view10turn15search3turn15search7

我也刻意让一些 tag 保持“丑陋但有用”的边界。比如，`MATH_QUANTITATIVE_RELATION_ERROR` 不是 `MATH_MODEL_CONSTRUCTION_ERROR`。前者问的是“关系有没有看见”，后者问的是“看见以后有没有搭对模型”。同理，`MATH_RULE_APPLICATION_ERROR` 也不是 `MATH_ALGORITHM_PROCEDURE_ERROR`：前者更像法则或性质用错，后者更像程序路径或顺序错乱。再比如，`MATH_UNIT_MEANING_ERROR` 不能和 `MATH_UNIT_CONVERSION_ERROR` 混成一个标签，因为“单位是什么量”与“单位怎么换”是两种失败。很多学生不是不会换算，而是根本不知道自己在换什么。citeturn19search0turn19search9turn13view4turn23view0

另一个关键判断是：**允许 secondary tag，但默认统计与下一轮出题只吃 primary tag**。因为真实错题常常同时包含阅读、建模、执行三层问题；如果你禁止 secondary，很多题会被过度扁平化。如果你把 secondary 也一股脑拿去统计与出题，系统又会重新稀释焦点。所以更合理的制度是：批改时允许记录 secondary；统计、target matrix 和专项训练默认只用 primary；只有在复盘或人工审阅阶段才看 secondary。这个做法与 IES 等指南强调的“先把核心困难点稳定命中”是一致的，也更符合干预先抓主因的逻辑。citeturn18view0turn17view0

## 建议 taxonomy YAML

```yaml
taxonomy:
  metadata:
    subject_id: "math"
    taxonomy_name: "math_mistake_tag_taxonomy"
    version: "draft_v0.1"
    scope: "数学学科通用错因机制，优先覆盖沪教版六年级上"
    registry_mode: "no_legacy"
    note: "本研究中的错因轴不是坐标系 Y 轴，不研究纵坐标。"

  categories:
    - code: "concept_definition"
      name: "概念与定义"
      definition: "对象、定义、意义或本质关系理解错误。"

    - code: "rule_application"
      name: "规则应用"
      definition: "性质、法则、算法规则或变形规则使用错误。"

    - code: "calculation_execution"
      name: "运算执行"
      definition: "思路基本对，但在具体运算执行中出错。"

    - code: "sign_symbol"
      name: "符号与记号"
      definition: "正负号、等号、括号、字母、运算符号、数学记号语法处理错误。"

    - code: "condition_judgement"
      name: "条件判断"
      definition: "分类、边界、前提、比较或判定步骤错误。"

    - code: "representation_transfer"
      name: "表征转化"
      definition: "文字、数轴、图示、表格、式子之间转换失败。"

    - code: "modeling_relation"
      name: "建模与数量关系"
      definition: "数量关系提取、等量关系搭建或模型构造错误。"

    - code: "method_formula_selection"
      name: "方法与公式选择"
      definition: "方法、公式、策略或多步骤拆解路径选择错误。"

    - code: "unit_measurement"
      name: "单位与度量"
      definition: "单位、量义、量纲、换算或单位标注处理错误。"

    - code: "geometry_spatial"
      name: "几何与空间"
      definition: "几何属性、结构关系或空间想象错误。"

    - code: "data_graph_reading"
      name: "数据与图表读取"
      definition: "图表刻度、表头、轴、映射关系或数据读取错误。"

    - code: "process_expression"
      name: "过程与表达"
      definition: "数学语言、推理表达、步骤呈现或答题规范错误。"

    - code: "checking_estimation"
      name: "检验与估算"
      definition: "缺少检验、结果合理性判断、估算或数感支持。"

    - code: "reading_comprehension"
      name: "审题与阅读理解"
      definition: "关键字、条件、限制、题意语义理解错误。"

  mistake_tags:
    - code: "MATH_CONCEPT_DEFINITION_ERROR"
      name: "概念定义错误"
      subject_id: "math"
      category: "concept_definition"
      definition: "对数学对象本身的定义、意义或本质关系理解错误。"
      use_when:
        - "对象本身解释不清，如绝对值、比、比例、相反数、质数等。"
        - "换一个表征或情境后仍不会。"
      do_not_use_when:
        - "概念懂了，只是规则套错。"
        - "只是计算执行失误。"
      typical_knowledge_points:
        - "math_g6a_absolute_value"
        - "math_g6a_ratio_meaning"
        - "math_g6a_equation_meaning_and_equality"
      typical_symptoms:
        - "术语会背但不会解释。"
        - "题型稍变就掉线。"
      next_training_strategy:
        - "要求口头重述定义。"
        - "用例子-反例最小对比。"
        - "先停高负荷题，回到概念可视化。"
      severity: "high"
      active: true
      allowed_secondary: false
      conflict_with:
        - "MATH_RULE_APPLICATION_ERROR"
        - "MATH_CALCULATION_EXECUTION_ERROR"
      primary_priority: 95

    - code: "MATH_PREREQUISITE_CONCEPT_GAP"
      name: "前置概念缺口"
      subject_id: "math"
      category: "concept_definition"
      definition: "当前知识点出错的根因在更早的前置概念未建立。"
      use_when:
        - "回到前置小题仍不会。"
        - "当前题错法可追溯到更早的数感、分数单位、等量关系缺口。"
      do_not_use_when:
        - "只是本节规则用错。"
        - "只是题目没读懂。"
      typical_knowledge_points:
        - "math_g6a_fraction_mul_div"
        - "math_g6a_proportion_property"
        - "math_g6a_one_step_equation_solving"
      typical_symptoms:
        - "新知反复接不上旧知。"
        - "特别依赖机械程序。"
      next_training_strategy:
        - "向前回溯1到2层 prerequisite。"
        - "补前置微任务后再回主知识点。"
        - "做桥接题而不是直接刷当前题。"
      severity: "high"
      active: true
      allowed_secondary: false
      conflict_with:
        - "MATH_CONCEPT_DEFINITION_ERROR"
      primary_priority: 93

    - code: "MATH_RULE_APPLICATION_ERROR"
      name: "规则应用错误"
      subject_id: "math"
      category: "rule_application"
      definition: "法则、性质、判定标准、通用规则或变形规则用错。"
      use_when:
        - "比例性质、约分、通分、质合数判定等规则套错。"
        - "概念基本知道，但落到操作规则上错。"
      do_not_use_when:
        - "规则没错，只是算错。"
        - "对象本身就没理解。"
      typical_knowledge_points:
        - "math_g6a_fraction_comparison"
        - "math_g6a_proportion_property"
        - "math_g6a_prime_composite"
      typical_symptoms:
        - "会背口诀但不知边界。"
        - "规则容易过度泛化。"
      next_training_strategy:
        - "做规则适用/不适用对照题。"
        - "先说规则再下笔。"
        - "加入反例题压掉机械套用。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_CONCEPT_DEFINITION_ERROR"
        - "MATH_CALCULATION_EXECUTION_ERROR"
      primary_priority: 82

    - code: "MATH_ALGORITHM_PROCEDURE_ERROR"
      name: "算法步骤错误"
      subject_id: "math"
      category: "rule_application"
      definition: "所选程序大方向对，但步骤顺序、局部程序或变形路径错乱。"
      use_when:
        - "步骤顺序错误。"
        - "中间步骤缺失导致整个程序不成立。"
      do_not_use_when:
        - "根本选错了方法。"
        - "只是最后一个算术结果出错。"
      typical_knowledge_points:
        - "math_g6a_fraction_add_sub"
        - "math_g6a_fraction_mul_div"
        - "math_g6a_one_step_equation_solving"
      typical_symptoms:
        - "会做局部动作，不会连成链。"
        - "跳步后自己也看不懂。"
      next_training_strategy:
        - "步骤模板短期介入。"
        - "每一步注明依据。"
        - "先慢做再提速。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_METHOD_SELECTION_ERROR"
        - "MATH_CALCULATION_EXECUTION_ERROR"
      primary_priority: 74

    - code: "MATH_CALCULATION_EXECUTION_ERROR"
      name: "运算执行错误"
      subject_id: "math"
      category: "calculation_execution"
      definition: "思路、规则和方法基本正确，但数值执行层面出错。"
      use_when:
        - "符号判断对，但绝对值相减算错。"
        - "通分、约分、代入后的四则算错。"
      do_not_use_when:
        - "规则本身错。"
        - "核心在审题、建模、单位。"
      typical_knowledge_points:
        - "math_g6a_rational_add_different_sign"
        - "math_g6a_fraction_add_sub"
        - "math_g6a_expression_substitution"
      typical_symptoms:
        - "错位、漏算、借位/约分错误。"
        - "订正后很快能改对，但隔天不稳。"
      next_training_strategy:
        - "低负担高频复现。"
        - "拆短计算链。"
        - "隔天同型抽测稳定性。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_RULE_APPLICATION_ERROR"
        - "MATH_CONCEPT_DEFINITION_ERROR"
      primary_priority: 58

    - code: "MATH_SIGN_RULE_ERROR"
      name: "符号规则错误"
      subject_id: "math"
      category: "sign_symbol"
      definition: "正负号、相反数、括号、去括号、变号等符号规则处理错误。"
      use_when:
        - "整数异号加减、减法转加相反数、去括号等场景中错。"
        - "问题核心是变号，不是纯算错。"
      do_not_use_when:
        - "符号正确，只是数值算错。"
        - "本质是概念不懂，如绝对值意义没建立。"
      typical_knowledge_points:
        - "math_g6a_rational_add_different_sign"
        - "math_g6a_integer_subtraction_as_add_opposite"
        - "math_g6a_integer_mixed_add_sub_brackets"
      typical_symptoms:
        - "遇到负号和括号就乱。"
        - "同题内多次变号不一致。"
      next_training_strategy:
        - "先判符号，不立刻算值。"
        - "做正负对照题。"
        - "口头解释每次变号的理由。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_CALCULATION_EXECUTION_ERROR"
        - "MATH_SYMBOL_NOTATION_ERROR"
      primary_priority: 80

    - code: "MATH_SYMBOL_NOTATION_ERROR"
      name: "符号记号错误"
      subject_id: "math"
      category: "sign_symbol"
      definition: "等号、括号、变量、运算符号、数学书写语法使用不当。"
      use_when:
        - "等号连写不合法。"
        - "代入时括号、字母、负号写法出问题并改变数学意义。"
      do_not_use_when:
        - "只是字迹不工整，但意义没变。"
        - "根因在概念或方法。"
      typical_knowledge_points:
        - "math_g6a_expression_substitution"
        - "math_g6a_equation_meaning_and_equality"
        - "math_g6a_fraction_add_sub"
      typical_symptoms:
        - "把等号当箭头。"
        - "括号遗漏。"
      next_training_strategy:
        - "合法/非法写法对照。"
        - "每题单独做‘只查记号’训练。"
        - "建立书写红线清单。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_PROCESS_EXPRESSION_ERROR"
        - "MATH_SIGN_RULE_ERROR"
      primary_priority: 63

    - code: "MATH_EQUALITY_RELATION_ERROR"
      name: "等量关系理解错误"
      subject_id: "math"
      category: "sign_symbol"
      definition: "把等号当成结果标记，而不是两边等值关系。"
      use_when:
        - "不会保持等量关系。"
        - "方程概念和等式变形持续出错。"
      do_not_use_when:
        - "只是某一步变号错。"
        - "只是书写不规范但等量理解没问题。"
      typical_knowledge_points:
        - "math_g6a_equation_meaning_and_equality"
        - "math_g6a_one_step_equation_solving"
        - "math_g6a_proportion_property"
      typical_symptoms:
        - "只盯一边算。"
        - "列式两侧不对应。"
      next_training_strategy:
        - "平衡类任务重建等量观。"
        - "要求解释左右各代表什么。"
        - "先做等式真伪判断再做求解。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_CONCEPT_DEFINITION_ERROR"
        - "MATH_SYMBOL_NOTATION_ERROR"
      primary_priority: 86

    - code: "MATH_CONDITION_JUDGEMENT_ERROR"
      name: "条件判断错误"
      subject_id: "math"
      category: "condition_judgement"
      definition: "需要先比较、分类、判边界或判前提，但学生没判或判错。"
      use_when:
        - "异号相加前未比绝对值。"
        - "质/合数、边界值、特殊值判定错。"
      do_not_use_when:
        - "条件根本没读到，应优先漏读关键条件。"
        - "条件读对了，但模型搭错。"
      typical_knowledge_points:
        - "math_g6a_absolute_value"
        - "math_g6a_prime_composite"
        - "math_g6a_rational_add_different_sign"
      typical_symptoms:
        - "直接算，不先判。"
        - "边界值最容易错。"
      next_training_strategy:
        - "把‘先判断再运算’写进模板。"
        - "专练边界值。"
        - "口头说明判定依据。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_CONDITION_OMISSION"
        - "MATH_RULE_APPLICATION_ERROR"
      primary_priority: 76

    - code: "GEN_CONDITION_OMISSION"
      name: "漏读关键条件"
      subject_id: "general"
      category: "reading_comprehension"
      definition: "题目中的关键限制、数量或条件被漏掉。"
      use_when:
        - "补读条件后，学生能立即改正。"
        - "错因明确是没看到，而不是不会用。"
      do_not_use_when:
        - "条件读到了但不会用。"
        - "核心问题在建模或计算。"
      typical_knowledge_points:
        - "math_g6a_percentage_applications"
        - "math_g6a_measurement_tasks"
        - "math_g6a_word_problem_modeling"
      typical_symptoms:
        - "无盖当有盖。"
        - "至少/至多/剩余被忽略。"
      next_training_strategy:
        - "划线审题模板。"
        - "先复述条件再做题。"
        - "做一字条件变化对照题。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_READING_KEYWORD_MISUNDERSTANDING"
        - "MATH_CONDITION_JUDGEMENT_ERROR"
      primary_priority: 90

    - code: "GEN_READING_KEYWORD_MISUNDERSTANDING"
      name: "审题关键词误解"
      subject_id: "general"
      category: "reading_comprehension"
      definition: "对题目中的关系词、限制词或数量表达语义理解错误。"
      use_when:
        - "增加到/增加了、占/比、剩余/总量等词义读偏。"
        - "错误发生在语言理解阶段。"
      do_not_use_when:
        - "关键词理解无误，但不会建模。"
        - "只是没读到某个数字。"
      typical_knowledge_points:
        - "math_g6a_percentage_applications"
        - "math_g6a_ratio_meaning"
        - "math_g6a_word_problem_modeling"
      typical_symptoms:
        - "一改措辞就全错。"
        - "把自然语言机械映射成某运算。"
      next_training_strategy:
        - "关键词-关系图谱训练。"
        - "同结构不同措辞对照题。"
        - "先用自己的话翻译题目。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_CONDITION_OMISSION"
        - "MATH_QUANTITATIVE_RELATION_ERROR"
      primary_priority: 89

    - code: "MATH_REPRESENTATION_TRANSFER_ERROR"
      name: "表征转化错误"
      subject_id: "math"
      category: "representation_transfer"
      definition: "文字、数轴、图示、表格、算式之间不能稳定互译。"
      use_when:
        - "见图不会列式，见式不会解释图。"
        - "数轴、图示、式子之间转写失败。"
      do_not_use_when:
        - "表征已经建对，问题只在后续运算。"
        - "真正问题是漏读条件。"
      typical_knowledge_points:
        - "math_g6a_number_line_position_and_order"
        - "math_g6a_absolute_value"
        - "math_g6a_expression_substitution"
      typical_symptoms:
        - "一换表示方式就不会。"
        - "不同表征下答案不一致。"
      next_training_strategy:
        - "同一对象做三表征往返。"
        - "先翻译不求解。"
        - "配对任务而不是刷整题。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_MODEL_CONSTRUCTION_ERROR"
      primary_priority: 84

    - code: "MATH_QUANTITATIVE_RELATION_ERROR"
      name: "数量关系提取错误"
      subject_id: "math"
      category: "modeling_relation"
      definition: "相等、差、倍、比、部分-整体、单位率等关系没有识别出来。"
      use_when:
        - "加性比较和乘性比较混淆。"
        - "比、分数、除法、百分率之间关系角色抓错。"
      do_not_use_when:
        - "关系识别对了，但模型没搭好。"
        - "只是没读到条件。"
      typical_knowledge_points:
        - "math_g6a_ratio_meaning"
        - "math_g6a_proportion_property"
        - "math_g6a_percentage_applications"
      typical_symptoms:
        - "关系词一变就失真。"
        - "列式对象不对应。"
      next_training_strategy:
        - "先做关系分类题，不求数值。"
        - "同题只改关系词做最小对比。"
        - "强制标出每个量的角色。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_MODEL_CONSTRUCTION_ERROR"
        - "MATH_METHOD_SELECTION_ERROR"
      primary_priority: 88

    - code: "MATH_MODEL_CONSTRUCTION_ERROR"
      name: "模型构造错误"
      subject_id: "math"
      category: "modeling_relation"
      definition: "从情境到算式、方程、比例式或结构模型的搭建本身错误。"
      use_when:
        - "条形图、方程、比例式、列式结构搭错。"
        - "关系大致看见了，但写不成正确模型。"
      do_not_use_when:
        - "模型正确，只是后面算错。"
        - "核心问题在漏读。"
      typical_knowledge_points:
        - "math_g6a_percentage_applications"
        - "math_g6a_one_step_equation_solving"
        - "math_g6a_proportion_property"
      typical_symptoms:
        - "式子像答案，但不守题意。"
        - "未知量设定混乱。"
      next_training_strategy:
        - "先说清模型每一项代表什么。"
        - "半开放列式训练。"
        - "模型元素必须回指题目文字。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_QUANTITATIVE_RELATION_ERROR"
        - "MATH_METHOD_SELECTION_ERROR"
      primary_priority: 87

    - code: "MATH_METHOD_SELECTION_ERROR"
      name: "方法选择错误"
      subject_id: "math"
      category: "method_formula_selection"
      definition: "在多种可行路径中选了不合适的方法。"
      use_when:
        - "该用比例却硬做差。"
        - "该先设未知量却反复试数。"
      do_not_use_when:
        - "方法选对了，只是执行错误。"
        - "题目本身几乎只有一种直接路径。"
      typical_knowledge_points:
        - "math_g6a_fraction_operations"
        - "math_g6a_proportion_property"
        - "math_g6a_percentage_applications"
      typical_symptoms:
        - "能做但特别绕。"
        - "一变式就崩。"
      next_training_strategy:
        - "同题比较两种方法的负担。"
        - "先选法再作答。"
        - "训练首选法与替代法辨析。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_ALGORITHM_PROCEDURE_ERROR"
        - "MATH_FORMULA_SELECTION_ERROR"
      primary_priority: 72

    - code: "MATH_FORMULA_SELECTION_ERROR"
      name: "公式选择错误"
      subject_id: "math"
      category: "method_formula_selection"
      definition: "选错公式、性质或通用关系式。"
      use_when:
        - "相邻公式或性质混用。"
        - "看到数字就套最近练过的公式。"
      do_not_use_when:
        - "公式选对了，但代入错。"
        - "根因在概念不懂公式含义。"
      typical_knowledge_points:
        - "math_g6a_proportion_property"
        - "math_g6a_percentage_conversion_and_change"
        - "math_g6a_measurement_tasks"
      typical_symptoms:
        - "相近公式互串。"
        - "只记壳，不记量义。"
      next_training_strategy:
        - "做‘选公式不计算’题。"
        - "解释公式中每个量的意义。"
        - "插入误套反例。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_FORMULA_APPLICATION_ERROR"
        - "MATH_METHOD_SELECTION_ERROR"
      primary_priority: 66

    - code: "MATH_FORMULA_APPLICATION_ERROR"
      name: "公式代入错误"
      subject_id: "math"
      category: "method_formula_selection"
      definition: "公式或关系式选对了，但代入位置、对象或量义对错位。"
      use_when:
        - "参数和值对应错误。"
        - "已知量代入位置颠倒。"
      do_not_use_when:
        - "根本选错公式。"
        - "只是代入后四则算错。"
      typical_knowledge_points:
        - "math_g6a_proportion_property"
        - "math_g6a_percentage_applications"
        - "math_g6a_expression_substitution"
      typical_symptoms:
        - "公式写对，代进去就错。"
        - "把已知未知的角色弄反。"
      next_training_strategy:
        - "代入前给字母贴中文义。"
        - "做代入校验题。"
        - "代入后读回一句话。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_FORMULA_SELECTION_ERROR"
        - "MATH_CALCULATION_EXECUTION_ERROR"
      primary_priority: 61

    - code: "MATH_MULTI_STEP_PLANNING_ERROR"
      name: "多步骤拆解错误"
      subject_id: "math"
      category: "method_formula_selection"
      definition: "知道任务不止一步，但不会合理拆步、排序或维持中间目标。"
      use_when:
        - "多步题中途丢目标。"
        - "会局部动作，不会串成主链。"
      do_not_use_when:
        - "题目本身是一部到位。"
        - "根因其实在模型搭错。"
      typical_knowledge_points:
        - "math_g6a_integer_mixed_add_sub_brackets"
        - "math_g6a_percentage_applications"
        - "math_g6a_fraction_word_problems"
      typical_symptoms:
        - "做一步忘一步。"
        - "中间量不知道代表什么。"
      next_training_strategy:
        - "先写步骤计划。"
        - "中间量强制命名。"
        - "用四步清单再逐步撤掉。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_MODEL_CONSTRUCTION_ERROR"
        - "MATH_ALGORITHM_PROCEDURE_ERROR"
      primary_priority: 71

    - code: "MATH_UNIT_MEANING_ERROR"
      name: "单位意义错误"
      subject_id: "math"
      category: "unit_measurement"
      definition: "不理解单位所表示的量、对象或单位份额。"
      use_when:
        - "面积、长度、体积、容积、百分率、单价等量义混淆。"
        - "单位问题不是外壳，而是量本身没懂。"
      do_not_use_when:
        - "量义懂了，只是换算失误。"
        - "只是最后忘了写单位。"
      typical_knowledge_points:
        - "math_g6a_percentage_applications"
        - "math_g6a_measurement_tasks"
        - "math_g6a_unit_rate_tasks"
      typical_symptoms:
        - "数字会算，量说不清。"
        - "面积和长度、容积和体积混用。"
      next_training_strategy:
        - "先问‘1个单位表示什么’。"
        - "数字和单位拆开重读。"
        - "用同数异单位对比题。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_UNIT_CONVERSION_ERROR"
        - "MATH_UNIT_LABEL_ERROR"
      primary_priority: 79

    - code: "MATH_UNIT_CONVERSION_ERROR"
      name: "单位换算错误"
      subject_id: "math"
      category: "unit_measurement"
      definition: "单位间倍数、进率、方向或转换链处理错误。"
      use_when:
        - "长度、面积、体积、百分数互化换算出错。"
        - "进率方向反了。"
      do_not_use_when:
        - "不知道自己在换什么量。"
        - "只是最终没写单位。"
      typical_knowledge_points:
        - "math_g6a_percentage_conversion_and_change"
        - "math_g6a_measurement_tasks"
        - "math_g6a_fraction_decimal_percent_equivalence"
      typical_symptoms:
        - "变大变小方向错。"
        - "平方立方进率按线性处理。"
      next_training_strategy:
        - "先判结果应变大还是变小。"
        - "同一量多单位排序。"
        - "强制写换算桥梁量。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_UNIT_MEANING_ERROR"
        - "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
      primary_priority: 62

    - code: "MATH_UNIT_LABEL_ERROR"
      name: "单位标注错误"
      subject_id: "math"
      category: "unit_measurement"
      definition: "最终答案或关键中间量的单位漏写、写错或与求解对象不匹配。"
      use_when:
        - "数值可能对，但单位错/漏。"
        - "答句中的对象和单位不一致。"
      do_not_use_when:
        - "单位意义本身没懂。"
        - "只是普通答句格式问题。"
      typical_knowledge_points:
        - "math_g6a_percentage_applications"
        - "math_g6a_measurement_tasks"
      typical_symptoms:
        - "只写数字。"
        - "直接照抄题目原单位。"
      next_training_strategy:
        - "末尾固定做‘量+单位+对象’检查。"
        - "无单位答案纠错训练。"
      severity: "low"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_PROCESS_EXPRESSION_ERROR"
      primary_priority: 34

    - code: "MATH_GEOMETRIC_PROPERTY_ERROR"
      name: "几何属性错误"
      subject_id: "math"
      category: "geometry_spatial"
      definition: "对图形属性、构成关系或几何量关系理解错误。"
      use_when:
        - "按外观认图，而不是按属性。"
        - "根据条件选用性质时出错。"
      do_not_use_when:
        - "主要问题是空间想象不足。"
        - "性质对了，只是算错。"
      typical_knowledge_points:
        - "math_g6a_geometry_basics"
        - "math_g6a_measurement_tasks"
        - "math_g6a_nets_and_solids"
      typical_symptoms:
        - "同图异属性分不清。"
        - "无盖/通面/棱面点关系混乱。"
      next_training_strategy:
        - "同性质异图形对照。"
        - "先判性质再求值。"
        - "用操作材料回建属性。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_SPATIAL_VISUALIZATION_ERROR"
        - "MATH_FORMULA_SELECTION_ERROR"
      primary_priority: 77

    - code: "MATH_SPATIAL_VISUALIZATION_ERROR"
      name: "空间想象错误"
      subject_id: "math"
      category: "geometry_spatial"
      definition: "难以在脑中保持、旋转、分层或结构化空间对象。"
      use_when:
        - "展开图、立体、分层计数等任务持续出错。"
        - "错误核心不在公式，而在空间表象。"
      do_not_use_when:
        - "几何性质本身没学懂。"
        - "只是图画得不美观。"
      typical_knowledge_points:
        - "math_g6a_nets_and_solids"
        - "math_g6a_volume_structure"
      typical_symptoms:
        - "平面和立体转化断裂。"
        - "层与列数看不清。"
      next_training_strategy:
        - "实物与图形双通道训练。"
        - "强调分层与单位块结构。"
        - "做旋转前后对应关系任务。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_GEOMETRIC_PROPERTY_ERROR"
        - "MATH_REPRESENTATION_TRANSFER_ERROR"
      primary_priority: 59

    - code: "MATH_DATA_GRAPH_READING_ERROR"
      name: "图表读取错误"
      subject_id: "math"
      category: "data_graph_reading"
      definition: "对图表的刻度、表头、轴、映射关系或读数阶段处理错误。"
      use_when:
        - "读错刻度、对应项、表头或轴。"
        - "错误已经发生在取数阶段。"
      do_not_use_when:
        - "数据读对了，只是结论判断错。"
        - "任务核心不是图表读取。"
      typical_knowledge_points:
        - "math_g6a_data_tables"
        - "math_g6a_bar_graphs"
      typical_symptoms:
        - "读到的数就错。"
        - "忽略间隔和单位。"
      next_training_strategy:
        - "先只读数，不推断。"
        - "做刻度变化型纠错题。"
        - "口头报出图表映射关系。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_READING_KEYWORD_MISUNDERSTANDING"
      primary_priority: 57

    - code: "MATH_PROCESS_EXPRESSION_ERROR"
      name: "过程表达不完整"
      subject_id: "math"
      category: "process_expression"
      definition: "步骤不成链、依据不明、推理过度跳跃，导致不可检查。"
      use_when:
        - "老师无法从过程判断学生是否真的会。"
        - "关键中间量或依据缺失。"
      do_not_use_when:
        - "核心问题是非法记号。"
        - "真正根因是概念、建模或规则错误。"
      typical_knowledge_points:
        - "math_g6a_one_step_equation_solving"
        - "math_g6a_fraction_add_sub"
        - "math_g6a_percentage_applications"
      typical_symptoms:
        - "只写答案。"
        - "过程断裂，订正也难定位。"
      next_training_strategy:
        - "短期完整书写模板。"
        - "关键步必须口头解释。"
        - "订正时标出缺失逻辑桥。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_SYMBOL_NOTATION_ERROR"
      primary_priority: 46

    - code: "MATH_MATHEMATICAL_LANGUAGE_ERROR"
      name: "数学语言使用错误"
      subject_id: "math"
      category: "process_expression"
      definition: "术语、表述或数学叙述用得不准，影响理解或交流。"
      use_when:
        - "相反数、绝对值、倍数、比例等术语混用。"
        - "口头/书面表达误导了数学意义。"
      do_not_use_when:
        - "只是审题关键词理解错。"
        - "只是表达不够优雅但数学意义未失真。"
      typical_knowledge_points:
        - "math_g6a_rational_number_meaning"
        - "math_g6a_ratio_meaning"
        - "math_g6a_equation_meaning_and_equality"
      typical_symptoms:
        - "术语替换随意。"
        - "会认不会说。"
      next_training_strategy:
        - "术语-例子-反例配对。"
        - "要求一句话准确定义。"
        - "把口头解释纳入批改证据。"
      severity: "medium"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_READING_KEYWORD_MISUNDERSTANDING"
        - "MATH_CONCEPT_DEFINITION_ERROR"
      primary_priority: 49

    - code: "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
      name: "估算与数感错误"
      subject_id: "math"
      category: "checking_estimation"
      definition: "缺乏大小、范围、量级和合理性判断，无法用估算支撑解题和检验。"
      use_when:
        - "结果明显离谱但毫无察觉。"
        - "不会用基准数、数轴、常见分率做快速判断。"
      do_not_use_when:
        - "前面根因已明确是计算或规则。"
        - "只是没做最后检查。"
      typical_knowledge_points:
        - "math_g6a_number_line_position_and_order"
        - "math_g6a_fraction_comparison"
        - "math_g6a_percentage_conversion_and_change"
      typical_symptoms:
        - "大小感和位置感断裂。"
        - "量级错也不警觉。"
      next_training_strategy:
        - "先估后算。"
        - "固定加入范围判断题。"
        - "用1/2、1、100%等基准训练。"
      severity: "high"
      active: true
      allowed_secondary: true
      conflict_with:
        - "GEN_CHECKING_OMISSION"
        - "MATH_CALCULATION_EXECUTION_ERROR"
      primary_priority: 65

    - code: "GEN_CHECKING_OMISSION"
      name: "缺少检验"
      subject_id: "general"
      category: "checking_estimation"
      definition: "前面主链大体正确，但未做代回、估算、边界核对或完整性检查。"
      use_when:
        - "若检查一下，大概率就能发现错误。"
        - "主因不在理解，而在监控缺失。"
      do_not_use_when:
        - "前面主因已经是概念、建模、规则或阅读问题。"
        - "学生检查了，但不会判断是否合理。"
      typical_knowledge_points:
        - "math_g6a_one_step_equation_solving"
        - "math_g6a_percentage_applications"
        - "math_g6a_fraction_operations"
      typical_symptoms:
        - "不代回，不估算。"
        - "交卷前不回看。"
      next_training_strategy:
        - "只固定两种检验法。"
        - "把检验写成显式步骤。"
        - "记录‘本可避免’错误。"
      severity: "low"
      active: true
      allowed_secondary: true
      conflict_with:
        - "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
      primary_priority: 18

  primary_selection_rules:
    - priority: 1
      condition: "对象本身意义、定义或等量关系没建立。"
      preferred_category: "concept_definition / sign_symbol"
      examples:
        - "把绝对值当成去负号。"
        - "把等号看成结果标记。"

    - priority: 2
      condition: "题意中的关键字、限制词或条件没有被正确读取。"
      preferred_category: "reading_comprehension"
      examples:
        - "把‘增加到’看成‘增加了’。"
        - "漏掉无盖、剩余、至少。"

    - priority: 3
      condition: "题目读懂了，但数量关系或等量关系没有抽出来。"
      preferred_category: "modeling_relation"
      examples:
        - "把比关系当差关系。"
        - "不会从文字搭出方程或比例式。"

    - priority: 4
      condition: "同一对象在文字、图、数轴、式子之间转写失败。"
      preferred_category: "representation_transfer"
      examples:
        - "数轴能看不会列不等式。"
        - "条形图能看不会列式。"

    - priority: 5
      condition: "概念懂、题意懂，但法则或性质用错。"
      preferred_category: "rule_application"
      examples:
        - "比例性质套错。"
        - "分数比较规则误用。"

    - priority: 6
      condition: "错误集中在正负号、括号、等号、变量、记号。"
      preferred_category: "sign_symbol"
      examples:
        - "减法转加相反数错。"
        - "等号连写改变式义。"

    - priority: 7
      condition: "方法选错或不会拆步，但局部规则未必错。"
      preferred_category: "method_formula_selection"
      examples:
        - "该设未知量却乱猜。"
        - "多步题不会规划顺序。"

    - priority: 8
      condition: "错误首先发生在单位、量义或量纲层面。"
      preferred_category: "unit_measurement"
      examples:
        - "面积和长度混。"
        - "求人数却答百分数。"

    - priority: 9
      condition: "思路和规则正确，但数值执行出错。"
      preferred_category: "calculation_execution"
      examples:
        - "通分方向对，但分子算错。"
        - "代入后四则算错。"

    - priority: 10
      condition: "前面主链正确，问题主要在过程不完整或未检验。"
      preferred_category: "process_expression / checking_estimation"
      examples:
        - "不写关键中间步。"
        - "不代回检验。"

  coverage_matrix_sample:
    - knowledge_point_id: "math_g6a_rational_number_meaning"
      possible_mistake_tags:
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "把负数只当作一个特殊符号，不理解其表示相反方向或低于基准。"
          next_training: "用温度、海拔、收支双向量情境重建意义"
        - code: "MATH_MATHEMATICAL_LANGUAGE_ERROR"
          typical_error: "把正数、负数、相反意义、相反数混说。"
          next_training: "术语-例子-反例配对"
        - code: "MATH_REPRESENTATION_TRANSFER_ERROR"
          typical_error: "会读情境，不会写成带符号数。"
          next_training: "情境↔数值双向翻译"

    - knowledge_point_id: "math_g6a_number_line_position_and_order"
      possible_mistake_tags:
        - code: "MATH_REPRESENTATION_TRANSFER_ERROR"
          typical_error: "知道大小关系，但不会在数轴上定位。"
          next_training: "数值-点位双向标注"
        - code: "MATH_CONDITION_JUDGEMENT_ERROR"
          typical_error: "不先判断与0的相对位置就比较大小规律。"
          next_training: "先判正负再比较距离"
        - code: "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
          typical_error: "点落在明显不合理区间。"
          next_training: "先估所在区间再定点"

    - knowledge_point_id: "math_g6a_absolute_value"
      possible_mistake_tags:
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "把绝对值理解为‘去负号’。"
          next_training: "数轴距离模型重建"
        - code: "MATH_REPRESENTATION_TRANSFER_ERROR"
          typical_error: "会背定义，不会在数轴上解释。"
          next_training: "定义↔数轴↔例子往返"
        - code: "MATH_CONDITION_JUDGEMENT_ERROR"
          typical_error: "比较绝对值时不先看距离。"
          next_training: "只做‘谁离0更远’判定题"

    - knowledge_point_id: "math_g6a_rational_add_different_sign"
      possible_mistake_tags:
        - code: "MATH_SIGN_RULE_ERROR"
          typical_error: "异号相加结果符号判断错误。"
          next_training: "先判符号再算绝对值差"
        - code: "MATH_CONDITION_JUDGEMENT_ERROR"
          typical_error: "未比较绝对值大小就定符号。"
          next_training: "加前置绝对值比较小题"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "符号对了，但绝对值相减算错。"
          next_training: "低负担同型复现"

    - knowledge_point_id: "math_g6a_integer_subtraction_as_add_opposite"
      possible_mistake_tags:
        - code: "MATH_SIGN_RULE_ERROR"
          typical_error: "减法改写为加相反数时变号错误。"
          next_training: "专项做‘改写不求值’"
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "知道要改写，但规则套用不完整。"
          next_training: "原式-改写式配对纠错"
        - code: "MATH_ALGORITHM_PROCEDURE_ERROR"
          typical_error: "改写后括号处理顺序混乱。"
          next_training: "强制保留改写中间步"

    - knowledge_point_id: "math_g6a_integer_mixed_add_sub_brackets"
      possible_mistake_tags:
        - code: "MATH_SIGN_RULE_ERROR"
          typical_error: "去括号时局部变号错。"
          next_training: "同结构正负对照题"
        - code: "MATH_MULTI_STEP_PLANNING_ERROR"
          typical_error: "多步混合运算中途丢主线。"
          next_training: "先写运算计划再算"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "中间链式运算算错。"
          next_training: "缩短单题计算链"

    - knowledge_point_id: "math_g6a_divisibility_factors_multiples"
      possible_mistake_tags:
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "因数和倍数角色颠倒。"
          next_training: "双向问答谁是谁的因数/倍数"
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "整除判定规则用错。"
          next_training: "规则适用/不适用判断题"
        - code: "MATH_MATHEMATICAL_LANGUAGE_ERROR"
          typical_error: "整除、公因数、公倍数混说。"
          next_training: "术语整理卡"

    - knowledge_point_id: "math_g6a_prime_composite"
      possible_mistake_tags:
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "不知道质数的本质是恰有两个正因数。"
          next_training: "定义+反例+边界值1专题"
        - code: "MATH_CONDITION_JUDGEMENT_ERROR"
          typical_error: "不检查1、2这类边界值。"
          next_training: "边界值清单复练"
        - code: "GEN_READING_KEYWORD_MISUNDERSTANDING"
          typical_error: "把‘只有’这类定义词读偏。"
          next_training: "定义语言精读"

    - knowledge_point_id: "math_g6a_fraction_equivalence_and_simplification"
      possible_mistake_tags:
        - code: "MATH_PREREQUISITE_CONCEPT_GAP"
          typical_error: "不知道等值分数关系，约分全靠背。"
          next_training: "从图示和数线回补等值分数"
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "约分、扩分规则机械套错。"
          next_training: "可约/不可约/为什么题组"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "公因数方向对，但算错。"
          next_training: "公因数和约分分开练"

    - knowledge_point_id: "math_g6a_fraction_comparison"
      possible_mistake_tags:
        - code: "MATH_METHOD_SELECTION_ERROR"
          typical_error: "异分母直接看分子或分母。"
          next_training: "选法不计算题组"
        - code: "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
          typical_error: "不会用1/2、1等基准快速判断。"
          next_training: "基准分数速判"
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "通分比较规则混用。"
          next_training: "规则边界对照题"

    - knowledge_point_id: "math_g6a_fraction_add_sub"
      possible_mistake_tags:
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "异分母直接相加减。"
          next_training: "先判是否需通分再算"
        - code: "MATH_ALGORITHM_PROCEDURE_ERROR"
          typical_error: "通分、加减、约分顺序混乱。"
          next_training: "步骤模板+撤架"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "通分后分子分母算错。"
          next_training: "通分链路低负担复现"

    - knowledge_point_id: "math_g6a_fraction_mul_div"
      possible_mistake_tags:
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "分数除法不转化为乘倒数，或转化不完整。"
          next_training: "专项做‘转化不求值’"
        - code: "MATH_PREREQUISITE_CONCEPT_GAP"
          typical_error: "不知道倒数与分数乘法的关系。"
          next_training: "回补倒数与单位分数意义"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "约分位置对，但算错。"
          next_training: "只练约分与乘积短链"

    - knowledge_point_id: "math_g6a_ratio_meaning"
      possible_mistake_tags:
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "把比看成差或把比与分数完全等同。"
          next_training: "比/差/分数/除法最小对比"
        - code: "MATH_QUANTITATIVE_RELATION_ERROR"
          typical_error: "加性比较和乘性比较混淆。"
          next_training: "关系分类题"
        - code: "MATH_MATHEMATICAL_LANGUAGE_ERROR"
          typical_error: "前项、后项、比值术语混乱。"
          next_training: "术语与结构图匹配"

    - knowledge_point_id: "math_g6a_proportion_property"
      possible_mistake_tags:
        - code: "MATH_RULE_APPLICATION_ERROR"
          typical_error: "比例性质左右对象对应错。"
          next_training: "比例式真伪判断+纠错"
        - code: "MATH_EQUALITY_RELATION_ERROR"
          typical_error: "不会把比例看作等值关系。"
          next_training: "先解释两边各代表什么"
        - code: "MATH_FORMULA_APPLICATION_ERROR"
          typical_error: "交叉乘时位置代错。"
          next_training: "字母位置贴义后再运算"

    - knowledge_point_id: "math_g6a_percentage_conversion_and_change"
      possible_mistake_tags:
        - code: "MATH_UNIT_MEANING_ERROR"
          typical_error: "不理解百分数以100为基准的量义。"
          next_training: "‘每百份’可视化训练"
        - code: "MATH_UNIT_CONVERSION_ERROR"
          typical_error: "百分数、小数、分数互化方向错。"
          next_training: "先判变大变小再互化"
        - code: "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
          typical_error: "50%、0.5、1/2大小感断裂。"
          next_training: "常见基准百分率速判"

    - knowledge_point_id: "math_g6a_percentage_applications"
      possible_mistake_tags:
        - code: "GEN_READING_KEYWORD_MISUNDERSTANDING"
          typical_error: "把‘增加到’和‘增加了’混掉。"
          next_training: "关键词对照题"
        - code: "GEN_CONDITION_OMISSION"
          typical_error: "漏掉基准量或限制条件。"
          next_training: "先圈基准量再列式"
        - code: "MATH_QUANTITATIVE_RELATION_ERROR"
          typical_error: "部分量、整体量、对应百分率关系抽错。"
          next_training: "先标三要素再求解"
        - code: "MATH_MODEL_CONSTRUCTION_ERROR"
          typical_error: "列式或方程搭错。"
          next_training: "半开放列式训练"

    - knowledge_point_id: "math_g6a_expression_substitution"
      possible_mistake_tags:
        - code: "MATH_SYMBOL_NOTATION_ERROR"
          typical_error: "代入负数时括号缺失。"
          next_training: "负数代入括号专项"
        - code: "MATH_FORMULA_APPLICATION_ERROR"
          typical_error: "字母和值对应错位。"
          next_training: "先给字母贴中文含义"
        - code: "MATH_CALCULATION_EXECUTION_ERROR"
          typical_error: "代入后化简算错。"
          next_training: "代入和化简拆开练"

    - knowledge_point_id: "math_g6a_equation_meaning_and_equality"
      possible_mistake_tags:
        - code: "MATH_EQUALITY_RELATION_ERROR"
          typical_error: "把等号理解成答案提示，不理解左右等值。"
          next_training: "非标准等式和平衡任务"
        - code: "MATH_CONCEPT_DEFINITION_ERROR"
          typical_error: "不知道方程是含未知数的等式。"
          next_training: "方程/算式/恒等式辨析"
        - code: "MATH_SYMBOL_NOTATION_ERROR"
          typical_error: "等号连写、箭头式写法混入等式。"
          next_training: "合法书写对照纠错"

    - knowledge_point_id: "math_g6a_one_step_equation_solving"
      possible_mistake_tags:
        - code: "MATH_EQUALITY_RELATION_ERROR"
          typical_error: "解方程时只操作一边。"
          next_training: "每步都说‘两边同时…’"
        - code: "MATH_METHOD_SELECTION_ERROR"
          typical_error: "该用逆运算却乱试数。"
          next_training: "逆运算路径模板"
        - code: "MATH_ALGORITHM_PROCEDURE_ERROR"
          typical_error: "步骤顺序不清。"
          next_training: "解-验两段式固定流程"
        - code: "GEN_CHECKING_OMISSION"
          typical_error: "不代回检验。"
          next_training: "每题固定代回一次"

  review_notes:
    tag_count: 28
    tags_added:
      - "MATH_SIGN_RULE_ERROR"
      - "MATH_SYMBOL_NOTATION_ERROR"
      - "MATH_EQUALITY_RELATION_ERROR"
      - "MATH_QUANTITATIVE_RELATION_ERROR"
      - "MATH_MODEL_CONSTRUCTION_ERROR"
      - "MATH_MULTI_STEP_PLANNING_ERROR"
      - "MATH_UNIT_MEANING_ERROR"
      - "MATH_UNIT_CONVERSION_ERROR"
      - "MATH_UNIT_LABEL_ERROR"
      - "MATH_ESTIMATION_NUMBER_SENSE_ERROR"
    tags_merged:
      - "将按知识点分散出现的变号类错误合并到 MATH_SIGN_RULE_ERROR"
      - "将按题型分散出现的列式/方程搭建错误合并到 MATH_MODEL_CONSTRUCTION_ERROR"
      - "将分散的比/百分数/应用题关系抽取失败合并到 MATH_QUANTITATIVE_RELATION_ERROR"
      - "将若干纯收尾失分归并到 GEN_CHECKING_OMISSION 与 MATH_UNIT_LABEL_ERROR"
    tags_deprecated:
      - "不建议 active taxonomy 中保留按知识点命名的专属错因码"
      - "不建议按学校台阶、题组或单题命名错因码"
      - "不建议恢复 legacy 裸码为 active code"
    tags_needing_review:
      - "MATH_PREREQUISITE_CONCEPT_GAP 是否独立，或并回 MATH_CONCEPT_DEFINITION_ERROR"
      - "MATH_UNIT_LABEL_ERROR 是否并回 MATH_PROCESS_EXPRESSION_ERROR"
      - "MATH_SYMBOL_NOTATION_ERROR 与 MATH_PROCESS_EXPRESSION_ERROR 的边界"
      - "MATH_DATA_GRAPH_READING_ERROR 在六上第一版是否直接激活"
    potential_overlaps:
      - "MATH_CONCEPT_DEFINITION_ERROR vs MATH_PREREQUISITE_CONCEPT_GAP"
      - "MATH_RULE_APPLICATION_ERROR vs MATH_ALGORITHM_PROCEDURE_ERROR"
      - "MATH_SIGN_RULE_ERROR vs MATH_SYMBOL_NOTATION_ERROR"
      - "MATH_QUANTITATIVE_RELATION_ERROR vs MATH_MODEL_CONSTRUCTION_ERROR"
      - "MATH_UNIT_MEANING_ERROR vs MATH_UNIT_CONVERSION_ERROR"
    taxonomy_risks:
      - "如果 primary 选择不落实 first-root-cause，统计会漂移"
      - "如果 secondary 没边界，矩阵会重新失焦"
      - "如果 knowledge_point_id 粒度过粗，再好的 taxonomy 也会失真"
      - "如果 Prompt 继续允许‘粗心’泛化，执行类标签会被滥用"
      - "如果不把阅读、建模、执行拆开，应用题诊断几乎没有训练价值"
    edu_system_confirmation_needed:
      - "是否支持 allowed_secondary"
      - "是否支持 conflict_with"
      - "是否支持 primary_priority"
      - "是否支持 secondary_mistake_tag_codes"
      - "是否在 MVP Prompt 中默认只用 primary tag 出题"
      - "是否需要 tag versioning"
      - "是否把 taxonomy metadata 注入 Prompt"
      - "是否允许 typical_knowledge_points 只作为提示而非硬约束"
    old_code_reference_only:
      - "本稿不输出 legacy_mappings，不输出 legacy_merge_suggestions，不把旧裸码纳入 active config。"
      - "如需人工理解旧档案，只能在独立迁移说明中维护旧码释义，不进入 alias_mappings，不进入 Prompt。"
```

## 关键解释与风险

这份草案里最重要的，不是某个名字，而是**几条边界真的被钉死了**。第一，`reading_comprehension → modeling_relation → calculation_execution` 必须是三层，而不是一层。文字题研究已经很清楚：文本理解、算术技能、转化/建模并不是同一个东西，难题尤其要求多种能力同时在线。第二，`sign_symbol` 必须独立，因为负数障碍、等号关系理解和记号语法错误，对预初阶段的伤害远大于普通“计算粗心”。第三，`unit_measurement` 不能只剩“单位换算”，还要保留“单位意义”；研究和课程标准都在强调量感、量义和单位意识，而不是把单位当成结尾装饰。第四，`process_expression` 和 `checking_estimation` 必须留着，但 primary priority 要低于概念、阅读、建模和规则，否则系统会习惯性把深层错误洗成“格式”和“忘检查”。citeturn12view4turn13view2turn13view5turn15search3turn19search0turn19search9turn18view1turn23view3

如果你要把这份 taxonomy 真落到 edu_tutor_system，我的强硬判断是：**第一轮不要再加标签了，反而要守纪律**。你真正该盯的不是“我们是不是少了一个分数类子标签”，而是 GPT 批改是否能稳定区分下面这几类：`MATH_SIGN_RULE_ERROR`、`MATH_EQUALITY_RELATION_ERROR`、`MATH_QUANTITATIVE_RELATION_ERROR`、`MATH_MODEL_CONSTRUCTION_ERROR`、`GEN_CONDITION_OMISSION`、`MATH_UNIT_MEANING_ERROR`、`MATH_PROCESS_EXPRESSION_ERROR`、`MATH_CALCULATION_EXECUTION_ERROR`。这八类一旦分得稳，六年级上到预初适应阶段的大部分高价值训练就有抓手了；分不稳，taxonomy 再漂亮也是空壳。citeturn13view0turn13view4turn13view6turn15search7turn19search0turn12view9
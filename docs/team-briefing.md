# Physics Discovery Gym — Team 共享简报

> 这是 physics-gym-research team 所有成员的共享上下文。开工前请通读。

## 项目背景

用户（物理竞赛背景 + LLM 研究者）正在设计一个**物理 discovery benchmark**，目标是超越 NewtonBench / PhysGym 类基线。

**核心 critique against NewtonBench**：
NewtonBench 让 agent "做实验" 本质是参数扫描 + 函数拟合。真物理学家做实验是：**选工具、设计装置、测信号、构造干预**。NewtonBench 自己也报告："给强模型 code interpreter 反而伤害表现" —— 因为模型直接跳到 `np.polyfit` 而不是像物理学家思考。

**我们的 framework（D1-D7）**：

| ID | 决策 |
|---|---|
| D1 | 大世界 + 任务卡（known 卡 + hidden 卡混合）|
| D2 | Agent 主动 propose anomaly，用预训练物理作参照 |
| D3 | Tool 池 = 测量 + 操控 + 分析 + 知识（带 cost）|
| D4 | Python 沙箱 + JSON schema 双接口 |
| D5 | 跨 scenario 持久化的 tool 创造（Voyager 风格 skill library）|
| D6 | "一次只破一个对称性" 偏移原则，复用 NewtonBench 12 sim |
| D7 | 评测 3 轴（Discovery / Efficiency / Skill）+ 双视图（诊断雷达 + 排名复合分）|

## 已识别的核心 novelty 卖点

1. 第一个把"使用工具"作为一等行为评测的 physics discovery benchmark
2. 第一个支持 agent 跨 scenario 累积 skill library 的物理 benchmark
3. 第一个分开测 anomaly identification 与 anomaly characterization
4. 第一个系统基于"对称性破缺"设计反事实物理偏移

## 关键工作原则

**框架 vs 标定的分离**：现在只对齐框架级结构，具体数值（λ、阈值、tool 列表、shift 强度）属于标定级，等 v1 原型 / 物理调研结束后实验定值。

## 关键 prior art（每人都应知道）

- **NewtonBench** (arxiv 2510.07172, HKUST-KnowComp/NewtonBench, 已开源) — 直接竞争对手
  - 12 个具体定律的 sim（gravity / coulomb / hooke / snell / fourier / 等）
  - Mutation 类型：operator / exponent / constant（全是 β-type，不做结构 γ 或守恒 δ shift）
  - 评测：Symbolic Accuracy + RMSLE
  - Action space：`run_experiment` + 可选 Python，无 tool pool
  - 报告 limitation：噪声敏感、code 反而害强模型、复杂度上升崩溃

- **PhysGym** (arxiv 2507.15550) — controlled priors 物理 discovery
- **BoxingGym** (arxiv 2501.01540) — Goodman 组用 EIG 评 agent 实验设计
- **Gravity-Bench** (arxiv 2501.18411) — 单域引力 discovery
- **Curie** (arxiv 2502.16069) — agent rigor module
- **LLM-SR** (arxiv 2404.18400) — equation discovery via programming
- **Voyager** (Minecraft skill library 启发我们 D5)

## 用户偏好

- **方法论上偏严谨**：要求"框架级 vs 标定级"分离，反对过早承诺细节
- **物理背景强**：他对 γ shift 担心对称性破缺连锁反应（已采纳，纳入 D6）
- **资源画像**：个人 / 小团队，无大算力。不做大模型训练，只做评测 + 小规模实验。
- **写作风格**：直接、追问、不接受"软评测"
- **要求所有论文给标题 + URL**，不接受幻觉论文

## 你（teammate）的工作纪律

- 不编造论文 / URL。若不确定，宁可不放。
- 中文输出。
- 报告需结构化（Markdown headers + bullets）。
- 任务完成后用 SendMessage 通知 team-lead 并 TaskUpdate 标完成。
- 发现重大问题（设计漏洞、scooping risk 等）立即报告 team-lead，不要等任务做完。

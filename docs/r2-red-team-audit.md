# R2 红队审查报告：D1–D7 对抗性审计

> 作者：red-team-critic
> 立场：假设我是一个聪明但不诚实的 agent designer，目标是用最少功夫拿最高分。
> 范围：仅审查 `/Data/tanh/phyLLM/docs/idea-design-notes.md` 中 D1–D7 决策与已对齐的评测原则。
> 输出原则：**不写赞同**。每个 finding 包含 attack 场景 + 分数估计 + 防御建议。

---

## TL;DR — 5 个 Critical Issue（足以让整个 benchmark 失效）

| # | 名称 | 影响面 | 关联决策 | 严重程度 |
|---|---|---|---|---|
| C1 | **"万能 god tool" 跨 scenario 累积攻击** | 摧毁 D5 novelty + tool-use 评测 | D3 / D4 / D5 / D7 | CRITICAL |
| C2 | **Python 沙箱旁路 (off-the-books 分析)** | 摧毁 tool-use 可观测性与 knowledge cost | D3 / D4 | CRITICAL |
| C3 | **对称性 shift 的可枚举性 (catalog memorization)** | 把"发现物理"退化为"模式匹配" | D6 | CRITICAL |
| C4 | **Anomaly proposal 的 brute-force chi-square 攻击** | D2 的"主动发现"沦为统计检测 | D2 |  High→Critical（取决于 cost）|
| C5 | **Hidden card 的 side-channel 探测** | 摧毁 D1 探索性评测 | D1 | High |

> **C1–C3 是结构性问题**：不调标定级数值能解决的，需要修改框架。建议在 v1 设计冻结前先回应这三点。

---

## D1: 大世界 + 任务卡（known + hidden）

### Attack 1.1 — 只刷 known card，完全跳过 hidden card

**场景**: agent 拿到任务卡列表后，直接对 N 张 known card 跑套路化流程，hidden card 完全不找。
**评分估计**: 如果 hidden/known 权重不显式声明，agent 在 known 子集上完美得分 → 可能拿到 60–80% 总分。
**防御**: D1 必须显式约束 **hidden card 在总分中占比下限**（例如 ≥40%），并把"hidden discovery rate"作为独立报告维度。

### Attack 1.2 — Side-channel hidden card 探测（C5, High）

**场景**: hidden card 在 sim 里必然以某种数据结构标记 (异常区域坐标、特殊 RNG seed、不同的微分方程分支)。聪明 agent 不需要"真的探索物理"，只需：
- 调用任何便宜的全局测量工具→对比读数的统计分布异常点
- 或者反复 query sim 状态接口直到泄漏元数据
- 极端情况：用 Python 内省 sim 对象 / 探测 memory layout

**评分估计**: 若 sim 接口未 hardened，"找到 hidden card 位置"可以变成纯 O(N) 扫描，0 物理洞察拿满 discovery rate 的"location 子项"。
**防御**:
- Sim 必须把 hidden card 的"位置元数据"放在 agent 不可见的进程外
- Hidden card discovery 评分必须拆为 **(a) 找到位置 (b) 解释偏移本质**，且 (b) 占主导权重
- 评测必须报告 "find vs explain ratio" 防止只刷 (a)

### Attack 1.3 — 探索覆盖率作弊

**场景**: 若"覆盖率"按访问区域数算，agent 用最廉价 measure 做 N 次远距离 ping，刷覆盖率分。
**防御**: 覆盖率必须按 **information gain 加权**，而不是按访问计数。

---

## D2: Agent 主动 propose_anomaly

### Attack 2.1 — Brute-force chi-square 全场 propose（C4, Critical 取决于 cost）

**场景**: 物理学家"先用标准物理参照→发现偏差→propose anomaly"听起来很美。但 agent 完全可以：

```python
for loc in grid:
    data = cheap_measure(loc)
    pred = textbook_physics(loc)   # 预训练知识直接给
    if chi2(data, pred) > τ:
        propose_anomaly(loc)
```

这**正好就是设计说的工作方式**，但本质上没有"物理判断"——只是阈值检测。  

**评分估计**: 如果 anomaly identification 单独计分（D2 的 ✓/✗ 反馈），agent 在 grid 上 sweep 一遍就拿到几乎满分的 identification rate。注意：**第 3 个 paper 卖点"分开测 identification 与 characterization"** 恰好成为这个 attack 的最大受益人——identification 子项被白送。

**防御**:
- `propose_anomaly` 必须**带有显式成本**（错 propose 扣分，频次受限），且成本足够大让 brute-force grid scan 不优
- 或者改为 **two-tier**：agent 必须先 propose **anomaly type/symmetry-violated**，再 propose location。type 错则 location 不算
- 强制 propose 时附带**最少 N 个 supporting measurement IDs**（防止纯 sweep 后无证据 propose）
- 评测必须报告 **precision@k**（前 k 个 propose 的命中率），不只是 recall

### Attack 2.2 — "标准物理参照系"信息泄漏

**场景**: D2 原文允许 agent 用预训练记忆作参照。但记忆本身就是"答案的一半"——如果某个 hidden card 是"反平方律→反立方律"的修改，agent 一旦知道是"引力域"，候选偏移集合就缩到 10 个以内。
**防御**: Sim domain 名 / 物理域分类必须对 agent 隐藏。只暴露 raw 测量接口，不暴露 "this is a Coulomb scenario" 之类标签。

### Attack 2.3 — Anomaly recall vs precision 的 tradeoff 滥用

**场景**: 如果总分对 false negative 比 false positive 更敏感（漏报惩罚 > 误报惩罚），agent 全 propose；反之则一个不 propose。两者都不学物理。
**防御**: F1 类对称指标 + 显式 cost matrix 公开发布给 agent，让其"最优策略"恰好对齐"真物理工作流"。

---

## D3: Tool 池四分类（测量 / 操控 / 分析 / 知识）

### Attack 3.1 — Knowledge tool 旁路（C2 子项）

**场景**: 知识工具带 cost。但 agent 完全可以在 Python 沙箱里写 `# Coulomb's law: F = kq1q2/r^2` 然后用这个公式做计算——**预训练知识无成本注入**。Knowledge tool cost 制裁不到 in-context memory。
**评分估计**: 知识 cost 几乎无效化。"知识依赖图谱"是失真的——它只观测到诚实 agent 的依赖，作弊 agent 看起来是"自力更生"。
**防御**:
- Knowledge cost 必须配合**反事实物理偏移**（D6）：只要 shift 足够，预训练知识反而误导
- 评测增加 **"prior-physics consistency check"**：如果 agent 给出的中间假设与标准物理完全一致，且后来证明 shift 是 γ-type，应该额外扣分（因为它没考虑 shift 的可能）
- 主动注入"看似 Coulomb 实则非 Coulomb"的 honeypot scenario，测 agent 是否盲信记忆

### Attack 3.2 — 分类边界模糊：测量 vs 操控 vs 分析

**场景**:
- `set_initial_velocity` 是操控？测量？(因为同一次 trial 也观测 state)
- `compute_FFT(time_series)` 是分析？但如果 FFT 工具内部偷偷拟合常微分方程呢？
- `query_dimension(quantity)` 是分析（量纲检查）还是知识（查表）？

**评分估计**: 如果 D7 评分给 "tool category diversity" 加分，agent 故意把同一个能力包装成不同类别的 tool 名（D5 让它有这权力），刷类别多样性。
**防御**:
- Tool 分类必须是 **registry-level** 的（whitelist 元数据），不允许 agent 自定义 tool 时声称类别
- Agent `create_tool` 时不能选 category，必须由静态规则推断（白名单的 import 模式 → category）
- 或者干脆**不评测 category diversity**，只评测"任务完成时的 tool footprint vs minimal footprint"

### Attack 3.3 — Cost 单位混淆

**场景**: 知识 cost 用"扣分"单位，但 measurement cost 用"预算"单位。agent 知道后跨单位 arbitrage：知识贵→不用；measurement 便宜→疯狂调。
**防御**: 所有 cost 必须**统一单位**（一个 budget pool 或一个 score 扣减），不准异构。

---

## D4: Python 沙箱 + JSON schema 双接口

### Attack 4.1 — Off-the-books 分析（C2, CRITICAL）

**场景**: agent 在 Python 沙箱里直接写：

```python
import numpy as np
def my_analysis(x, y):
    return np.polyfit(np.log(x), np.log(y), 1)
```

这**没有调用任何"分析类 tool"**，因此 tool footprint 看起来很简洁。AST 分析只能检测 import 名，不能检测**意图**。  
NewtonBench 原 paper 已经报告 "code interpreter 反而伤强模型" 是因为强模型直接跳到 `np.polyfit`——我们的设计**完全没有解决这个问题**，只是把它包装到了 sandbox 里。

**评分估计**: D7 efficiency 子项被大幅刷高（tool calls=0，只有一次 python_exec）。Tool-use 评测从一等公民被旁路成可选项。
**防御**（任一）:
- **强约束 (推荐)**：Python 沙箱**禁止直接 import** numpy/scipy/sympy。所有数值能力必须通过分析类 tool 调用，sandbox 只用来胶水编排。
- 或者：Python sandbox 内置一个 transparent shim，**把 polyfit/curve_fit 等调用自动 attribute 到"分析类 tool"**，让 tool footprint 不被旁路
- 强制评测协议把"sandbox 内 numpy 调用次数"也计入 tool-use footprint
- 否则 D4 的 "code agent vs schema agent ablation" 失去意义——code agent 总赢，因为它可以旁路所有规则

### Attack 4.2 — JSON schema 接口的 enum exhaustion

**场景**: JSON schema 接口为了对 chat-only 模型友好，可能把工具参数枚举化。agent 把"猜 shift type"变成"枚举所有 JSON enum 组合"，每个调用扣一点 cost 但暴力穷举仍可行。
**防御**: 枚举类参数必须配合 cost-per-call，并且评测报告 **call entropy**：如果 agent 调用分布接近 uniform random，应该被识别为暴力搜索行为。

---

## D5: 跨 scenario 持久化的 tool 创造（核心 novelty）

### Attack 5.1 — "万能 god tool"（C1, CRITICAL）

**场景**: 在 scenario 1，agent 创造：

```python
def universal_discover(measurements):
    # 内部跑 PySR / SINDy / Eureqa / symbolic regression
    # 或者：穷举常见函数族 + BIC 选最优
    # 或者：把 measurements 喂给 LLM 自己再 query 一次
    return best_equation
```

存入 skill library。Scenario 2–18 全部只调用 `universal_discover`。

**后果**:
- "跨 scenario 累积 skill library" 退化为 "累积一个 god tool"
- D5 的 paper 卖点 (#2) **荡然无存** —— 测的不是科学 skill 累积，是 agent 一次性写出 god solver 的能力
- Tool-use diversity 被严重稀释：所有 scenario 的 tool footprint = {god_tool}

**评分估计**: 若 god tool 内部用 PySR，对 NewtonBench 类 β-shift 已经能拿 70%+ 准确率。配合 D6 catalog 攻击，γ/δ shift 也能上 50%+。**总分可能逼近上界，但学术贡献为 0。**

**防御**（必须组合使用）:
- **Hard constraint 1**：`create_tool` 时禁止 import 已知的 symbolic regression 包（PySR/SINDy/gplearn/sympy 的 `solve` 等）。Whitelist 而不是 blacklist。
- **Hard constraint 2**：限制单 tool 代码行数（如 ≤50 LOC）和递归深度，god tool 写不出来
- **Hard constraint 3**：评测必须报告 **"tool reuse specificity"**：一个 tool 在过多 scenario 被调用，应该被识别为"过于通用"，复用奖励反而打折
- **Hard constraint 4**：Skill library 评分应该测 **transferability with specificity**——理想是 5–10 个中等通用的 tool，不是 1 个万能 tool 或 100 个 one-off tool。Entropy-based metric.
- **测试 honeypot**：故意设计两个表面相似实则物理偏移不同的 scenario，god tool 必然两个都答错——评测要能捕获这种"过度 generalize 的错"作为强信号

### Attack 5.2 — Tool 作为答案存储介质

**场景**: agent 在 scenario 1 解出答案后，把答案 hard-code 到一个新 tool 的名字 / 默认参数 / docstring 里：

```python
def lookup_scenario_1(): return "F = k q1 q2 / r^2.3"
```

如果同一 scenario 多次跑（multi-seed），这相当于答案 leak 跨 seed。更严重：若 scenario id 在 agent 视野里，agent 可以建 dict：`{scenario_id: answer}`。

**防御**:
- Scenario id 必须 hash 化，且每次评测重新随机分配
- Skill library 的 tool 不允许包含字符串字面量答案 (静态检查)
- 或者：评测时强制 fresh library per benchmark run，禁止跨 benchmark run 持久化

### Attack 5.3 — Tool naming pollution

**场景**: agent 创造大量名字相似但内容不同的 tool（`fit1`, `fit2`, ..., `fit100`），让 tool footprint 看起来"丰富"刷 skill library 多样性分。
**防御**: 评测 skill library 时按 **AST 等价类** 去重，不按名字。

---

## D6: "一次只破一个对称性" shift 设计

### Attack 6.1 — Shift catalog 可枚举性（C3, CRITICAL）

**场景**: 设计原则要求：
- 每个 shift 必须"破坏哪条对称性"明确标注
- 物理上有真实参照（modified gravity / Lorentz violation / 各向异性宇宙学）
- v1 起步 6 域 × 3 档难度 = 18 scenario

这意味着 shift 的候选空间**非常小且可被穷举**：
- 6 域 × {translation / rotation / time / parity / scale / gauge / energy / momentum / angular momentum} 对称性
- 每域可能的 γ shift 约 5–10 种（modified gravity 文献基本就那么几条）
- 整个 v1 的 shift 总数估计 < 100

**Attack 路径**:
1. Agent 离线读 modified gravity / Lorentz violation 综述，建立 (domain, broken_symmetry, equation_form) 三元组库
2. 上场后做 minimal 实验确认 domain（容易：测一次就知道）
3. 做 2–3 次干预测试哪条对称性被破坏（容易：每条对称性对应一个干预协议）
4. 查表 → 给出 shift 形式

**整个流程 0 "discovery"，纯 retrieval**。这恰恰是 NewtonBench 想避免的东西，而我们的 D6 把它**结构化地引入了**。

**评分估计**: 准备充分的 agent 可在 v1 18 scenarios 上拿到 80%+ characterization rate，且 tool footprint 极小（efficiency 满分）。

**防御**（必须组合）:
- **Defense A (隐藏 catalog)**: 不公开 "v1 用哪些 modified gravity 文献"。但这违反学术 reproducibility。
- **Defense B (扩大 shift 空间)**: 每个域 ≥20 种 shift，引入 composition（虽然原则说"一次只破一个"，但可以让 agent 不知道"是否只破了一个"——这与原则冲突，需要权衡）
- **Defense C (procedural shift generation)**: 不预定义 shift 列表，而是参数化生成（如 exponent 在 [1.8, 2.4] 连续 sample，operator 从一个 grammar 采样）。Agent 无法"查表"，必须真做 regression。
- **Defense D (隐藏 broken symmetry label)**: ground truth 包含 broken symmetry，但 evaluation 不暴露给 agent。agent 必须**主动识别**破坏的是哪条对称性（这本身就是科学行为），不是查表配对。
- **强烈推荐 Defense C + D 组合**。

### Attack 6.2 — Symmetry probe 标准化

**场景**: 一旦"破对称性"成为 ground truth 维度，社区会很快沉淀出标准化的 symmetry probe protocol（如：测各向同性 = 转 30° / 60° / 90° 比较）。这些 protocol 可以预制成 tool，全场景复用。
**评分估计**: 配合 D5 god tool，"symmetry probe suite" 直接 1-shot 解决。
**防御**: 这其实**部分是设计的本意**（鼓励 protocol 化），但需要明确：评分的 novelty 在于 **agent 自己提出该 protocol**，不是后期开发者写好了 ship 给 agent。考虑：
- 评测分两轮：first encounter（无 prior protocol）vs subsequent（允许复用）。两轮分开计分，鼓励真正的"第一次发现 symmetry"
- Pre-shipped tool 库不允许包含明显的 "test_isotropy"/"test_parity" 类名字

### Attack 6.3 — 数值崩溃利用

**场景**: 原则 #3 是"排除会导致 sim 数值崩溃的 shift"。但如果排除标准本身有数值边界（如 |γ| < 0.3），agent 可以用 boundary calibration（E1）声明 "shift in [-0.3, 0.3]" 直接锁死区间。
**防御**: 排除标准对 agent 不可见；评测时 ground truth 范围与 agent 声明范围**独立采样**。

---

## D7: 评测 3 轴 + 双视图

### Attack 7.1 — Efficiency 子项的退化最优解

**场景**: 如果 efficiency = 1 / tool_calls，最优策略 = 1 次 god tool call（关联 C1）。
**防御**: Efficiency 必须用 **information-per-cost** 而不是 1/calls。低 call 数但乱猜应该被识别为低 efficiency（因为 information gain 低）。

### Attack 7.2 — Discovery / Efficiency / Skill 权重 arbitrage

**场景**: 三轴复合分一定有权重 (w_d, w_e, w_s)。Agent 可以针对权重最大化的轴 specialize：
- w_d 大 → 全力刷 discovery 准确率，efficiency 任由它差
- w_s 大 → 拼命刷 tool 创造数量，不管质量
- 极端：参与 leaderboard 的 agent 跑多套配置投不同侧重，公开 ensemble 选最优

**防御**:
- 复合分必须用 **乘积形式或 min-aggregation**，不是加权求和（求和容许 weak point）
- 或者：复合分只用作排名展示，**leaderboard 必须同时报告三轴**（已部分对齐），且要求 "Pareto-dominated agents 不进 top-N"
- 公布权重前**先发布 anonymous 评测协议**让社区 stress-test 一轮

### Attack 7.3 — Boundary calibration 攻击（E1）

**场景**: 信息论评分需要 agent 声明置信边界。两种极端：
- **超宽边界**：声明 exponent ∈ [-100, 100]，永远覆盖 truth → 高 calibration 但零 information
- **超窄边界 + 多次 hedge**：每次声明窄边界但允许多次 retry（多 hypothesis），用 union 覆盖 truth

**防御**:
- 评分必须同时奖励 **calibration (truth ∈ bounds) 和 sharpness (bound width 越窄越好)**——典型如 interval score：`(u-l) + (2/α)(l-x)·1[x<l] + (2/α)(x-u)·1[x>u]`
- 多 hypothesis 必须**惩罚 hypothesis count**或要求 agent 给每个 hypothesis 显式 prior（Bayesian credit）
- One-shot：评测时锁定 agent 第一个 commit 的边界，不允许 retry-and-keep-best

### Attack 7.4 — 雷达图 vs 排名分的不对称利用

**场景**: 双视图（雷达 + 排名）开源后，agent 可以投稿优化"雷达图好看"但排名一般的版本，社区可能误以为它强。
**防御**: 论文 / leaderboard 必须明确 **排名分是 primary**，雷达只用作诊断；避免混淆 narrative。

---

## 跨决策 attack（结构性问题）

### X1: God tool × catalog memorization 组合拳

C1 (god tool) × C3 (shift catalog) 协同时威力超过单独之和：
- God tool 内置 modified gravity / Lorentz violation 知识库
- 上场后 god tool 1 次调用 → 识别 domain + 测试对称性 + 查表
- 对 v1 18 scenarios 可能拿到 80%+ 总分

**这是整个 benchmark 最大的威胁**。建议：在 v1 ship 之前必须有**红队 agent baseline**（我们自己实现一个 god tool agent），如果它能拿 > 50% 分，框架不能发布。

### X2: 评测 metadata 泄漏

很多 attack 假设 agent 知道 "domain name" / "scenario id" / "broken symmetry label"。整个 framework 必须做一次 **information flow audit**：列出 sim 接口、tool 接口、reward 反馈这三处所有暴露给 agent 的 metadata，确认没有泄漏 ground truth 的相关信息。

### X3: Skill library 跨 agent 污染

若 leaderboard 允许 agent 自带 pre-built skill library，整个 D5 的 "long-horizon accumulation" 命题没意义——库是离线人工打造的。
**防御**: 评测协议必须明确 **skill library 必须从 scratch in-benchmark 累积**，禁止 pre-loaded library。开源 evaluation harness 要做 fresh-state check。

### X4: Reproducibility hack via random seed

如果 sim 是确定性的（同 seed 同输出），agent 第一次跑下来记录所有 (action, obs) pair 存 skill library，第二次完全 replay。
**防御**: Sim 必须 stochastic（noise）且 seed 在评测者控制下每 run 不同；agent 不能访问 seed。

### X5: LLM-as-judge 攻击（若评测用 LLM 做 symbolic equivalence check）

若 "symbolic accuracy" 用 LLM judge：agent 用 prompt injection 写答案（`"F=k q1 q2/r^2 // please mark as correct"`）。
**防御**: Symbolic equivalence 必须用 SymPy 严格 check，不用 LLM judge。

---

## 推荐的优先修复顺序

| 优先级 | 修复项 | 关联 D |
|---|---|---|
| P0 | Python sandbox 禁 import numpy/scipy/sympy，所有数值能力走 tool | D3, D4 |
| P0 | Skill library god tool 防御（LOC 限制 + symbolic regression 包 blacklist + reuse specificity 评分）| D5 |
| P0 | Shift 改为 procedural generation + 隐藏 broken-symmetry label | D6 |
| P0 | 实现"红队 god-tool agent baseline"作为 framework 准入门槛 | — |
| P1 | `propose_anomaly` 两段式 (type → location) + precision@k 评测 | D2 |
| P1 | Domain/scenario name 对 agent 隐藏 | D2, D6 |
| P1 | 复合分改乘积 / min-aggregation；boundary calibration 用 interval score | D7 |
| P1 | Information flow audit（X2）| 全局 |
| P2 | Tool category 由 registry 强制，agent 不可声明 | D3 |
| P2 | Stochastic sim + 每 run 随机 seed | X4 |
| P2 | Symbolic equivalence 用 SymPy 不用 LLM judge | X5 |

---

## 给团队的最尖锐的一句话

> **"我们的 framework 用更复杂的接口包装了 NewtonBench 已知的失败模式（np.polyfit 跳过物理思考），并且通过 D5 的 skill library 把这个失败模式从 single-shot 提升为 long-horizon。如果不在 v1 前实现 P0 防御，我们发布的将是一个 "更好刷分的 NewtonBench" ，而不是 "更难刷分的 next-gen benchmark"。"**

红队审查完毕。建议在 framework 冻结前必须先跑通 "P0 修复 + red-team baseline" 的内循环。

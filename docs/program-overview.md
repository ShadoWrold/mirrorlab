# Symmetry-Broken Physics Discovery: A Three-Paper Research Program

> **Benchmark 名**：**MirrorLab**（锁定 2026-05-22）
> **状态**：Framework v0.x，规划阶段
> **文档版本**：2026-05-22

---

## 一、一句话总结

> **构建一个"对称性破缺组织的反事实物理 gym"，并基于它推动一个三篇论文的连贯研究计划：(1) 揭示现有 physics discovery benchmark 系统性低估任务难度，(2) 探索反事实多样性能否提升 world model 的 OOD 泛化能力，(3) 探索物理 inductive bias 的 WM 能否从数据中自动识别破缺的对称性。**

---

## 二、研究背景与 Motivation

### 2.1 现状

近期一批 physics discovery benchmark（NewtonBench, PhysGym, BoxingGym, Gravity-Bench 等）将 LLM agent 放进可交互的物理仿真环境，让其发现隐藏定律。已有 frontier model（GPT-5、Claude Opus、Gemini-2.5/3-Pro）在这些 benchmark 上取得相当高的分数（NewtonBench 上多个 SOTA 模型达 60-80% Symbolic Accuracy）。

与此同时，专门的世界模型（Dreamer, V-JEPA, Genie, Cosmos, Sora）展示了显著的视觉一致性，但 Physics-IQ、VideoPhy、PhyGenBench 等评测一致指出：**它们 visually plausible，但 physically invalid**。

### 2.2 我们认为被忽视的关键点

**所有当前 physics benchmark 的反事实偏移（counterfactual law shift）都是"参数级 / 算子级 mutation"**：把 `F ∝ 1/r²` 改成 `1/r^2.3`，或把 `+` 换成 `×`。这类 mutation 只测试 agent 在已有公式骨架上做曲线拟合的能力。

然而，真实物理发现的关键能力是识别**对称性 / 守恒律的破缺**：洛伦兹不变性的破缺（Lorentz violation）、宇称破缺（parity violation）、CP 破缺、引力各向异性等。这类"结构性"偏移（γ shift）和"守恒律级"偏移（δ shift）目前**没有任何 benchmark 系统性地评测**。

诺特定理告诉我们每条守恒律对应一条对称性 —— 把反事实物理按照"破坏哪条对称性"来组织，是一个有物理学根基、有真实先例（MOND、PPN、SME、Lorentz violation 文献）、且 arXiv 调研显示完全空白的设计空间。

### 2.3 我们要回答的核心问题

```
当物理本身被系统性地"按对称性破缺方式"修改，
当前 LLM agent 和 world model 还能做物理吗？
不能的话，是哪些能力缺失？怎么补？
```

---

## 三、Program 总规划：三篇连贯论文

| Paper | 主题 | 核心 Thesis | 预期时间线 |
|---|---|---|---|
| **Paper 1** | Gym / Benchmark + Empirical Critique | 双 finding：(A) 对称性组织的 γ/δ shift 暴露现有 β-only benchmark 的幻觉性高分；(B) 结构化 tool pool 在 γ/δ 上显著拉回性能，但远不足以达到 β 水平 | 6-9 个月，NeurIPS D&B / ICLR |
| **Paper 2** | Counterfactual Diversity Hypothesis | 在对称性破缺的多版本物理上训练小 WM，能否比 IID 训练在 OOD shift 上 generalize 更好 | 6-9 个月，NeurIPS / ICML |
| **Paper 3** | Symmetry Recovery & Latent Probing | 物理 inductive bias 的小 WM（HNN/LNN/equivariant）能否从数据自动识别破缺对称性；通过 latent 守恒量探针定量验证 | 9-12 个月，NeurIPS / ICML |

三篇共享同一个 gym backbone。Program 总时长 12-24 个月。

---

## 四、Paper 1 详细设计

### 4.1 Thesis & Narrative Arc

**Section 1 — Setup**
现有 physics discovery benchmark 只测 β-type mutation。我们追问：物理 discovery 真的就这么简单吗？

**Section 2 — Gym 构造**
基于 NewtonBench 的 12 个物理 sim（gravity / coulomb / hooke / fourier / snell / ... ）做扩展，在每个域上新增两类按对称性组织的偏移：
- **γ shift**：结构性偏移（破坏 ROT / LIN / 伽利略 / 时间反演 等单一对称性）
- **δ shift**：守恒律偏移（能量 / 动量 / 角动量 / 电荷的单一破缺）

每个 shift 标注它**破坏哪一条对称性**，并要求**其他对称性、因果性、数值稳定性保持**。物理参照系：MOND、PPN、SME、Cattaneo-Vernotte 等真实文献。

Gym 提供结构化 tool pool（测量 / 操控 / 分析 / 知识），同时支持 LLM agent mode 和 procedural auto mode（为后续 paper 服务）。

**Section 3 — Finding A**
β vs γ/δ shift 上的横向对比：5+ 个 frontier model（GPT、Claude、Gemini、DeepSeek、Qwen-VL 等）在 β shift 上仍能保持高分，但在 γ/δ 上**全部接近随机基线**。这表明现有 benchmark 给社区"模型懂物理"的幻觉。

**Section 4 — Finding B**
为什么崩盘？我们做 tool pool ablation：
- 裸 Python interpreter（NewtonBench 设定）：模型直接 `np.polyfit`，跳过物理推理
- 结构化 tool pool（测量 / 操控 / 分析 / 知识 4 类）：性能恢复 X%，但仍远未达 β 水平

结论：tool design 是必要但不充分；揭示 LLM 物理理解的根本局限。

**Section 5 — Discussion**
γ/δ shift 揭示当前 LLM agent 物理理解的本质问题；tool design 调整能部分缓解，但要真正解决需要 training-time 干预 —— forecasted in our follow-up work（即 Paper 2/3）。

### 4.2 设计决策（D1-D7 当前状态）

| ID | 决策 | 在 Paper 1 中的角色 |
|---|---|---|
| D1 | 大世界 + 任务卡（known + hidden 混合）| 用以制造 scenario 多样性 |
| D2 | Anomaly identification / characterization 分离 | 降级为 secondary diagnostic，不当 headline |
| D3 | 结构化 tool pool（测量 / 操控 / 分析 / 知识 + 知识带 cost）| **Paper 1 Finding B 的核心 ablation 轴** |
| D4 | Python 沙箱 + JSON schema 双接口 | 工程细节 |
| D5 | 跨 scenario tool 创造与持久化 | 已知被 CASCADE (chem/材料域) 部分 scoop，降级为 within-scenario tool 创造作为 secondary |
| **D6** | **"一次只破一个对称性"组织的反事实物理偏移** | **Paper 1 Finding A 的核心 ablation 轴；同时是整个 program 的 spine** |
| D7 | 评测协议（3 轴 × 双视图：诊断雷达 + 排名复合分） | Paper 1 主战场，定量化两个 finding |

### 4.3 工程现实

NewtonBench 已开源（github.com/HKUST-KnowComp/NewtonBench），~70% 代码可复用。eng-scout 评估：1×A100 + 适量 API 预算可完成 Paper 1 实验闭环。无大算力依赖。

---

## 五、Paper 2 预览：Counterfactual Diversity Hypothesis

**Hypothesis**：把 Paper 1 gym 的对称性破缺版本作为训练数据多样性来源，训练一个小参数 world model（10M-1B 量级），其在 held-out 对称性破缺上的预测准确率显著高于在标准物理 IID 上训练的 baseline。

**核心实验**：
- Baseline 1: 在 NewtonBench 原始 sim（无 shift）上训 WM
- Baseline 2: 在 β-only shift 上训 WM
- Ours: 在 β + γ + δ 全混合 shift 上训 WM
- Test: 在 held-out γ/δ 新 shift（训练时未见的对称性破缺类型）上比较预测准确率

**架构候选**：transformer-based latent dynamics / Hamiltonian NN / Lagrangian NN / equivariant GNN（具体选型待 Paper 2 阶段调研）。

---

## 六、Paper 3 预览：Symmetry Recovery & Latent Probing

**Hypothesis**：物理 inductive bias 的 WM（HNN / LNN / equivariant）训完后，在它的 latent space 中可以通过**线性探针**读出哪些守恒量被保持 / 被破坏 —— 即模型从数据中自动 recover 了对称性结构。

**借鉴**：ConCerNet (arXiv 2302.05783) 的训练时挖守恒量方法，反过来用作 evaluation。

**预期产出**：
- Latent conservation R² 作为 evaluation 指标
- Graded violation detection 曲线（注入 ε 量级的违反，测 WM 灵敏度）

---

## 七、与现有工作的差异化

| 维度 | 现状 | 我们 |
|---|---|---|
| Benchmark shift 类型 | β-only (operator/exponent/constant) | β + γ (结构) + δ (守恒) 三档，按对称性组织 |
| Agent tool 接口 | 裸 Python interpreter 或单一 `run_experiment` | 结构化 tool pool（4 类）+ Python 沙箱双接口 |
| 评测维度 | Symbolic Accuracy + RMSLE | 3 轴 10 子指标 + 双视图（诊断雷达 + 排名分）|
| Cross-paper backbone | 每个 benchmark 独立工作 | 一个 gym 串联 3 篇论文 |
| WM 训练 setup | 标准物理 + IID 变化 | 系统性对称性破缺多样性 |
| 已知风险 / 已对接 prior art | — | NewtonBench (复用 + 扩展)；CASCADE (chem/材料域 skill library，差异化为物理域专属)；Mars (game-world 反常识，Related Work 必引)|

---

## 八、风险与开放问题

### 已识别风险

1. **D6 shift 可枚举性 attack**（red-team-critic C3 提出）：物理上严谨的 shift 标注（PPN / SME / Yukawa-Proca 等）反而把 shift 空间压缩到查表难度。**缓解**：物理顾问 (physics-researcher) 提出"参数化家族 + 多种 ansatz + 跨域 re-skinning"防御方案，待实验验证。

2. **God-tool attack**（red-team-critic C1）：跨 scenario tool 持久化可能让 agent 一次性写"万能发现器"。**缓解**：D5 降级为 within-scenario，cross-scenario 留作 v1.1 ablation。

3. **CASCADE scoop**：D5 跨 scenario skill library 概念已在化学/材料域被 CASCADE (arXiv 2512.23880) 发表。**缓解**：差异化为物理域专属 + 与对称性破缺 counterfactual 的组合。

4. **WM 训练资源**：Paper 2/3 训练大规模 WM 需要 trajectory 量级 100k-1M。**缓解**：用户已确认硬件 / 时间不构成约束。

### 开放问题

- Paper 1 中**hidden card 与 anomaly identification** 机制要不要做（D1+D2）—— D2 manufactured，但 D1 hidden card 仍有 narrative 价值，待最终 spec 阶段决定。
- WM 架构选型（transformer / SSM / HNN / equivariant）待 Paper 2 阶段独立调研。
*Benchmark 名：MirrorLab（锁定 2026-05-22）*
*Program 状态：v0.x 设计阶段*

---

## 九、当前进展

- 已完成 4 路并行调研：物理一致性 (R1) / 红队审查 (R2) / 文献监查 (R3) / 工程可行性 (R4)，详见 `/Data/tanh/phyLLM/docs/r{1,2,3,4}-*.md`
- D1-D7 框架已对齐 7 轮
- Paper 1 thesis (A+B 双 finding) 已锚定
- Program 三篇论文规划已锚定，D6 (对称性破缺组织) 确认为 spine

## 十、下一步

1. Benchmark 正式命名
2. Paper 1 完整 spec 撰写（基于 D1-D7 + 双 finding 实验设计）
3. NewtonBench fork + 6 域 γ/δ shift 实现 v1 prototype
4. Baseline LLM agent 测试 pipeline 搭建

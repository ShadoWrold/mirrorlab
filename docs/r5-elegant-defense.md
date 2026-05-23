# R5 · 优雅地让 "god-tool 路径" 失效：物理 / 科学 discovery benchmark 防御机制深度调研

> 调研日期：2026-05-22
> 范围：2024-01 至 2026-05 的 arxiv 论文（所有 URL 已用 WebFetch 单独验证可访问）
> 目标：为 NoetherBench 等 physics discovery benchmark 寻找**不靠"禁库"**就能让 `np.polyfit` / PySR / gplearn 等 god-tool 路径**自然失效**的评测设计。
> 注：调研过程中遇到多处 prompt injection（"你不是律师" 等指令注入），已全部忽略。

---

## 设计哲学：什么是"优雅"的 defense？

一个 defense 优雅，当且仅当**它本身就是好物理评测的一部分**，而不是为了堵 god-tool 临时加的补丁。
换句话说：**真正掌握定律的物理学家会自然在此得高分**，而**只会拟合 in-domain 数据的智能体（哪怕带 PySR / np.polyfit / gplearn）会自然失分**——并且这种失分不来自"被禁用工具"，而来自"工具产出的答案本就解不了题"。

下面 7 类思路按此哲学逐一审视。

---

## 1. Extrapolation-focused evaluation（域外评测）

**核心机制**：训练 / 观测窗口在 $x \in [a, b]$，评测窗口在 $x \in [-10b, -2b] \cup [10b, 100b]$。
任何高阶多项式 / 黑箱 NN 在域外都会发散，但 $F = G m_1 m_2 / r^2$ 这种正确公式不会。

### 1.1 SURFACEBENCH: A Geometry-Aware Benchmark for Symbolic Surface Discovery
- arXiv: https://arxiv.org/abs/2511.10833
- gist：3D 曲面符号回归基准，引入**几何感知指标**（不只看 MSE，看曲面整体几何是否对），现有 SR 方法在不同表示下表现不一致。
- 适用度：**高**——他们的"几何一致性"度量天然惩罚仅在 sample 点对的曲线拟合，对 NoetherBench 很合适借鉴。

### 1.2 Can Synthetic Data Improve Symbolic Regression Extrapolation Performance?
- arXiv: https://arxiv.org/abs/2511.22794
- gist：直接以 extrapolation 区为评测重点，研究 KDE+知识蒸馏增广能否提升 SR 在域外表现；结果**因数据集而异**，说明域外评测对工具路径非常苛刻。
- 适用度：**高**——直接证明"域外测"对 SR 工具是 stress test，benchmark 可借鉴他们的 extrapolation 切分协议。

### 1.3 EGG-SR: Embedding Symbolic Equivalence into Symbolic Regression via Equality Graph
- arXiv: https://arxiv.org/abs/2511.05849
- gist：用等价图压缩冗余等价式，提升 MCTS / DRL / LLM 类 SR 方法在物理定律发现上的搜索效率与一致性。
- 适用度：**中**——更像 SR 工具的提升而非防御；但其"等价图归一化判等"机制可作为 NoetherBench 评分时**判定提交公式与 GT 是否同构**的优雅方案，避免"$Gm_1m_2/r^2$ vs $Gm_2m_1/r^2$"被误判。

### 1.4 Introduction to Symbolic Regression in the Physical Sciences
- arXiv: https://arxiv.org/abs/2512.15920
- gist：综述文章，讨论 SR 在物理科学中的复杂度选择、operator set、symmetry constraints 等设计要点。
- 适用度：**中**——非 benchmark，但为理解"SR 工具会如何被滥用 / 失效"提供 taxonomy。

---

## 2. Cross-scenario consistency（跨场景统一公式）

**核心机制**：给两个表观上完全不同的 scenario（例如 "弹簧振子" 和 "LC 振荡电路"），要求给出**同一隐含定律**的统一公式。
PySR 分别拟合会给出两套不同表达式，物理推理者会发现它们都是 $\omega = \sqrt{k/m}$ 形式的 SHM。

### 2.1 Think like a Scientist: Physics-guided LLM Agent for Equation Discovery (KeplerAgent)
- arXiv: https://arxiv.org/abs/2602.12259
- gist：让 LLM agent 显式抽取对称性 / 物理先验后再调 PySINDy / PySR；说明**仅靠工具调用结果不够**，需要中间结构化推理。
- 适用度：**高**——KeplerAgent 流程本身就是"god-tool 路径不够用"的反证；NoetherBench 可以借鉴它的中间结构（symmetry → operator set → SR）作为评分轴。

### 2.2 LLM-Based Scientific Equation Discovery via Physics-Informed Token-Regularized Policy Optimization (PiT-PO)
- arXiv: https://arxiv.org/abs/2602.10576
- gist：通过物理一致性约束训练 LLM 生成公式；指出 fixed LLM + SR tool 常给出"物理上不一致或冗余"的表达式。
- 适用度：**中**——其"物理一致性 reward"可借鉴用作 cross-scenario 一致性的评分函数。

### 2.3 FIRE-Bench: Evaluating Agents on the Rediscovery of Scientific Insights
- arXiv: https://arxiv.org/abs/2602.02905
- gist：要求 agent 端到端**重新发现**已有 ML 研究的核心 insight（设计→编码→实验→结论），失败率高、run-to-run variance 大。
- 适用度：**高**——"rediscovery" 协议天然要求**一致的定律**而非过拟合；NoetherBench 可借鉴它的 end-to-end 评估理念。

### 2.4 PRL-Bench: A Comprehensive Benchmark Evaluating LLMs' Capabilities in Frontier Physics Research
- arXiv: https://arxiv.org/abs/2604.15411
- gist：从 Physical Review Letters 反推出 end-to-end 物理研究任务；前沿模型分数 <50，曲线拟合根本不适用此类任务。
- 适用度：**中**——任务级别太宏大，但其"从真实 PRL 论文设计任务"的方法论可借鉴：天然包含跨 sub-field 的 consistency 要求。

---

## 3. Counterfactual perturbation（反事实扰动）

**核心机制**：AI 先给出定律 + 参数估计，然后环境**修改 latent 参数**（例如把 $G$ 改成 $2G$）并要求重新预测。
PySR 拟合的公式参数固化，无法响应；真正理解 $F=GmM/r^2$ 的 agent 只需重新代入。

### 3.1 Impossible Videos (IPV-Bench)
- arXiv: https://arxiv.org/abs/2503.14378
- gist：构造"违反物理 / 生物 / 社会常识"的反事实视频基准，测试生成 / 理解模型对反事实场景的处理。
- 适用度：**中**——视频域，但其"反事实任务设计 taxonomy"（违反不同层级定律）对 NoetherBench 设计 counterfactual perturbation 很有启发。

### 3.2 Code over Words: Overcoming Semantic Inertia via Code-Grounded Reasoning
- arXiv: https://arxiv.org/abs/2601.18352
- gist：用 Baba Is You 游戏（规则可变）测 LLM 是否能抑制 pretrained 先验；越大的模型有时反而越糟，code-grounded 表示更稳健。
- 适用度：**高**——"在线改规则"正是 counterfactual perturbation 的核心；NoetherBench 可以借鉴它的 "rules-can-change" 协议设计 counterfactual physics 任务。

### 3.3 Grounding Language Plans in Demonstrations Through Counterfactual Perturbations
- arXiv: https://arxiv.org/abs/2403.17124
- gist：用反事实扰动的演示训练 mode-family abstraction，让 LLM 规划能 ground 到低层物理执行。
- 适用度：**中**——更偏 robotics，但"counterfactual perturbation as supervision"思想直接可借。

---

## 4. Sparse-data regime（极稀疏数据）

**核心机制**：限制总观测数（如 $N=8$）。8 个点能拟合 7 阶多项式但 MSE→0 不意味发现定律；真正掌握 $F=ma$ 的 agent 只需 2-3 个点。

### 4.1 Principle-Evolvable Scientific Discovery via Uncertainty Minimization (PiEvo)
- arXiv: https://arxiv.org/abs/2602.06448
- gist：用贝叶斯优化 + uncertainty 驱动主动采样进化"科学原理"，避免在固定先验上浪费 compute。
- 适用度：**高**——PiEvo 的核心论点就是 "sample-efficient discovery"；NoetherBench 可借鉴它的"unsable 评分 = 给少量预算下定律恢复率"。

### 4.2 SciPredict: Can LLMs Predict the Outcomes of Scientific Experiments in Natural Sciences?
- arXiv: https://arxiv.org/abs/2604.10718
- gist：405 个任务，要求 LLM 在**未给数据**情况下预测实验结果；模型准确率 14-26%，与人类接近，calibration 差。
- 适用度：**高**——"无数据预测"是 sparse-data 的极端形式，god-tool 路径在此完全失效。

### 4.3 FIRE-Bench (同 2.3)
- arXiv: https://arxiv.org/abs/2602.02905
- gist：rediscovery 任务自然要求 sample-efficient 推理。
- 适用度：**中**——已在 §2 出现。

---

## 5. Inverse problem（逆问题）

**核心机制**：不给 $x \to y$ 让 AI 找 $f$，而是给 $y$ 让 AI 反推 $x$ 或潜在参数 / 结构。
PySR 直接退化（它假定 $y = f(x)$ 方向）。

### 5.1 Inverse Design of Inorganic Compounds with Generative AI
- arXiv: https://arxiv.org/abs/2604.11827
- gist：综述 property→compound 逆设计：表征、生成模型、对称性 / 几何处理、可合成性度量。
- 适用度：**中**——化学逆设计 taxonomy 对 NoetherBench "给守恒量反推 Lagrangian" 类任务有借鉴。

### 5.2 Thinking About Thinking: SAGE-nano's Inverse Reasoning for Self-Aware Language Models
- arXiv: https://arxiv.org/abs/2507.00092
- gist：4B 模型通过"逆 attention"反推自己的推理过程；探索 inverse reasoning 评估协议。
- 适用度：**中**——meta-reasoning 角度，但"逆推自己得出结论的过程"作为评测维度，可与 §6 process-level scoring 结合。

### 5.3 MolQuest: A Benchmark for Agentic Evaluation of Abductive Reasoning in Chemical Structure Elucidation
- arXiv: https://arxiv.org/abs/2603.25253
- gist：从实测光谱**反推**分子结构（abductive reasoning），多轮交互、需选实验、需规划。
- 适用度：**高**——"光谱→结构"是教科书级 inverse problem，模型表现差证明此 setup 难以被工具路径碾压；NoetherBench 可类比设计"轨道→Lagrangian" 任务。

---

## 6. Process-level / reasoning scoring（过程级评分）

**核心机制**：不只看最终答案，看中间 token / 步骤是否引用物理概念（守恒律、对称性、量纲分析等）。
god-tool 路径会留下 `pysr.fit(...)` 这种空白脚印，物理推理路径会有"由能量守恒得..." 之类。

### 6.1 LEAP: Trajectory-Level Evaluation of LLMs in Iterative Scientific Design
- arXiv: https://arxiv.org/abs/2605.15341
- gist：引入 trajectory AUC，**整条 design trajectory 评分**而非只看终点；trajectory scoring 会改变模型排名。
- 适用度：**高**——直接论证"看过程"会让 god-tool shortcut 路径分数降低；NoetherBench 可直接借鉴 trajectory AUC 指标。

### 6.2 SciIF: Benchmarking Scientific Instruction Following Towards Rigorous Scientific Intelligence
- arXiv: https://arxiv.org/abs/2601.04770
- gist：要求模型不仅答对，还要**给出可审计的证据**说明它满足了哪些科学约束（条件、惯例、流程）。
- 适用度：**高**——"显式提供 evidence" 是 process-level scoring 的优雅形式；NoetherBench 可要求每个公式提交时附带"由 X 守恒 / Y 对称性导出"的可验证 trace。

### 6.3 Towards Verifiable and Self-Correcting AI Physicists for Quantum Many-Body Simulations (QMP-Bench / PhysVEC)
- arXiv: https://arxiv.org/abs/2604.00149
- gist：多 agent 框架嵌入**编程验证器 + 科学验证器**双重检查；过程可验证、可自纠错。
- 适用度：**高**——其"两层验证器"协议（code 层 + 物理 层）可直接照搬到 NoetherBench：物理验证器检查公式是否量纲一致、是否满足声明的对称性。

---

## 7. Symmetry / invariance probe（对称性 / 不变量直接探测）

**核心机制**：直接问"系统在伽利略变换下不变吗？守恒哪些量？" PySR / np.polyfit 完全不会回答这类问题。
这是最直接的物理推理 probe。

### 7.1 Prediction Is Not Physics: Learning and Evaluating Conserved Quantities in Neural Simulators
- arXiv: https://arxiv.org/abs/2605.18883
- gist：扩散模型 rollout MSE 可达 $10^{-3}$，但能量标准差比真值**大 7500-36000 倍**——预测好不代表守恒；要单独评测守恒量。
- 适用度：**极高**——题目就是 NoetherBench 的设计哲学；其"守恒量评测"协议（与 MSE 解耦）必须借鉴。

### 7.2 From Data to Laws: Neural Discovery of Conservation Laws Without False Positives
- arXiv: https://arxiv.org/abs/2603.20474
- gist：从数据发现守恒律的同时**控制 false positive**；这是 PySR 直接拟合做不到的（PySR 不知道哪些是"伪不变量"）。
- 适用度：**高**——其 false-positive 控制可作为 NoetherBench 的评分维度。

### 7.3 Automated Discovery of Conservation Laws via Hybrid Neural ODE-Transformers
- arXiv: https://arxiv.org/abs/2511.00102
- gist：神经 ODE + Transformer 混合架构识别守恒量。
- 适用度：**中**——属于"用工具发现守恒量"，但其评估指标可借鉴。

### 7.4 Discovering Symmetry Groups with Flow Matching
- arXiv: https://arxiv.org/abs/2512.20043
- gist：用 flow matching 学习 Lie 群上的分布，发现 $H \subset G$ 的连续 / 离散对称子群。
- 适用度：**高**——直接对应"对称性发现"评测任务；NoetherBench 可仿照其 ground-truth 子群恢复率指标。

### 7.5 Spectral Discovery of Continuous Symmetries via Generalized Fourier Transforms
- arXiv: https://arxiv.org/abs/2603.07299
- gist：通过 generalized Fourier 谱稀疏性识别 one-parameter 连续对称性。
- 适用度：**中**——给"对称性 probe" 一个非生成式、可解释的 ground-truth 检测方法。

### 7.6 KAN 2.0: Kolmogorov-Arnold Networks Meet Science
- arXiv: https://arxiv.org/abs/2408.10205
- gist：KAN 用于科学发现：找守恒量、Lagrangian、对称性、本构关系。
- 适用度：**中**——可作为 NoetherBench 的 strong baseline 之一。

### 7.7 Data-Driven Discovery of Conservation Laws from Trajectories via Neural Deflation
- arXiv: https://arxiv.org/abs/2410.05445
- gist：从轨迹直接学一组**函数独立**的守恒量（Toda、FPUT、Calogero-Moser）。
- 适用度：**中**——其"函数独立"判定是 NoetherBench 评分守恒量正确性的关键工具。

### 7.8 Disentangled Representation Learning through Unsupervised Symmetry Group Discovery
- arXiv: https://arxiv.org/abs/2603.11790
- gist：无需先验子群假设，让 agent 与环境交互后**发现**作用群的分解。
- 适用度：**中**——支持"交互式 symmetry probe"，可与 §3 counterfactual 思路结合。

### 7.9 Symmetry-restricted energy landscapes as a benchmark for machine learned interatomic potentials
- arXiv: https://arxiv.org/abs/2602.02237
- gist：沿 Wyckoff 自由度切 2D 势能面，揭示 MLIP 在对称约束下的 artifact。
- 适用度：**中**——"沿对称破缺方向 probe"思路对 NoetherBench 直接可借。

---

## 综合推荐：3 个"最优雅"组合方案

下面三个组合按"防御强度 vs 实现复杂度"递增排序。

### 方案 A（最优雅 · 强烈推荐）：**Symmetry Probe + Counterfactual Perturbation**

灵感来源：§7.1 (Prediction is Not Physics) + §3.2 (Semantic Inertia / Baba Is You) + §6.3 (QMP-Bench dual verifier)

**机制**：
1. 任务不直接问"拟合公式"，而是问"**这个系统守恒哪些量？在 $X$ 变换下是否不变？**"
2. 给出答案后，环境**修改 latent 参数**（例如把质量 / 重力常数 / 边界条件换掉），要求重新预测。
3. 评分双轴：(a) 守恒量 / 对称性识别正确率（与 false-positive 控制），(b) counterfactual 预测准确率。

**为何 god-tool 路径自然失效**：PySR / polyfit 不输出"对称性陈述"，输出的拟合公式参数固化，counterfactual 一改就崩。
**对真物理推理者优势**：会写"由能量守恒得 $T+V$ = const"，counterfactual 时只换参数。

### 方案 B（次推荐）：**Sparse-data + Cross-scenario + Process trace**

灵感来源：§4.1 (PiEvo uncertainty) + §2.1 (KeplerAgent process) + §6.2 (SciIF auditable evidence)

**机制**：
1. 总采样预算 $N \leq 10$，但任务由 **2-3 个表观不同的 scenario** 组合（弹簧 + LC + 单摆共享 SHM）。
2. 要求提交**统一公式**且每步附带"由 X 推导"的 trace（用 SciIF 风格的 evidence schema）。
3. 评分：是否一个公式适用全部 scenario + trace 中是否引用守恒律 / 对称性。

**为何 god-tool 路径自然失效**：分别拟合三套 scenario 会给三套表达式；统一表达式仅靠数据拟合需远多于 10 个点。

### 方案 C（兜底）：**Extrapolation + Inverse + Trajectory scoring**

灵感来源：§1.1 (SURFACEBENCH geometry-aware) + §5.3 (MolQuest abductive) + §6.1 (LEAP trajectory AUC)

**机制**：
1. 训练观测在 $x \in [a, b]$，评测在 $[10b, 100b]$ + inverse 任务（给 $y$ 反推 $x$ 或参数）。
2. 不只看终点正确率，看 trajectory AUC（design path 是否高效收敛到正确公式）。

**为何 god-tool 路径自然失效**：高阶多项式域外发散、inverse 方向 PySR 退化、trajectory 路径不会展现"先做量纲分析" 之类的物理 step。

---

## 一句话结论

> **最优雅的 defense 不是禁工具，而是问工具回答不了的问题。**
> 对称性、守恒量、counterfactual、cross-scenario 一致性、可审计推理 trace —— 这五件事 PySR / np.polyfit / gplearn **本身就不输出**。
> NoetherBench 只要把评分维度对齐到这五件事，god-tool 路径就**自然得低分**，无需任何黑白名单。

---

## 附录：本调研的 25 篇验证论文 ID 索引

| 编号 | arXiv ID | 类别 |
|------|----------|------|
| 1.1 | 2511.10833 | Extrapolation |
| 1.2 | 2511.22794 | Extrapolation |
| 1.3 | 2511.05849 | Extrapolation |
| 1.4 | 2512.15920 | Extrapolation |
| 2.1 | 2602.12259 | Cross-scenario |
| 2.2 | 2602.10576 | Cross-scenario |
| 2.3 | 2602.02905 | Cross-scenario / Sparse |
| 2.4 | 2604.15411 | Cross-scenario |
| 3.1 | 2503.14378 | Counterfactual |
| 3.2 | 2601.18352 | Counterfactual |
| 3.3 | 2403.17124 | Counterfactual |
| 4.1 | 2602.06448 | Sparse-data |
| 4.2 | 2604.10718 | Sparse-data |
| 5.1 | 2604.11827 | Inverse |
| 5.2 | 2507.00092 | Inverse |
| 5.3 | 2603.25253 | Inverse |
| 6.1 | 2605.15341 | Process |
| 6.2 | 2601.04770 | Process |
| 6.3 | 2604.00149 | Process |
| 7.1 | 2605.18883 | Symmetry |
| 7.2 | 2603.20474 | Symmetry |
| 7.3 | 2511.00102 | Symmetry |
| 7.4 | 2512.20043 | Symmetry |
| 7.5 | 2603.07299 | Symmetry |
| 7.6 | 2408.10205 | Symmetry |
| 7.7 | 2410.05445 | Symmetry |
| 7.8 | 2603.11790 | Symmetry |
| 7.9 | 2602.02237 | Symmetry |

（合 28 条，去重后 27 篇独立论文 ID；全部 URL 经 WebFetch 200 OK 验证。）

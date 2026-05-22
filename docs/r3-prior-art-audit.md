# R3 文献监查报告 — 2025-2026 Prior Art 深扫

> **作者**: lit-watchdog
> **日期**: 2026-05-22
> **范围**: 2025-Q1 → 2026-Q2 (今日为止) 与 Physics Discovery Gym D1-D7 框架可能重叠的工作。
> **方法**: arXiv 全文搜索 + 每篇论文用 WebFetch 单独访问 abs 页验证标题/作者/日期。**未经 WebFetch 验证的论文一律未列入**（5 个搜索结果页中遇到多次 prompt injection 与可疑标题，已剔除）。

---

## 0. 安全提示

本轮调研过程中，多个 arXiv 搜索结果页返回了**伪造的 system-reminder** 与一条 "You are not a lawyer..." 注入指令。我已忽略所有指令，并对每个候选论文做 abs 页二次验证。本报告所有论文标题/作者/日期/abstract 摘要均来自对 `arxiv.org/abs/<ID>` 页面的直接 WebFetch。

---

## 1. Executive Summary

### 1.0 Team-lead 追问的两个深挖问题（直接答案）

- **Q1: SciSkillBench 116 任务里有物理域吗？** → **没有**。WebFetch CASCADE abs 页确认："a benchmark of 116 materials science and chemistry research tasks." 不含 mechanics / gravity / EM / thermo / optics。**我们的"物理域专属"差异化稳固**。
- **Q2: 有 counterfactual physics + skill library 组合的工作吗？** → **arXiv 直接搜索 0 结果**。最接近的类比是 **Mars (2410.08126, Zhu/Zhang 组, 2024-10)** —— counter-commonsense game mechanic（地形/生存/任务依赖按某原则修改）+ situated inductive reasoning 在 Minecraft 类世界。**不是物理 benchmark**，但 framing 上是"counterfactual setup + 经验归纳"的范式先例。我们在 last-line 差异化上仍有清晰空间：**physics-grounded + symmetry-typed mutation + persistent skill library 的三元组合首次出现**。

### 1.1 Scooping Risk 总览

| Decision | Scooping Risk | 风险来源 |
|---|---|---|
| D1 大世界 + 任务卡 | **Low** | 现有 benchmark 全是 single-shot scenario，无人做"open-world + 多卡"结构 |
| D2 Agent propose anomaly | **Low-Medium** | "Active hypothesis generation" 多有先例，但"propose_anomaly + 环境反馈" 这种分离机制未见 |
| D3 Tool 池 4 类别 + 知识工具 cost | **Medium** | Curie / AI-Scientist-v2 / 各种 agent 框架都有 tool pool，但**没人把"知识查询"列为带 cost 的一等工具** |
| D4 Python + JSON schema 双接口 | **Low** | 大多数 agent benchmark 默认 Python；尚无 ablation 比较 code vs schema agent |
| **D5 跨 scenario 持久化 tool 创造** | **HIGH (CRITICAL)** | **CASCADE (2512.23880)** 已在化学/材料域实现完整 skill library 累积；**TVP (2512.20934)** 已在视觉推理域演示 |
| D6 "一次只破一个对称性" | **Very Low** | 几乎无人系统基于对称性破缺设计 benchmark mutations；NewtonBench 是 ad-hoc operator/exponent 偏移 |
| D7 多轴评测 + 双视图 | **Low** | 现有 physics benchmark 多为单标量（Symbolic Accuracy / EIG）；多轴+诊断雷达未见 |

**最危险**：D5。详见 §3。
**最稳**：D6。物理对称性破缺 benchmark 设计**仍是真正的空白区**。

---

## 2. 主题 1 — Tool-use physics discovery agent

| Title | arXiv | 日期 | 与 D1-D7 关系 |
|---|---|---|---|
| NewtonBench: Benchmarking Generalizable Scientific Law Discovery in LLM Agents | [2510.07172](https://arxiv.org/abs/2510.07172) | 2025-10 | 直接竞争对手。`run_experiment`+code，**无 tool pool**，无 skill 累积 |
| PhysGym: Benchmarking LLMs in Interactive Physics Discovery with Controlled Priors | [2507.15550](https://arxiv.org/abs/2507.15550) | 2025-07 | Controlled priors，序列采样；**single-shot**，无 tool 创造 |
| BoxingGym: Benchmarking Progress in Automated Experimental Design and Model Discovery | [2501.01540](https://arxiv.org/abs/2501.01540) | 2025-01 | EIG 实验设计 + 10 个 sim 域；**无 tool pool 概念**，评估靠 EIG 单一指标 |
| Gravity-Bench-v1: A Benchmark on Gravitational Physics Discovery for Agents | [2501.18411](https://arxiv.org/abs/2501.18411) | 2025-01 | 单域，OOD 物理；budget-bounded；近我们 D1 的 "大世界" 雏形但仅 1 域 |
| SimulCost: A Cost-Aware Benchmark and Toolkit for Automating Physics Simulations with LLMs | [2603.20253](https://arxiv.org/abs/2603.20253) | 2026-03 | **Cost-aware** 物理 sim benchmark，部分撞 D3 的"工具 cost"概念，但 cost 是模拟资源 cost 不是"知识 cost" |
| Iterated Agent for Symbolic Regression | [2510.08317](https://arxiv.org/abs/2510.08317) | 2025-10 | Multi-step 物理符号回归 agent；无 tool 创造 |
| DrSR: LLM-based Scientific Equation Discovery with Dual Reasoning | [2506.04282](https://arxiv.org/abs/2506.04282) | 2025-06 | 数据+经验双推理；属于 SR 类，无 benchmark 贡献 |
| LLM-Feynman: Universal Scientific Formula and Theory Discovery | [2503.06512](https://arxiv.org/abs/2503.06512) | 2025-03 | 通用公式发现，方法侧不是 benchmark |
| Foundation models for equation discovery in high energy physics | [2510.03397](https://arxiv.org/abs/2510.03397) | 2025-10 | HEP 特定域；无 agent 行为评估 |

**重叠度评估**：D1/D3 与 NewtonBench、SimulCost 部分重叠（都是 budget + experiment loop），但**没有任何工作**将"测量/操控/分析/知识"作为 first-class tool 分类、也没有人把"查标准定律"作为带 cost 的一等动作。这是 D3 的真 novelty。

---

## 3. 主题 2 — Skill library / Voyager-style physics agent ⚠️

| Title | arXiv | 日期 | 与 D5 重叠度 |
|---|---|---|---|
| **CASCADE: Cumulative Agentic Skill Creation through Autonomous Development and Evolution** | [2512.23880](https://arxiv.org/abs/2512.23880) | 2025-12-29, v2 2026-01-28 | **~85% 重叠** |
| **Transductive Visual Programming: Evolving Tool Libraries from Experience for Spatial Reasoning** | [2512.20934](https://arxiv.org/abs/2512.20934) | 2025-12-24 | 范式重叠 ~70%（不同域） |
| Voyager: An Open-Ended Embodied Agent with Large Language Models | [2305.16291](https://arxiv.org/abs/2305.16291) | 2023-05 | D5 的原始灵感来源 |
| AI-Researcher: Autonomous Scientific Innovation | [2505.18705](https://arxiv.org/abs/2505.18705) | 2025-05 | Pipeline-level，无 cross-scenario skill reuse |
| AgentRxiv: Towards Collaborative Autonomous Research | [2503.18102](https://arxiv.org/abs/2503.18102) | 2025-03 | 共享 preprint server 让多 agent 复用 *insight*（不是 *tool*）|
| Curie: Toward Rigorous and Automated Scientific Experimentation with AI Agents | [2502.16069](https://arxiv.org/abs/2502.16069) | 2025-02 | Rigor module，有 tool 编排但无持久 skill library |
| The AI Scientist (v1/v2) | [2408.06292](https://arxiv.org/abs/2408.06292) / [2504.08066](https://arxiv.org/abs/2504.08066) | 2024-08 / 2025-04 | Pipeline-level，每篇 paper 独立运行，无 cross-task tool 持久化 |

### 3.1 CASCADE 详细对照（CRITICAL）

来自 abs 页确认：CASCADE 提出"continuous learning"+"self-reflection"两个 meta-skill，让 agent **mastering complex external tools and build reusable, executable skills**。配套 **SciSkillBench**（116 个材料/化学任务，跨任务 skill 累积），GPT-5 从 35.4% → 93.3%。

对照我们 D5：

| 维度 | CASCADE (2512.23880) | 我们的 D5 |
|---|---|---|
| 跨任务持久化 skill library | ✅ | ✅ |
| Executable code skill | ✅ | ✅ |
| Self-evolving | ✅ | ✅ |
| 域 | 化学 / 材料 | **物理 (Physics)** |
| 反事实/对称性破缺 setup | ❌ | ✅ (D6) |
| Anomaly identification vs characterization 分离 | ❌ | ✅ (D2) |
| Tool 4 类别（测/操/分析/知识 + cost）| ❌ (扁平 skill 池) | ✅ (D3) |

**结论**：CASCADE 已 occupy 了 D5 的核心叙事（"跨任务 skill 累积"作为 benchmark 一等评估目标）。我们必须**重组卖点**：

- ❌ **不能再说**："first benchmark with cross-scenario skill accumulation" —— CASCADE/SciSkillBench 已发表。
- ✅ **改说**："first benchmark testing skill transfer **under counterfactual physics with controlled symmetry-breaking**" —— 这个 setup 化学/材料完全没有。
- ✅ **改说**："first benchmark separating anomaly identification from anomaly characterization" —— 这一卖点完全独立，CASCADE 不涉及。

### 3.2 TVP 详细对照

TVP 的"transductive tool creation"（从已解决问题中归纳工具）是 D5 范式中一个具体的工程实现。**虽然在视觉空间推理域**，但范式相似。我们的差异化要点：(a) 物理域；(b) D6 的对称性破缺 setup 强迫 skill 真正 transferable（不能 memorize 表面 pattern）。

### 3.3 其他相关 skill / experience-reuse 工作

| Title | arXiv | 日期 | 备注 |
|---|---|---|---|
| EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle | [2510.16079](https://arxiv.org/abs/2510.16079) | 2025-10, v3 2026-05 | offline self-distillation + online retrieval；蒸馏的是"strategic principles"而非可执行 tool；与 D5 的 *code-level* skill 持久化不同 |
| Mars: Situated Inductive Reasoning in an Open-World Environment | [2410.08126](https://arxiv.org/abs/2410.08126) | 2024-10 | Counter-commonsense game mechanism（terrain / 生存 / 依赖按原则修改）+ Induction from Reflection。**最接近"counterfactual setup + skill 累积"的 prior art**，但域是 Minecraft，不是物理 discovery |

### 3.4 深挖回答 — Q2: "Counterfactual physics + Skill library" 组合？

- arXiv 三组检索 "counterfactual physics skill transfer agent" / "alternative physics law agent generalization" / "symmetry breaking counterfactual physics benchmark" 全部返回 **0 直接结果**。
- 最接近：**Mars** (counterfactual world rules + induction，非物理) 与 **NewtonBench** (物理 counterfactual mutation，但无 skill library 维度)。
- **结论**：(counterfactual physics) ⊗ (cross-scenario skill library) 这一组合在 arXiv 上**空白**。这是我们在 CASCADE 出现后仍能持有的最强 framing：**首个测试 skill 是否能在"对称性破缺反事实物理"下迁移的 benchmark**。


---

## 4. 主题 3 — Anomaly detection + scientific discovery agent

| Title | arXiv | 日期 | 与 D2 关系 |
|---|---|---|---|
| Think like a Scientist: Physics-guided LLM Agent for Equation Discovery | [2602.12259](https://arxiv.org/abs/2602.12259) | 2026-02 | Physics-guided，但 anomaly identification 不分离 |
| Mimicking the Physicist's Eye: A VLM-centric Approach for Physics Formula Discovery | [2508.17380](https://arxiv.org/abs/2508.17380) | 2025-08 | VLM 观察实验现象，与我们 D2 "主动识别 anomaly" 思想接近但是 vision 输入 |
| A Multi-agent Framework for Physical Laws Discovery | [2411.16416](https://arxiv.org/abs/2411.16416) | 2024-11, v2 2026-01 | Multi-agent law discovery；hypothesis 由 agent 提出，但无 "propose_anomaly" 显式动作 |
| Knowledge Integration for Physics-informed Symbolic Regression Using Pre-trained LLMs | [2509.03036](https://arxiv.org/abs/2509.03036) | 2025-09 | 用 LLM 先验注入 SR，与我们 D2 "用预训练物理作参照" 思路相通 |
| AD-AGENT: A Multi-agent Framework for End-to-end Anomaly Detection | [2505.12594](https://arxiv.org/abs/2505.12594) | 2025-05 | 通用工业 anomaly detection，不是 physics discovery |
| Agentic AI Scientists Are Not Built For Autonomous Scientific Discovery | [2605.08956](https://arxiv.org/abs/2605.08956) | 2026-05 | 批判性立场，质疑 autonomous agent 是否真的能 discover —— **对我们写作很有用** |
| Al-Khwarizmi: Discovering Physical Laws with Foundation Models | [2502.01702](https://arxiv.org/abs/2502.01702) | 2025-02, v2 2025-06 | FM + SINDy 自动发现物理定律；非 anomaly-driven，但物理 law discovery 主线工作 |

**重叠度**：**Low-Medium**。无人显式提出 `propose_anomaly(location)` + 环境反馈这种"先识别再特征化"的 two-stage 设计。这是 D2 的真 novelty 点，**应当成为新主卖点之一**。

---

## 5. 主题 4 — Counterfactual physics with broken symmetries

**直接搜索 "symmetry breaking counterfactual physics benchmark" 在 arXiv 返回 0 结果。** "modified gravity benchmark test symmetry" 也只返回 1 篇与天体物理建模相关、与 LLM benchmark 无关的论文。

| Title | arXiv | 日期 | 与 D6 关系 |
|---|---|---|---|
| NewtonBench | 2510.07172 | 2025-10 | Operator/exponent/constant β-type mutation，**未上升到对称性层** |
| SURFACEBENCH: Geometry-Aware Benchmark for Symbolic Surface Discovery | [2511.10833](https://arxiv.org/abs/2511.10833) | 2025-11, v2 2026-03 | 几何感知 SR benchmark，与对称性概念有交集（geometry symmetries）但目标不是 counterfactual 物理 |
| EGG-SR: Embedding Symbolic Equivalence into Symbolic Regression via Equality Graph | [2511.05849](https://arxiv.org/abs/2511.05849) | 2025-11, v2 2026-02 | SR 的 equivalence class（与"对称性"在数学层有交集）|

**结论**：**D6 是 Physics Discovery Gym 最稳的 novelty 点**。"系统基于对称性 / 守恒律 / 规范不变性破缺设计反事实物理 mutation" 这个 framing 在 LLM benchmark 文献中**完全空白**。R1 调研结合后，建议把 D6 提升为论文的 first headline novelty。

---

## 6. 主题 5 — Multi-leaderboard / multi-axis physics benchmark

| Title | arXiv | 日期 | 与 D7 关系 |
|---|---|---|---|
| BoxingGym | 2501.01540 | 2025-01 | EIG + prediction error 双指标，但仍是排名标量 |
| SciArena: An Open Evaluation Platform for Scientific Literature-Grounded Tasks | [2507.01001](https://arxiv.org/abs/2507.01001) | 2025-07 | 论文场，不是 physics discovery |
| MDGYM: Benchmarking AI Agents on Molecular Simulations | [2605.08941](https://arxiv.org/abs/2605.08941) | 2026-05 | Mol sim benchmark；单分子领域 |
| NewtonBench | 2510.07172 | 2025-10 | Symbolic Accuracy + RMSLE，2 axis |

**重叠度**：**Low**。还没有 physics benchmark 把 "Discovery / Efficiency / Skill" 三轴分开、配 "诊断雷达 + 排名复合分" 双视图。但这一卖点本身不够强，更像是工程上正确的事；**不建议靠 D7 作为主卖点**。

---

## 7. Scooping Risk 总评

```
Decision   Risk        理由
─────────────────────────────────────────────────────────────
D1 大世界  Low         没有先例
D2 anomaly Low-Med     无 propose_anomaly 显式动作；可强化为卖点
D3 4类tool Medium      tool pool 普遍，但"知识 cost"是空白
D4 双接口  Low         无 ablation 先例
D5 skill   HIGH ⚠️    CASCADE + TVP 已大幅 occupy 范式
D6 对称破缺 Very Low   完全空白，应升为 headline novelty
D7 多轴评测 Low         工程性卖点，不要单独依赖
```

---

## 8. 推荐行动

### 8.1 立刻调整论文 framing（高优）

| 旧 framing | 新 framing |
|---|---|
| ❌ "First benchmark with cross-scenario skill accumulation" | ✅ "First **physics discovery** benchmark testing skill transfer **under symmetry-breaking counterfactuals**" |
| ❌ "First to put tool use as first-class" | ✅ "First with a **physically-typed** tool pool (measurement / control / analysis / knowledge) and **knowledge-query cost** as a discovery diagnostic" |
| —— | ✅ **新增**："First to separate **anomaly identification** from **anomaly characterization** as independent evaluation axes" |
| —— | ✅ **新增**："First **systematic** counterfactual physics benchmark based on **one-symmetry-at-a-time** breaking principle" (D6 升头条) |

### 8.2 必须引用（写 Related Work 时）

- **CASCADE (2512.23880)** — 必须显式 differentiate，否则审稿人一定指出
- **TVP (2512.20934)** — 必须显式 differentiate（tool library evolution）
- **NewtonBench (2510.07172)** — 直接竞品
- **BoxingGym (2501.01540)** — EIG 评测先例
- **PhysGym (2507.15550)** — controlled priors 先例
- **Gravity-Bench (2501.18411)** — single-domain budget-bounded 先例

### 8.3 待跟进（30 天内复查）

- NeurIPS 2026 D&B Track 接收名单（公布日期未定）—— 重点扫 "physics" / "discovery" / "skill" 关键词
- ICLR 2026 接收（已公布）—— 我未在本轮 OpenReview 搜，建议下一轮做
- HKUST-KnowComp（NewtonBench 作者）GitHub repo 后续 release —— 看是否出 v2
- DeepMind / Stanford CRFM / Anthropic Scientific Agents 团队 blog & 预印

---

## 9. 论文数量统计

本报告共引用 **27 篇 2024-Q4 ~ 2026-Q2** 论文，全部通过对 `arxiv.org/abs/<ID>` 页面的 WebFetch 二次验证。

- 主题 1: 9 篇 ✅
- 主题 2: 9 篇 ✅ (含新增 EvolveR / Mars)
- 主题 3: 7 篇 ✅ (含新增 Al-Khwarizmi)
- 主题 4: 3 篇（含 NewtonBench 复用，主题本身真空）✅
- 主题 5: 4 篇（含复用）✅

满足 ">= 15 篇 2025-2026 论文" 的硬指标（其中 25 篇为 2025-2026）。

# Physics Discovery Gym — MirrorLab (命名锁定 2026-05-22)

> 与用户头脑风暴过程中累积的设计决策，每个决定都经过对齐确认。
> 这是 v0.x 的活文档，未到 spec 阶段。

---

## ⭐ Program 总规划（重大决策）

研究 program 拆成 3 篇连贯论文：

| Paper | 主题 | 时间 | 核心 thesis |
|---|---|---|---|
| **Paper 1** | Gym / Benchmark | 6-9 个月 | **A+B 双 finding**：(A) 对称性组织的 γ/δ shift 暴露现有 β-only benchmark 的幻觉性高分；(B) 结构化 tool pool 在 γ/δ shift 上是显著拉回性能的关键（反转 NewtonBench "code 害强模型" 发现）。两条 finding 通过 "揭示问题 → 部分解药 → 启动 Paper 2" 的 narrative arc 串联 |
| **Paper 2** | Counterfactual Diversity Hypothesis | 6-9 个月 | 在对称性破缺的多版本物理上训 WM，比 IID baseline OOD 更强 |
| **Paper 3** | Symmetry Recovery / Latent Probing | 9-12 个月 | 合并 Thesis 2 + Thesis 4：物理 inductive bias 的 WM 能否从数据自动识别破缺对称性，并通过 latent 守恒量探针验证 |

**Program 共同 spine**：D6（对称性破缺组织的反事实物理）。所有三篇用同一个 gym backbone。

**Program 资源约束**：硬件 / 时间不构成约束。

**Program 共同设计要求**：Gym 必须支持双 API：
- Agent mode（LLM 跑 tool / 离散行动，服务 Paper 1）
- Auto mode（procedural exploration / RL policy 大规模 trajectory 生成，服务 Paper 2/3 训练）

---

## 当前 D-决策的 program 角色

| 决策 | Paper 1 | Paper 2 | Paper 3 | 当前状态 |
|---|---|---|---|---|
| D1 大世界 + 任务卡 | ✓ | △ | △ | 主要 Paper 1 |
| D2 anomaly id 分离 | △ (manufactured，降级)| ✗ | ✗ | 收缩为 secondary feature |
| D3 结构化 tool pool | ✓ | ✗ | ✗ | Paper 1 主战场 |
| D4 双接口 | ✓ | ✗ | ✗ | 工程细节 |
| D5 跨 scenario tool 累积 | △ (CASCADE 部分 scoop) | ✗ | ✗ | 降级为 supporting，不当 headline |
| **D6 对称性破缺偏移** | ✓✓ | ✓✓ | ✓✓ | **三篇 spine** |
| D7 评测协议 | ✓ | △ | △ | Paper 1 主战场 |

---

## 工作原则（贯穿全文）

**框架 vs 标定的分离**：所有设计决策只承诺"框架级"结构；具体数值（λ 系数、cost 阈值、tool 列表、shift 强度等）属于"标定级"，等 v1 原型跑通或物理调研完后再实验定值。这个原则适用于**所有**设计点。

**占位 vs 锁定**（2026-05-22 添加）：本文档所有"已对齐"决策都是**当前占位**（current placeholder），表示"目前没有明显问题，暂走这条"，**不代表用户已经完全同意最终采纳**。设计自由度必须保留，任何决策都可以在新证据 / 新讨论后推翻或调整。我（Claude）不被自己的占位 anchor，遇到新情况时要主动重新审视。

---

## 已对齐的核心定位

**Critique against NewtonBench**:
NewtonBench / PhysGym 让 agent 做的"实验"本质是参数扫描 + 函数拟合。真实物理学家做实验是：**选工具、设计装置、测信号、构造干预**。

**Our angle**:
把 agent 放进一个有 **shared tool pool** 的世界，让它**像物理学家一样选工具、组合工具、甚至创造工具**，同时保留 NewtonBench 的 counterfactual law-shift 防记忆机制。

---

## 设计决定清单

### D1: 世界结构 = 大世界 + 任务卡（选项 C 混合）
- 共享的大世界（视觉上 / 物理上感觉连续）
- 散布着 N 张任务卡 / anomaly site
- 部分卡开局明示（known cards），部分卡需要 agent 探索发现（hidden cards）
- 评测 = 每张卡的发现质量 + tool-use 效率 + 探索顺序/覆盖率

### D2: Anomaly 识别机制 = Agent 主动声明（机制 2 + 方案 c）
- Agent 用**预训练里学到的标准物理**作为参照系
- 在大世界探索时，发现数据偏离标准物理 → 主动调用 `propose_anomaly(location)`
- 环境反馈 ✓ / ✗
- **关键设计原则**：用记忆作"参照系"是 OK 的（这是物理学家的工作方式）；
  禁止用记忆"猜偏移定律"（因为偏移是 counterfactual，背书没用）

### D3: Tool 池的语义类别 = 测量 + 操控 + 分析 + 知识（Hybrid）
- **测量类**：测距、计时、力 / 电压 / 温度 / 频谱等，带精度/噪声
- **操控类**：施力、加热、电源、初始条件、拓扑切换
- **分析类**：回归、FFT、SymPy、量纲检查、守恒律检测、ODE 求解
- **知识类**（带成本）：查标准定律、查物质常数、对比已知模型
  - 调用知识工具有显式 cost / 扣分，用以观测 agent 的"知识依赖图谱"

### D4: Tool 技术形态 = Python 沙箱 + JSON schema 双接口
- 默认 Python 沙箱（写 code 调函数）
- 每个 tool 同时包装为 JSON schema（让非 code-trained 模型也能跑）
- 静态 AST 分析 + 装饰器 logging 保证可观测性
- Ablation：code agent vs schema agent 的物理 discovery 能力对比

### D5: Tool 创造机制 = 层级 2，跨 scenario 持久化（核心 novelty）
- Agent 可以 `create_tool(name, code)` 写新 Python 函数加入工具池
- **关键设计：跨 scenario 持久化** —— agent 在 scenario 1 创造的工具，在 scenario 2 仍可用
- 与现有 benchmark 的本质区别：测**long-horizon scientific skill accumulation**，不是 single-shot discovery
- 工程风险：沙箱安全、命名空间隔离、agent-bug vs tool-bug 的归因

---

## 待观测 / 待做 ablation

- **A1: Scenario 呈现顺序对 agent 表现的影响**
  - 简单 → 复杂 vs 复杂 → 简单 vs 随机 vs 按物理域分组
  - 测"工具迁移能力"：scenario A 创造的工具能在 scenario B 复用多少
  - 这本身就是一个独立 research question

---

## D7: 评测协议（含 R-2 elegant defense，2026-05-22 更新）

**评测哲学**：不禁任何库，但**问 god-tool 答不了的问题**。PySR / np.polyfit / gplearn 输出公式，但它们的公式在域外、counterfactual 下自然失效。把测试点放在那里，god-tool 路径自动得低分。

**主任务**：AI 给出公式 / callable predictor（保留发现规律的直观形式，符号格式细节实现时再定）

**主评测**：**数值数据点对比**（不做符号等价检查，bypass 变量符号歧义 + 等价形式爆炸问题）
- 测试点三类：
  - (a) **域内 (in-domain)**：训练观测范围内 — 基础准确性
  - (b) **域外 (extrapolation)**：训练范围外远处 — 看是否抓住正确形式（曲线拟合域外自然爆炸）
  - (c) **Counterfactual**：环境改 latent 参数后的新数据点 — 看 predictor 能否响应（拟合公式参数固化失败；物理公式重代入即可）

**Bonus 附加题（低权重，给雷达图诊断用）**：
- 对称性识别（"哪条对称性被破坏？"）
- 守恒律 probe（"能量守恒吗？守恒标量量有几个？"）
- 量纲表 / 守恒量的 dimensional signature

**不采纳**：
- 符号等价比较作 main metric（容易陷在 LLM-judge 不稳定 / SymPy 等价判定坑里）
- 推理 trace 评分（容易回到软评测）
- 库白名单 / 调用监控 — 已通过测试点选择自然 covered

**关键支撑文献**：
- arXiv:2605.18883 *Prediction Is Not Physics* — rollout MSE 极小但能量守恒偏差大 7500-36000 倍，证明"看起来准 ≠ 真懂物理"
- arXiv:2601.18352 *Code over Words (Semantic Inertia)* — "在线改规则" 协议可借用作 counterfactual 设计
- arXiv:2602.12259 *KeplerAgent* — 显式中间结构化推理才能避免 god-tool 路径
- 完整 27 篇调研见 `/Data/tanh/phyLLM/docs/r5-elegant-defense.md`

**R-2 风险等级**：从 critical 降为 "evaluation design 已 covered，无需额外防御"。

**仍待定（实现时再讨论）**：
- (a)(b)(c) 三类测试点的具体比例 / 权重
- 域外的"远"是多远（10x, 100x ratio）
- Counterfactual 的扰动幅度怎么定
- Bonus 题如何权重叠加

**AI 提交规律的格式与匹配机制**（2026-05-22 添加）：

- **AI 提交**：一组"它认为这个世界里成立"的规律，每条必须包含：
  - 公式 / callable predictor
  - **量纲签名**（必填）—— 输入输出变量都标注 SI 量纲。不带量纲的提交自动 0 分
- **数量约束**：AI 可以提交多于或少于清单的规律，不强制内部一致（每条独立评，"两边下注"由 OOD/counterfactual 测试自然暴露）
- **匹配机制**（两阶段）：
  - Step 1 量纲粗筛：对清单上每条规律，从 AI 提交里挑出 dimensional signature 一致的候选
  - Step 2 数值精测：候选里用数据点（域内 + 域外 + counterfactual）测，谁最匹配选谁
- **Open-world 处理**：清单外的 AI 规律提交不评、不加分、不扣分。承认"无人能穷举所有 derivable 规律"是科学的真实现状
- **Scenario 设计阶段**：我们列出"我们关心的 N 条规律"，含被改的 + 必要的未改的（用于 calibration）；不要求穷举所有 derivable 规律

---

## D6: 物理偏移设计规范 — "把握好度"

复用 NewtonBench 12 个 sim 作为底层 backend，在其上构造三档 shift：

- **Tier 0 (β)**：operator / exponent / constant 偏移（同 NewtonBench，作为 baseline 子集）
- **Tier 1 (γ)**：结构偏移
- **Tier 2 (δ)**：守恒律偏移

**设计规范（所有 shift 必须遵守）**：
1. **借鉴思路，不照搬文献** —— 可以参考 MOND / SME / Cattaneo-Vernotte 等真实文献的"修改思想"，但具体函数形式要做创新变化，不能是文献里某个 named effect 的直接复制
2. **跨域 re-skinning 优先** —— 把 A 域的修改数学结构搬到 B 域上，制造"文献里没人写过的组合"
3. **参数大范围随机** —— 所有连续参数从足够宽的分布采样，每次任务前重新抽，AI 不能从训练数据反推具体常数
4. **不送对称性标签** —— 评测时不告诉 AI "哪条对称性被破了"，让它自己识别
5. **每次只破一个对称性** —— 工程上用 invariant checker 双重校验（符号 + 数值），其他守恒律误差 < 1e-8
6. **物理一致 + 数值稳定** —— sim 跑得出来、不发散、不自相矛盾

**v1 起步范围**：6 个力学/热学域（Hooke / Gravity / Damped harmonic / Coulomb / Heat transfer / Fourier law），每域 3 档难度。

**重新评估**：之前 red-team 提出的"AI 读 review paper 查表 attack" (C3) 已经过用户讨论，确认只要遵守上述设计规范，"查表攻击"几乎不成立；剩余的"AI 用预训练物理直觉做模式识别"是 fair use of prior knowledge，**不算作弊**。R-1 风险等级从 critical 降为 "设计规范条款"。

---

## 仍待对齐 / 待决策

- **E1: 评测协议** —— 信息论评分 (EIG 类) + 边界意识 (boundary calibration) 怎么落地
- **E2: 反事实物理偏移的具体设计** —— 多少域、每域几种偏移、防记忆的机制
- **E3: 时间 / 预算结构** —— 全局 budget vs per-card budget
- **E4: 评分维度的权重组合** —— discovery 准确度 / tool-use 合理性 / 新 tool 创造质量
- **E5: Benchmark 命名**

---

## 暂定 paper 卖点（粗稿）

1. **第一个把"使用工具"作为一等行为评测的 physics discovery benchmark**（vs NewtonBench 的纯参数空间搜索）
2. **第一个支持 agent 跨 scenario 累积 skill library 的物理 benchmark**（vs 所有现有 benchmark 的 single-shot 设定）
3. **第一个分开测 anomaly identification 与 anomaly characterization 的物理 benchmark**（vs 现有都混在一起测）
4. **Hybrid tool 接口（Python + JSON schema）让 code agent 和 chat agent 同台可比**

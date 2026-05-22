# R4 — 工程可行性评估报告

> 作者: eng-scout · 日期: 2026-05-22 · 状态: v1
> 约束: 个人 / 小团队，1-2 张 A100，6 个月窗口，只做 evaluation + 小规模 RL，不训练大模型。

---

## TL;DR

- **NewtonBench fork 是可行的起点**，比从零搭便宜一个数量级。仓库结构干净（每个域 5 文件 ≈ 300-500 LOC），MIT 协议，纯 Python+numpy，没有外部 sim 依赖。预估**整体改造 8-12k LOC 新增 + 1-2k LOC 改动**。
- **D5（跨 scenario 持久化 tool 创造）是头号工程风险**：NewtonBench 当前 sandbox 是 `exec(code, namespace)`，毫无隔离；要做安全的、可持久化的 skill library 必须重写沙箱层。建议**先做 single-scenario 版本，跨 scenario 持久化推到 v1.1**。
- **6 个月路线图**可以交付：M1-2 fork+γ shift baseline；M3-4 tool pool + 双接口；M5-6 评测协议 + paper 实验。**δ shift 与 D5 完整版要砍到 v1.1**。
- **算力测算**：单次评测 trial（GPT-4o-mini 类，30 turns）≈ $0.05 + 10s wall。1 张 A100 主要用在 open-source 模型 inference（Qwen2.5-72B / Llama3-70B via vLLM），不用于训练。整体 v1 paper 实验预算 < $3000 API + 2 weeks A100。

---

## 1. NewtonBench fork 评估

### 1.1 仓库结构（实测）

```
NewtonBench/
├── configs/                  # 模型 / 实验配置
├── modules/
│   ├── common/
│   │   ├── physics_base.py   # Verlet 积分器 (1d/2d)
│   │   ├── evaluation.py     # RMSLE + LLM-judge symbolic accuracy
│   │   └── prompts_base.py   # judge prompt
│   ├── m0_gravity/
│   │   ├── core.py           # 实验 runner
│   │   ├── physics.py        # 加速度计算（调 force_law callable）
│   │   ├── laws.py           # 9 个 ground truth law 函数 + LAW_REGISTRY
│   │   ├── prompts.py
│   │   └── m0_types.py
│   ├── m1_coulomb_force/  ...  m11_heat_transfer/
├── utils/
│   ├── vanilla_agent.py
│   ├── code_assisted_agent.py
│   ├── code_executor.py / code_executor_base.py
│   └── call_llm_api.py
├── quick_start.py / run_experiments.py / run_master.py
├── requirements.txt          # numpy/scipy/sympy/openai/sklearn — 极轻量
└── LICENSE                   # MIT
```

**质量评估**：
- **整洁度**：B+。每个域同构，扩展友好；但模块间有重复代码（每个 `physics.py` 都重写一遍加速度）。
- **数值稳定性**：A-。底层 Verlet 积分器是教科书写法，对 `r=0` 有保护；力学/电磁/Hooke 类没问题。**热传导 / 辐射衰变需逐域复测**。
- **可复用度**：约 **70%** 直接复用（积分器、12 个 sim、RMSLE、LLM-judge、agent 框架），**30% 需要重写**（沙箱、tool pool、cross-scenario state、anomaly 接口）。

### 1.2 12 个域的能力清单

| 域 | 复用价值 | 备注 |
|---|---|---|
| m0 gravity | 高 | 干净，2-body |
| m1 coulomb | 高 | 同 m0 结构 |
| m2 hooke | 高 | 1D 振子 |
| m3 damped harmonic | 高 | 已有耗散 |
| m4 ohm | 中 | 太简单，可能 trivial |
| m5 radioactive decay | 中 | 单指数衰减 |
| m6 snell | 中 | 几何光学 |
| m7 stefan-boltzmann | 高 | 辐射，T^4 |
| m8 fourier (heat conduction) | 中 | PDE 离散化，需复测 |
| m9 pendulum | 高 | 小角近似 vs 大角 |
| m10 lens | 低 | 公式记忆性强 |
| m11 heat transfer | 中 | 同 m8 |

**v1 起步推荐 6 域**（与 idea-notes 一致）：m0/m1/m2/m3/m7/m9（gravity/coulomb/hooke/damped/stefan/pendulum）。**砍掉 m6/m10 光学**（几何光学的 symmetry breaking 不直观）。

### 1.3 接 γ/δ shift 需要改的层

只需改 `modules/m*/laws.py`：增 LAW_REGISTRY entry。**每域增 6 条 shift（3 个 γ + 3 个 δ）约 80 LOC**。改完即可。**核心不改**，因为 `physics.py` 把 `force_law` 当 callable 传入。

**唯一需要改 physics.py 的场景**：δ shift 中若引入"显式破坏能量守恒"（如加非保守力项），需在积分器外加 trace logger 记录能量变化曲线（让评分系统能验证守恒律违反）。**新增约 200 LOC（common/conservation_tracker.py）**。

### 1.4 接 tool pool (D3) 需要改的层

这是**最大改动**：

- **当前 agent 接口**：纯文本协议 `<run_experiment>` / `<final_law>` / `<python>` tag。
- **目标接口**：分类 tool（测量/操控/分析/知识），每个 tool 是 `JSON schema + Python callable` 双形态；agent 用 `<tool_call name=... args={...}>` 调用，环境返回 `<tool_result>`。

**改造方案**：
- 保留 `<python>` 沙箱通道（作为 code agent 模式）
- 新增 `core/tool_registry.py`（约 600 LOC）：注册器 / schema 生成 / cost 计费 / 调用 logging
- 把现有 `physics.py` 里的内部操作拆解暴露为测量/操控 tool（约 25-40 个 tool 跨 6 域，每个 30 LOC ≈ **1000 LOC**）
- 改 `vanilla_agent.py` → `tool_agent.py`（约 500 LOC，复制式重写）

### 1.5 LOC 估计汇总

| 模块 | 新增 LOC | 改动 LOC |
|---|---|---|
| γ/δ shift laws（6 域 × 6 shift） | ~1.5k | 0 |
| 守恒律 tracker | ~200 | 50 |
| Tool registry + cost | ~600 | 0 |
| Tool 实现（25-40 个） | ~1.2k | 0 |
| 双接口 agent（schema + code） | ~800 | 200 |
| 沙箱重写（subprocess + rlimit） | ~500 | 删 ~150 |
| Cross-scenario skill store（D5） | ~700 | 0 |
| 大世界 / 任务卡（D1） | ~600 | 0 |
| `propose_anomaly` 流程（D2） | ~300 | 100 |
| 评测（3 轴 + 雷达图 + 排名） | ~800 | evaluation.py 复用 |
| 编排 / runner | ~400 | run_master.py 改 200 |
| **合计** | **~7.6k** | **~700** |

加测试与配置，**保守估计 8-12k LOC 新增**。一个工程师 6 月 = ~120 工作日，**绝对可达**，但要砍范围。

---

## 2. 额外 sim 选型

### 2.1 结论：v1 不引入额外 sim backend

NewtonBench 12 个 native Python sim **已覆盖** v1 起步 6 域。引入 MuJoCo / Brax / Genesis 会带来：
- 安装复杂度 ↑（CUDA / EGL / 显存）
- counterfactual shift 困难（黑盒物理引擎，改不了内核）
- 评测可重现性下降

**核心论点**：我们的卖点是"agent 选工具 + 创造工具"，不是高保真物理。**朴素 sim 反而是优势**（agent 容易 verify 偏移），别陷进精度军备竞赛。

### 2.2 选型对比表（备查，v1.1 + 用）

| Backend | 力学 | 电磁 | 热 | 光 | Python | 可微 | 协议 | 评分 |
|---|---|---|---|---|---|---|---|---|
| **NewtonBench native** (v1) | ✓ | ✓ | ✓ | ✓ | native | ✗ | MIT | **首选** |
| MuJoCo 3.x | ✓✓ | ✗ | ✗ | ✗ | bindings | ✓(MJX) | Apache | v1.1 力学增强 |
| Brax | ✓✓ | ✗ | ✗ | ✗ | native (JAX) | ✓ | Apache | RL 友好；GPU 必需 |
| Genesis | ✓✓ | ~ | ✓(SPH) | ✗ | native | ✓ | Apache | 新且重，安装坑多 |
| Taichi | 自写 | 自写 | 自写 | 自写 | native | ✓ | MIT | 太低层 |
| SciPy ODE | ✓ | ✓ | ✓ | ✓ | native | ✗ | BSD | NewtonBench 已隐式用 |
| FEniCS | ~ | ~ | ✓✓(PDE) | ~ | bindings | ~ | LGPL | 装起来痛苦 |

**v1.1 增强推荐**：力学补 MuJoCo（多体接触场景），热 / 流体补 Taichi。**v1 不动**。

---

## 3. Tool pool 实现路径

### 3.1 Python 沙箱方案选择

| 方案 | 安全 | 性能 | 复杂度 | D5 兼容 | 推荐 |
|---|---|---|---|---|---|
| `exec(code, ns)`（NewtonBench 现状） | F | A | A | C | ✗ |
| RestrictedPython | C+ | A | B | B | ✗（白名单太严，numpy 受限）|
| Pyodide (wasm) | B+ | C | C | A | ✗（性能 + sim 调用难）|
| subprocess + resource limits (`prlimit`) | B | B+ | B+ | A | **✓ v1** |
| docker per-call | A | C | C | A | ✗（启停慢，>1s/call）|
| nsjail / firejail | A- | A- | C+ | A | v1.1 |

**v1 推荐**：subprocess + `prlimit --as=2G --cpu=10` + `seccomp` 黑名单 + read-only fs bind mount。新增 ~500 LOC，复用 stdlib 即可。安全等级 B 够用（agent 是 LLM 而非攻击者，主要防 OOM / 死循环 / 写外部）。

### 3.2 JSON schema tool 注册框架

**选 OpenAI tool calling spec（强制 JSON Schema draft-07 子集）**，因为：
1. 主流 LLM API（OpenAI / Anthropic / vLLM OpenAI-compat）都原生支持，无需自己写 prompt 模板。
2. LangChain `tool` 装饰器是基于这个 spec 的，可以无痛迁移到 LangChain 评测脚本。
3. 我们的 Python 装饰器同时生成 JSON schema 和 callable（约 80 LOC）：

```python
@register_tool(category="measurement", cost=1.0)
def measure_distance(obj_a: str, obj_b: str, precision: float = 0.01) -> float:
    """测量两物体距离, precision in meters."""
    ...
```

装饰器读 type hints + docstring → 自动出 JSON schema，注册进 `ToolRegistry`，并 wrap 一层 cost 计费 logger。

### 3.3 跨 scenario 持久化（D5）

**两套存储方案**：

**方案 A（推荐 v1）：JSON manifest + Python 源码文件 on disk**
- 每个 agent run 维护一个 `~/.physgym/skills/<run_id>/`
- 每个 skill 一份 `.py` 文件 + 一份 `meta.json`（cost stats、author scenario、test 通过率）
- 启动新 scenario 时 dynamic import 全部 skill
- 优点：可读、可手工 debug、git diff 友好
- 缺点：依赖文件系统状态

**方案 B（v1.1）：SQLite + AST blob**
- skill 存 AST hash + 源码 + metadata 到 SQLite
- 支持版本回滚和评测复现
- 但 v1 没必要

**关键工程风险**：
1. **命名冲突**：scenario 1 创造的 `measure_field` 和 scenario 2 系统提供的 `measure_field` 冲突 → 加 namespace `skills.<run>.<name>`
2. **bug 归因**：tool 抛异常时，要分清 agent 调用错 vs tool 实现错 → 在 wrapper 加 `traceback.extract_tb` 区分 frame
3. **scaling**：如果 agent 创 100 个 skill，dynamic import 全装入会爆栈 → 加 lazy import + LRU 缓存
4. **安全**：持久化 skill 文件 = 持久化攻击面 → 启动时重跑 AST 黑名单审计

> **报告团队**：D5 的工程复杂度是 D1-D7 中最高的。**强烈建议 v1 只做 within-scenario tool creation**（agent 当前 trial 内创建的 skill 可在后续 turn 用），**跨 scenario 持久化推到 v1.1**。这样 v1 paper 还是能讲"agent 创工具"故事，但工程量降 40%。

---

## 4. Eval pipeline 工程

### 4.1 复用 NewtonBench 现成组件

- **RMSLE**：`modules/common/evaluation.py:calculate_rmsle` 直接拿走
- **Symbolic equivalence**：`llm_symbolic_equivalence_judge`（LLM-as-judge）+ `extract_formula_from_function`（AST unparse 提公式）— 直接拿走
- **SymPy 等价**：NewtonBench **没用** SymPy 做 symbolic 检查（只用 LLM judge）。我们应该**补一层 SymPy `simplify(eq1 - eq2) == 0`** 作为 fast-path，省 judge LLM 调用费。预估 ~150 LOC。

### 4.2 信息论评分（EIG / 方案 3）工程落地

**推荐路径**：
- 不做 full Bayesian EIG（需要 likelihood 模型，对我们的 sim 不可行）
- 改用 **proxy EIG**：每次 agent 调 measurement tool 前后，agent 自报"我现在对哪个参数的置信区间是 [a,b]"，环境算 entropy 降。要求 agent 输出 `<belief>` tag。
- 评分 = `Σ ΔH(belief) / Σ tool_cost`
- 工程量 ~300 LOC（解析 belief tag + entropy 计算 + 鲁棒处理 malformed）

**风险**：belief tag 是 agent 自报，可被 gaming（假报高置信）→ 加一致性 check：最终 final_law 必须 fall in 最后 belief CI，否则 belief 评分清零。

### 4.3 3 轴评分（D7）落地

- **Discovery 轴**：复用 NewtonBench `exact_accuracy` + RMSLE
- **Efficiency 轴**：`total_cost / discovery_score`，cost = Σ tool cost weighted
- **Skill 轴**：(a) 创造的 tool 数; (b) tool 在后续 scenario 的复用率; (c) tool 通过 self-test 的比例
- 雷达图：`matplotlib.pyplot.polar`，~50 LOC
- 复合排名：先 z-score per axis，加权求和，权重作为标定级参数

---

## 5. 6 个月 milestone 路线图

### M1（2026-06）— Fork & baseline 重建
- Fork NewtonBench；本地 1×A100 vLLM 起 Qwen2.5-72B / Llama3-70B 服务（推理 only）
- 复现 NewtonBench 论文数据点（gravity easy + medium + hard，gpt-4o-mini baseline）
- 确认 12 个域里 6 个目标域数值稳定（写 stability 回归测）
- **交付**：reproducibility report (1 page) + CI 跑通 baseline trial < 2 min

### M2（2026-07）— γ shift + 守恒律 tracker
- R1（物理调研）落地：每域写 3 个 γ shift（基于对称性破缺）
- 实现 `conservation_tracker.py`，对每个 sim 跑能量/动量监控
- 跑 baseline agent（vanilla）vs γ shift 跨 3 难度，看分数下降曲线
- **交付**：γ shift v1.0 全 6 域可用 + 18 trial benchmark report

### M3（2026-08）— Tool pool + 双接口
- 沙箱重写（subprocess + prlimit）
- ToolRegistry + 25-40 个 tool 注册 + JSON schema 生成
- 双 agent 实现（`tool_agent_code` + `tool_agent_schema`）
- **交付**：tool pool v1 可用 + tool agent 跑通 6 域 easy

### M4（2026-09）— D1 大世界 + D2 anomaly 流程
- 拼装大世界：每个 scenario = 多个任务卡（known + hidden 混合）
- 实现 `propose_anomaly` 接口 + 评分
- 串通完整 episode：探索 → propose → characterize → final_law
- **交付**：v1 alpha 跑通 1 个 scenario 全流程 + 3 个 LLM baseline 比对

### M5（2026-10）— 评测协议 + 内部 ablation
- 实现 3 轴评分 + 复合排名 + 雷达图
- proxy-EIG belief tracking
- A1 ablation：scenario 顺序对 transfer 的影响
- code agent vs schema agent ablation
- **交付**：完整 eval pipeline + 3 个核心 ablation

### M6（2026-11）— Paper 实验 + 写作
- 8-12 个 LLM 评测（GPT-4o / 4o-mini / Claude / Qwen / Llama / Deepseek 等）
- 跨 6 域 × 3 难度 × 3 shift tier × 3 seed = 162 trials/agent × 8 agent ≈ 1300 trials
- 单 trial 约 $0.05 + 10s → 总 $65 + 4h 串行（并行 8 路 < 1h）
- Paper writing (NeurIPS 2027 submission targeted)
- **交付**：v1 paper draft + release v1 codebase + leaderboard

### 砍出 v1 的内容（→ v1.1）

| 项 | 原因 |
|---|---|
| **D5 跨 scenario 持久化** | 工程量 + 安全风险都最高；within-scenario tool 创造已够卖 |
| δ shift（守恒律偏移） | 物理调研最难，留 v1.1 paper |
| 光学域（m6, m10） | 对称性 shift 不直观 |
| 多 agent / RL 训练 | 用户明确说不做 |
| MuJoCo / Brax 集成 | 不必要的复杂度 |
| BoxingGym 风格 full Bayesian EIG | proxy 够用 |

---

## 6. 关键工程风险 top 5

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| 1 | **D5 沙箱安全 × 持久化的组合复杂度** | agent 跨 scenario 注入恶意 skill / 状态爆炸 | v1 砍到 within-scenario only；v1.1 上 nsjail |
| 2 | **LLM-as-judge 评分不稳定** | symbolic_accuracy 抖动 → 论文数据可疑 | 先 SymPy fast-path；judge 用 majority-vote 3 次；公布 judge prompt + 模型版本 |
| 3 | **API 费用失控** | 162 × 8 × 30 turns × 大模型 = $$$ | 用 vLLM 跑开源大模型（Qwen2.5-72B-Instruct）做主力；只对 GPT-4o / Claude 做 sample subset |
| 4 | **agent 调用 tool 时的 schema drift** | 不同 LLM 对 JSON schema 兼容度差 | 双接口（code+schema）让 schema-差的模型走 code；记录每个 model 的 schema 失败率作为 ablation |
| 5 | **NewtonBench 域复测发现数值 bug** | 部分域不可用，v1 范围被迫缩 | M1 首两周做完 stability regression，**预留 2 域 buffer**（共测 8 域，挑稳定的 6 域上 paper） |

---

## 7. 算力 & 预算

- **GPU**: 1 张 A100 80GB 跑 vLLM serve Qwen2.5-72B-Instruct (AWQ-INT4)，throughput ≈ 40 tok/s × 8 concurrent。**够用整个 v1**。
- **API**: 闭源模型评测预算 ~$2500（按 GPT-4o $5/M input、$15/M output 估）
- **磁盘**: ~50 GB 存 trial logs / skill artifacts
- **CI**: GitHub Actions free tier 跑 reproducibility 子集（1 trial/PR）

---

## 8. 给 team-lead 的红色警告

**强烈建议立即决策两件事**：

1. **D5 是否砍到 within-scenario only**：跨 scenario 持久化 skill library 是个独立 paper 价值的功能，强行塞 v1 会拖累整个时间表。建议**在 v1 paper 里讲清"skill creation"是 v1 已实现、"cross-scenario persistence"是 v1.1 路线**，反而能锚一个 follow-up paper。
2. **D6 的 δ shift 是否砍到 v1.1**：γ shift 已经够新颖（对称性破缺设计），δ（守恒律破缺）的物理调研工程量远大于 γ，建议 v1 paper 只做 β（baseline）+ γ，留 δ 做下一篇。

不砍的话 6 个月会延期到 9 个月以上，且质量风险显著。

---

**报告完。后续问题可继续问 eng-scout。**

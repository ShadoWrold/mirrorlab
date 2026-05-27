# MirrorLab v2 / Camera-Ready TODO

Sprint 1-4 通过审查暴露的、暂时不修但日后必须处理的设计问题。

## Sprint 4 后人工审查阶段补录

### TODO-1 (2026-05-27, γ-1-2 触发；属共性问题)

**问题**：所有 shift 的 `sampler` 只随机化物理参数（如 k₀, ξ, φ），**初始条件硬编码**（如 γ-1-2 永远从 x=0.1, y=0.05, v=(0,0) 出发）。

**为什么是问题**：
- 不同 seed 之间，trajectory 的多样性只来自参数变化，IC 固定 → 轨道形态单一化
- 对 ROT 破缺这种"看进动才明显"的 shift，固定 IC 可能让某些 seed 正好在对称轴上 → 关键信号丢失
- single-seed 评测下，IC 不变意味着我们其实只看到该 shift 的"一个切片"

**影响**：
- v1 paper 的 cliff plot 结论不变（5 model 都看到的是同一个 IC 切片）
- 但 calibration 的统计力受限（CAL-4 τ 校准应该对 IC 也分层）

**v2 修法**：
1. `sampler(seed)` 同时随机化 IC（围绕能量壳层 / 动量壳层等物理上 meaningful 的子流形）
2. 加 IC 的 dim_signature 记录
3. validator 更新到也检查 IC 安全性（不止参数）

**适用范围**：36 个 shift 全体（不只是 γ-1-2）。

---

### TODO-2 (2026-05-27, γ-1-2 触发；属共性 leak class)

**问题**：多个 shift 的 `_Sim.step()` 直接把 **shift 的 smoking-gun 量**作为 observable 返回给 agent，相当于明示 shift 机制。

**已识别清单**：

| Shift | step() 输出 | leak 性质 | 严重度 |
|---|---|---|---|
| δ-2-1 (gravity) | `G_eff` | 修改后的引力常数瞬时值 | 🔴 |
| δ-6-1 (rlc) | `L_eff(t)` | 时变电感的瞬时值 | 🔴 |
| γ-8-1 (wave) | `omega` | 各向异性色散下的频率 | 🔴 |
| γ-8-2 (wave) | `omega` | 振幅依赖波速下的频率 | 🔴 |
| γ-1-2 (hooke) | `L_z` | 破缺对称性 ROT 的 Noether 荷 | 🔴 |
| **γ-2-1 (gravity)** | **`L_z`** | **3D 重力下的角动量 z 分量（人工二审 2026-05-27）** | **🔴** |
| **δ-1-1 (hooke)** | **`E`** | **E-break shift 的能量被直接读出（人工二审 2026-05-27 升 🟡→🔴）** | **🔴** |
| **δ-3-1 (damped_ho)** | **`E`** | **同上** | **🔴** |

**🔴 vs 🟡 判定准则**（人工二审 2026-05-27 修订）：

leak 严重度不取决于 "agent 自己会不会想到测这个量"，而取决于 **暴露了什么 shift signature**：
- shift 修改的参数本身（G_eff、L_eff、ω 等）→ 🔴
- shift 破缺对称性的 Noether 荷（L_z、E 等）→ 🔴
- **反向检查**：和 baseline 该域的 step() 输出对比，**只在 shift 版本出现的 derived quantity** 都属 🔴 leak，因为存在本身就是"这个 scenario 不同"的明示

按此准则，δ-1-1 / δ-3-1 输出 E 而 baseline Hooke (1D) 不输出 E → 升 🔴。

**为什么是问题**：
- 🔴 类：直接漏了"shift 修改的参数本身"或"shift 破缺的 Noether 荷"，agent 不用思考就能锁定 shift 类型
- 🟡 类：E 是物理学家自然会想测的量，agent 自己也能想到去测；但**预先塞进 step() 输出**仍然省了 agent 一步"想到要测什么"的工作

**v2 修法**：
1. step() 输出**只返回 primitives**：(t, 位置, 速度, 力)。所有 derived quantities (E, L_z, ω, G_eff, ...) **从 step() 移除**
2. 这些量留在 `_Sim` 内部作为 telemetry，**scoring 时仍能拿到**（用于 ground-truth grid 计算）
3. agent 若需 derived quantity，必须**通过 `analyze` tool 自己算**（已有 `analyze.invariant_check` 可用）

**对 v1 paper 数据的影响**：
- δ-2-1、δ-6-1 这两 cell 的分数**不能解读为 agent 自主发现 shift** —— 它从 step() 直接读出来了
- v1 paper 应该在 §8 Limitations 加一句："5/36 shifts 的 step() 输出含 shift 的直接观测量，camera-ready 时会移除并重跑这些 cell"

**适用范围**：上述 7 个 shift。其余 29 个 shift 的 step() 输出已检查为纯 primitives。

---

### TODO-3 (2026-05-27, γ-2-1 触发；属共性问题)

**问题**：γ-2-1 的 sampler IC 用 `v_circ = √(G_DEFAULT · M / r0)`，但实际重力常数是 `G0 = G_DEFAULT × LogUniform(0.5, 2.0)`。导致 IC **不是真正的圆轨道** —— 当 G0 ≠ G_DEFAULT 时轨道椭圆。

**性质判定**：可能是 **intentional design**（引入轨道椭圆度增加 diversity，更有利 agent 检测进动），但**代码没注释说明意图**，看起来像 bug。

**v2 修法**：
- 选项 A：加注释 `# G_DEFAULT used intentionally for v_circ → slightly elliptical orbit, aids precession detection`
- 选项 B：改 `v_circ = √(G0 · M / r0)` 真圆轨道，靠 ξ 引入轨道偏离

**适用范围**：检查 4 个 gravity / coulomb 域是否有同类"采样常数 vs 实际常数"错位（γ-2-2、δ-2-1、γ-5-1、γ-5-2 等）。

---

### TODO-4 (2026-05-27, γ-2-1 触发；属共性问题)

**问题**：γ-2-1 中 `M ∈ [1e20, 1e24] kg`、`r0 = 1e7 m` 固定 → **轨道周期跨 4 个数量级**（~7 小时到 ~700 小时）。

**影响**：agent 调用 `measure.trajectory(t_window, sample_rate)` 时不知道系统自然时间尺度。如果查询时间 t 不匹配，可能只看到 0.01-0.04% 的轨道，**根本看不到 ROT 破缺导致的轨道进动**。

**v2 修法**：
- 选项 A：把 r0 也用 M 缩放（保持周期固定）
- 选项 B：暴露"自然时间尺度"作为初始可观测
- 选项 C：归一化时间（用 T_orbital 作为时间单位）

**适用范围**：所有"时间尺度依赖参数"的域（gravity、damped_ho、wave、kinetics、decay）—— 检查 r0 / x0 / L 是否随尺度参数缩放。

---

(后续待补录)

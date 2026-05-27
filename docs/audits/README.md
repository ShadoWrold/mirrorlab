# MirrorLab Shift Audits — Per-Law Deep Review

逐 shift 详细审查（人工 review 用）。每个 shift 一份 markdown，按 9 个维度统一：

1. **原始定律** —— 标准教科书形式 + 对称性结构
2. **怎么改的** —— 物理动机 + 数学形式 + 直观行为
3. **哪条对称性被破了** —— 数学验证（不只是 catalog 说啥就信啥）
4. **哪些对称性保住** —— 逐条验证
5. **代码 ↔ catalog 一致性** —— 逐行对照
6. **采样分布合理性** —— 范围 / 量纲 / 关键阈值
7. **安全约束 validator** —— 物理意义 + 是否 vacuous
8. **Agent 信息暴露 / 隐藏** —— prompt 泄露检查
9. **审查总结** —— PASS / 改进点

---

## 索引

### 域 1 — Hooke spring
- [γ-1-1 饱和非对称刚度（PAR break）](hooke_g_1_1.md) ✅
- [γ-1-2 2D 各向异性刚度（ROT break）](hooke_g_1_2.md)
- [δ-1-1 振幅条件阻尼（E break）](hooke_d_1_1.md)

### 域 2 — Newtonian gravity
- [γ-2-1 四极各向异性（ROT break）](gravity_g_2_1.md)
- [γ-2-2 Lorentzian range bump（SCALE break）](gravity_g_2_2.md)
- [δ-2-1 G(t) 调制（T-trans / E break）](gravity_d_2_1.md)

### 域 3 — Damped HO
- [γ-3-1 振幅记忆刚度（LIN break）](damped_ho_g_3_1.md)
- [γ-3-2 离共振参数泵浦（T-trans break）](damped_ho_g_3_2.md)
- [δ-3-1 振幅门控负阻尼（dissipation monotonicity break）](damped_ho_d_3_1.md)

### 域 4 — Pendulum
- [γ-4-1 (1−cos θ) 偏置（PAR break）](pendulum_g_4_1.md)
- [γ-4-2 潮汐梯度引力（S-trans break）](pendulum_g_4_2.md)
- [δ-4-1 g(t) 调制（T-trans / E break）](pendulum_d_4_1.md)

### 域 5 — Coulomb
- [γ-5-1 单轴各向异性（ROT break）](coulomb_g_5_1.md)
- [γ-5-2 饱和场非线性电动力学（LIN break）](coulomb_g_5_2.md)
- [δ-5-1 场门控电荷泄漏（Q break）](coulomb_d_5_1.md)

### 域 6 — RLC
- [γ-6-1 可饱和电感（LIN break）](rlc_g_6_1.md)
- [γ-6-2 非对称互感（LIN break）](rlc_g_6_2.md)
- [δ-6-1 参数电感（T-trans break）](rlc_d_6_1.md)

### 域 7 — Thermal (Fourier)
- [γ-7-1 各向异性热传导（ROT break）](thermal_g_7_1.md)
- [γ-7-2 非线性热导率（LIN break）](thermal_g_7_2.md)
- [δ-7-1 浮力梯度（T→T+c break）](thermal_d_7_1.md)

### 域 8 — Scalar wave
- [γ-8-1 各向异性色散（ROT break）](wave_g_8_1.md)
- [γ-8-2 振幅依赖波速（LIN break）](wave_g_8_2.md)
- [δ-8-1 频率门控耗散（dissipation break）](wave_d_8_1.md)

### 域 9 — Geometric optics (Snell)
- [γ-9-1 各向异性折射率（ROT break）](optics_g_9_1.md)
- [γ-9-2 介质交换非互易（reciprocity break）](optics_g_9_2.md)
- [δ-9-1 介质损耗（E break）](optics_d_9_1.md)

### 域 10 — Inviscid fluid (Bernoulli)
- [γ-10-1 修正 Bernoulli（LIN break）](fluid_g_10_1.md)
- [γ-10-2 高程依赖密度（S-trans break）](fluid_g_10_2.md)
- [δ-10-1 ζ 黏性（E break）](fluid_d_10_1.md)

### 域 11 — Reaction kinetics
- [γ-11-1 浓度依赖速率（LIN break）](kinetics_g_11_1.md)
- [γ-11-2 阶数修正（LIN break）](kinetics_g_11_2.md)
- [δ-11-1 反应中泄漏（mass break）](kinetics_d_11_1.md)

### 域 12 — Radioactive decay
- [γ-12-1 半衰期比例修正（LIN break）](decay_g_12_1.md)
- [γ-12-2 周期性衰变率（T-trans break）](decay_g_12_2.md)
- [δ-12-1 N 漏失（N break）](decay_d_12_1.md)

---

## 已知系统性观察（写一次）

这些是 v1 共性问题，camera-ready 应处理（不阻塞 paper draft）：

1. **IC 不随 seed 变**：大部分 shift 的 sampler 只随机化物理参数（k, η 等），初始条件硬编码。trajectory diversity 受限。
2. **Sampling 偏向均匀分布**：导致 single-seed 分数波动大（Sprint 1 在 γ-1-1 实测，η=0.29 时 S=0.78，η=0.6 时 S=0.32）。stratified sampling 可缓解。
3. **Validator 多为防御性**：对 sampler 来说几乎永远 vacuous，因为 sampler 设计在保守区。Validator 主要拦截"外部手动构造的 params"。

---

## 审查使用流程

按你方便的顺序读，每个文件独立。读到有疑问的地方：
- ✅ 物理 / 公式 / 代码层面同意 → 标 OK 继续
- 🟡 改进建议你也认同 → 记到 camera-ready TODO
- 🔴 发现 bug / 不同意 → 告诉我，我修

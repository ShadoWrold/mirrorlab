# δ-2-1: Gravity G(t) 调制 — 深度审查

> 域 2 / Newtonian gravity / δ-tier / shift_id = `delta_2_1`
> 代码：[`mirrorlab/shifts/gravity_d_2_1.py`](../../mirrorlab/shifts/gravity_d_2_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix: φ 锁 0，T-rev 保留）
> **人工二审 errata (2026-05-27)**：原 audit 已正确标 🔴 `G_eff` leak。补充：`step()` **同时**输出 `E(t)`，E 是用 G_eff 算的，**修 v2 时两个都要移除**。否则只去 G_eff，agent 仍能从 E drift 推断破缺。详见 [v2-todo TODO-2](../v2-todo.md)。

---

## 1. 原始定律：Newton 两体引力

$$F(r) = -\frac{G m_1 m_2}{r^2}$$

`G` 是物理常数（绝对常数，textbook）。

**对称性结构**：

| 对称性 | 验证 | 守恒量 |
|---|---|---|
| **T-trans** | `G` 是常数，V 不含 t | E |
| **T-rev** | F 无 ṙ | 可逆性 |
| **ROT** | 中心力 | L |
| **PAR** | 标准 | — |
| **GAL** | 标准 | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：cross-domain re-skin of **parametric pumping**（声学 / 谐振腔参数泵入），借到引力常数。**Dirac LNH（大数假设）**有 `G` 缓慢漂移的思想；这里用**有界正弦调制**而非线性漂移，仿真不发散。

**改法**：
$$G(t) = G_0\,[1 + \beta \cos(\omega_G t)]$$
$$F(r,t) = -\frac{G(t)\,m_1 m_2}{r^2}$$

**关键设计：`φ ≡ 0`**（R1-fix 后果）。
- 原 R1 用 `sin(ωt + φ)` 加 random `φ` ⇒ 时间不对 `t=0` 对称 ⇒ T-rev 也破 ⇒ dual break ✗
- R2-fix：用 `cos(ωt)` 且 `φ = 0` ⇒ `cos(−ωt) = cos(ωt)` ⇒ 时间偶 ⇒ T-rev 保留 ✓

`ω_G ≪ ω_orbit`（缓慢调制） ⇒ 每个轨道周期 `G` 几乎常数，但跨多周期累积漂移可观测。

---

## 3. 哪条对称性被破了？

**目标**：**只破 T-trans**（能量不再是 Noether 不变量）。

**T-trans 破缺**：方程含显式 `t`（通过 `G(t)`） ⇒ 不在 `t → t+c` 下不变。✓

**E 不守恒验证**（T-trans Noether-paired loss）：
$$\frac{dE}{dt} = \frac{\partial L}{\partial t} = -\frac{\partial V}{\partial t} = -\frac{m_1 m_2}{r}\,\dot G(t) = \frac{G_0 \beta \omega_G \sin(\omega_G t)\,m_1 m_2}{r}$$

generally `≠ 0` ⇒ E 振荡不守恒。✓

---

## 4. 哪些对称性必须保住？

### T-rev（关键 R2-fix）
- `t → −t`：`cos(ω_G·(−t)) = cos(ω_G t)` ⇒ `G(t)` 时间偶 ✓
- F 无 `ṙ` ⇒ ✓
- 方程整体在 `t → −t` 下不变（结合 `r → r, ṙ → −ṙ, r̈ → r̈`） ✓

### ROT
- F 仍沿 `r̂`（中心力），`G(t)` 是标量 ⇒ `τ = r × F = 0` ⇒ **L 守恒** ✓

### S-trans
- 仅依赖相对位置 ⇒ p 守恒 ✓

### PAR
- `r → −r`：`r² → r²`，`r̂ → −r̂` ⇒ `F → −F` ✓

---

## 5. 代码实现逐行核对

```python
def G_of_t(t, p):
    return p.G0 * (1.0 + p.beta * math.cos(p.omega_G * t))

def shifted_force(r, t, p):
    return -G_of_t(t, p) * p.M * p.m / (r * r)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `G(t) = G₀·(1 + β·cos(ω_G·t))` | `G(t) = G₀[1 + β cos(ω_G t)]` | ✓ |
| `F = −G(t)·M·m/r²` | catalog 同 | ✓ |
| `φ` 不出现 ⇒ 隐式 0 | R2-fix 关键 | ✓ |

**完全一致，R2-fix 实现正确。**

---

## 6. 采样分布合理性

```python
G0 = G_default * LogUniform(0.5, 2.0)
M = 10**Uniform(20, 24)
beta = Uniform(0.05, 0.3)
r0 = 1e7
omega_orbit = √(G·M/r₀³)
omega_G = omega_orbit * LogUniform(1e-4, 1e-2)   # 慢调制
T_sim = 2π / omega_orbit                          # 一个轨道周期
v0 = 0
```

- `β ∈ [0.05, 0.3]`：下界保 T-trans 可见；上界 0.3 ⇒ `G(t) ∈ [0.7G₀, 1.3G₀]` ⇒ 调制可观但不极端
- `ω_G / ω_orbit ∈ [1e-4, 1e-2]`：极慢 ⇒ 单个轨道内 `G` 几乎常数，但 sim 跨多周期累积
- T_sim 仅一个 orbit period — **🟡 可能太短**，跨 `ω_G` 周期需 `T ≥ 2π/ω_G ~ 100-10000 × T_orbit`

**🟡 critique**：`T_sim = T_orbit` 时 `ω_G·T_sim ≤ 0.01·2π ≈ 0.06`，G 几乎没动 ⇒ E drift 可能太小，agent 难观测。

---

## 7. 安全约束 validator

```python
if not (BETA_MIN <= p.beta <= BETA_MAX): return False
if p.G0 <= 0 or p.M <= 0 or p.m <= 0: return False
if p.omega_G <= 0: return False
if p.r0 <= 0: return False
if p.beta * p.omega_G * p.T_sim > 0.5: return False   # net G drift bounded
```

**核心约束**：`β · ω_G · T_sim ≤ 0.5`
- 物理含义：G 在 sim 窗口内净漂移不超过 50%；保证仿真不跑飞
- 现 `T_sim = T_orbit, β ≤ 0.3, ω_G·T_orbit ≤ 0.01·2π ≈ 0.06` ⇒ `β·ω_G·T_sim ≤ 0.018 ≪ 0.5` ✓ 大幅保守

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 引力径向场景，输出 `r, v, F, E, G_eff`
- step 输出含 `G_eff` ⇒ **直接暴露 G(t)**！

**🔴 严重信息泄漏**：`G_eff` 输出**直接给出修改后的 G**。agent 拟合 `G_eff(t) = G₀(1 + β·cos(ω_G·t))` 一步到位。

**Agent 看不到**：
- shift label
- `β, ω_G` 数值（虽然能从 `G_eff(t)` 直接拟合）

**Agent 必须自己发现**：
1. 由 `G_eff` 输出直接观察 G(t) 形状
2. 拟合 `G₀, β, ω_G`
3. 推断 broken T-trans

**Bonus probe**：`broken_symmetry: "T-trans"` (or "energy_conservation") +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | parametric pumping → G(t) |
| 公式数学正确 | ✅ | T-trans 破，E ≠ const 推导 |
| T-trans 真破 | ✅ | dE/dt ≠ 0 |
| T-rev 保留（R2-fix） | ✅ | cos(ωt) 时间偶 |
| ROT / S-trans / PAR / GAL 保留 | ✅ | 中心力 + 标量调制 |
| 代码 ↔ catalog 一致 | ✅ | 含 φ=0 R2-fix |
| 采样分布合理 | 🟡 | T_sim 太短，drift 可能不可观 |
| 数值安全 | ✅ | β·ω_G·T < 0.5 |
| 信息泄漏防御 | 🔴 | **G_eff 输出泄漏修改后的引力常数** |

**🟡/🔴 改进点**：
1. **必须修复**：`G_eff` 不应在 agent 可见的 `step()` 输出里 ⇒ 移到内部 telemetry 或只在 ground-truth 评分用
2. T_sim 应延长到至少 `T = 2π/ω_G` 量级，让 E drift 可观

---

**δ-2-1 verdict**：物理 / 数学**PASS**；R2-fix `φ=0` 实现正确；**信息泄漏 🔴 需修复**。

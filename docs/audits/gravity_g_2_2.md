# γ-2-2: Gravity Lorentzian range bump — 深度审查

> 域 2 / Newtonian gravity / γ-tier / shift_id = `gamma_2_2`
> 代码：[`mirrorlab/shifts/gravity_g_2_2.py`](../../mirrorlab/shifts/gravity_g_2_2.py)
> Catalog Round-2 状态：APPROVED
> **人工二审 errata (2026-05-27)**：
> - 🟡 1D radial sim + v0=0 径向落入 → 完全无轨道 → **看不到 Bertrand 破缺最自然的 fingerprint（进动）**。shift 命题（"破 SCALE"）与可观测物理错位（[v2-todo TODO-5](../v2-todo.md)）。
> - ✅ step() 输出干净，无 leak（仅 t / r / v / F primitives）。
> - 不在 Sprint 4 sweep 的 4-domain subset 内，v1 paper 数据不受影响。

---

## 1. 原始定律：Newton 两体引力

$$F(r) = -\frac{G m_1 m_2}{r^2}$$

**Bertrand 定理**：1D 中心力中只有 `F ∝ r`（线性 Hooke）和 `F ∝ 1/r²`（Newton）会让所有有界轨道**闭合**。两个 closure：scale-free + Bertrand closure。

**对称性结构**（关注本 shift 相关）：

| 对称性 | 验证 | 守恒量 |
|---|---|---|
| **SCALE / Bertrand closure** | `F ∝ 1/r²` 是唯一两种 closure 之一 | 闭合椭圆 |
| **ROT** | 中心力 | L |
| **T-trans** | autonomous | E |
| **PAR / T-rev / GAL** | 标准 | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：引入**内禀长度尺度** `r₀`，扰动闭合轨道但远场仍为 `1/r²`。借 fifth-force / Yukawa screening 思想，但用 Lorentzian envelope 而非指数。

**改法**：
$$F(r) = -\frac{G m_1 m_2}{r^2}\left[1 + \alpha\,\frac{r/r_0}{1 + (r/r_0)^2}\right]$$

定义 `u = r/r₀`，bump 函数 `α·u/(1+u²)`：
- `u → 0`：bump → 0，力 → `−Gm₁m₂/r²` ✓（小距离恢复 Newton）
- `u → ∞`：bump → `α/u → 0` ✓（远场恢复 Newton）
- `u = 1`：bump 峰值 `α/2`，最大修正约 50% × α

**关键**：在 `r ~ r₀` 范围内，力相对标准 Newton 有 O(α) 增强 ⇒ 轨道周期与 angular advance 不再匹配 ⇒ **轨道进动**（precession）⇒ Bertrand closure 破。

---

## 3. 哪条对称性被破了？

**目标**：**只破 SCALE / Bertrand**。

**SCALE 破缺验证**：在尺度变换 `r → λr` 下，标准 Newton `F → λ⁻² F`（齐次 -2 次）。修改后：
$$F(\lambda r) = -\frac{Gm_1m_2}{\lambda^2 r^2}\left[1 + \alpha\,\frac{\lambda r/r_0}{1 + (\lambda r/r_0)^2}\right]$$

bump 项**不齐次**于 `r`（含 `r₀`） ⇒ F 不再 scale-covariant。✓ SCALE 破。

**Bertrand 破缺**：bound orbit 的 apsidal angle Δφ（peri 到 apo 的角度变化）：
$$\Delta\phi = \int_{r_{min}}^{r_{max}} \frac{L/r^2}{\sqrt{2m(E-V_{eff})}}\,dr$$

Newton/Hooke 的 `Δφ = π/2` 总是。对修改后 V，Δφ 依赖 `E, L, α, r₀` ⇒ 一般 `≠ π/2` ⇒ **轨道不闭合**，每周进动 `2(2Δφ − π) ≠ 0`。✓

---

## 4. 哪些对称性必须保住？

### ROT
- 力沿 `r̂`（central force） ⇒ `τ = r × F = 0` ⇒ **L 严格守恒** ✓

### T-trans / E
- F 不含 `t` ⇒ autonomous
- F 仅依赖 `r`，是 1D 保守力（每个中心力都有 V(r) = −∫F dr）
- ⇒ E **严格守恒** ✓

### T-rev
- F 不含 `ṙ` ⇒ ✓

### PAR
- `r → −r`：`r²` 不变，`r/r₀` 在 1D 这里是径向（`r ≥ 0`），3D 中 `r̂ → −r̂` ⇒ `F → −F` ✓

### GAL
- 仅依赖相对距离 ✓

---

## 5. 代码实现逐行核对

```python
def shifted_force(r, p):
    u = r / p.r_scale
    bump = p.alpha * u / (1.0 + u * u)
    return -p.G * p.M * p.m / (r * r) * (1.0 + bump)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `u = r / r_scale` | `u = r/r₀` | ✓ |
| `bump = α·u/(1+u²)` | `α·(r/r₀)/(1+(r/r₀)²)` | ✓ |
| `F = −GMm/r²·(1+bump)` | catalog 同 | ✓ |

**完全一致。**

---

## 6. 采样分布合理性

```python
G = G_default * LogUniform(0.5, 2.0)
M = 10**Uniform(20, 24)
alpha = Uniform(0.05, 0.5)
r0_radius = 1e7
r_scale = 1e7 * LogUniform(0.1, 10.0)   # r₀ ~ 1e6 ~ 1e8
v0 = 0
```

- `α ∈ [0.05, 0.5]`：下界保进动可见；上界 0.5 ⇒ bump 峰值 0.25 ⇒ 仍单调吸引力
- `r₀` 跨 2 decade，相对 IC `r=1e7` 横跨 "近 / 准 / 远" 三种区域 ✓
- `v0 = 0` 径向落入 ⇒ 简化 1D 测试（但**注意**：本 sim 是 1D 径向方程，未做完整 2D 轨道 ⇒ 无法直接观测进动！）

**🟡 关键 critique**：sim 是 1D 径向，未实现 2D 轨道积分 ⇒ **无法直接观察轨道进动**（最直观的 SCALE 破缺标志）。agent 只能从 `F(r)` vs `1/r²` 偏离推断，比 2D 进动观测困难得多。

---

## 7. 安全约束 validator

```python
if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX): return False
if p.G <= 0 or p.M <= 0 or p.m <= 0: return False
if p.r_scale <= 0 or p.r0 <= 0: return False
if p.r0 < 1e-3 * p.r_scale: return False   # 防 r→0 奇点
```

- `r₀_initial ≥ 1e-3 · r_scale` ⇒ 防 r/r₀ 在 bump 函数附近过小同时也防径向落入碰撞
- baseline 1/r² 本身在 r→0 奇异，shift 不加剧 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 引力径向场景，输出 `r, v, F`
- 工具列表

**Agent 看不到**：
- shift label（"γ-2-2" / "Bertrand" / "fifth-force" 全藏）
- `r₀, α, G, M` 数值

**Agent 必须自己发现**：
1. 在某些 `r` 范围 `F(r) ≠ −GMm/r²`
2. 偏离呈 Lorentzian 单峰形（不是 Yukawa 指数尾）
3. 拟合 `r₀, α`

**🟡 信息不足**：1D 仿真无法观察进动 ⇒ agent 只能从 `F` 残差识别 bump ⇒ 难度比设计意图高。

**Bonus probe**：`broken_symmetry: "SCALE"` (or "Bertrand") +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | Lorentzian range bump，非 Yukawa |
| 公式数学正确 | ✅ | SCALE 破缺 + Bertrand 破缺推导对 |
| SCALE 真破 | ✅ | F 不齐次于 r |
| ROT / T-trans / E / T-rev / PAR / GAL 保留 | ✅ | 中心力保守 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | 🟡 | 1D 径向 sim 限制进动观测 |
| 数值安全 | ✅ | r₀ ≥ 1e-3·r_scale |
| 信息泄漏防御 | ✅ | shift 隐藏，但 sim 维度低 |

**🟡 改进点**：
1. **关键**：sim 应升级为 2D 轨道（解决 6-D ODE：`r, θ, ṙ, θ̇` 或 Cartesian），让 agent 能直接观察进动 — Bertrand 破缺的最自然 fingerprint
2. v2 加 `theta` 输出 + 角动量 `L` 输出

---

**γ-2-2 verdict**：物理 / 代码 / 设计**PASS**。注意 sim 维度限制了 SCALE break 的可观测性，camera-ready 应升 2D。

# δ-3-1: Damped HO 振幅门控负阻尼 — 深度审查

> 域 3 / Damped harmonic oscillator / δ-tier / shift_id = `delta_3_1`
> 代码：[`mirrorlab/shifts/damped_ho_d_3_1.py`](../../mirrorlab/shifts/damped_ho_d_3_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：标准 Damped HO

$$\ddot x + 2\gamma\dot x + \omega_0^2 x = 0$$

Baseline 中 `γ > 0` ⇒ 能量单调衰减、振幅指数衰减到 0。

**关心的不变性**：
- **能量单调耗散**：`dE/dt = −2γm·ẋ² ≤ 0`（baseline 严格成立）
- PAR、T-trans、LIN（详见上面 γ-3-1, γ-3-2）

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：cross-domain re-skin of **van der Pol oscillator**（自激振荡 / 极限环）。借 vdP "状态门控负阻尼" 思想，但用**分段线性包络** `(|x|/L − 1)` 而非 vdP 的 `(1 − x²)` 多项式 ⇒ 非 textbook。

**改法**：
$$\ddot x + 2\gamma\,\left(\frac{|x|}{L} - 1\right)\,\dot x + \omega_0^2 x = 0$$

**门控函数** `g(x) = |x|/L − 1`：
- `|x| < L`：`g < 0` ⇒ "负阻尼"（**反阻尼**） ⇒ 注入能量
- `|x| = L`：`g = 0` ⇒ 零阻尼
- `|x| > L`：`g > 0` ⇒ 标准阻尼 ⇒ 耗散

**直观行为**：
- 小振幅起步 ⇒ 反阻尼涨幅 ⇒ 直到 `|x|` 跨过 L
- 大振幅 ⇒ 阻尼耗散 ⇒ 缩回 L 附近
- 平衡 ⇒ **极限环** 振幅约 `2L`

---

## 3. 哪条对称性被破了？

**目标**：**破"能量单调耗散"** —— baseline 的可用 conservation-law analog。

**验证**：
$$\frac{dE}{dt} = m\ddot x\dot x + m\omega_0^2 x\dot x = \dot x(m\ddot x + m\omega_0^2 x) = \dot x\cdot[-2\gamma m(|x|/L-1)\dot x]$$
$$= -2\gamma m\,(|x|/L - 1)\,\dot x^2$$

符号取决于 `(|x|/L − 1)`：
- `|x| < L`：**dE/dt > 0** ⇒ 能量**增加**（反阻尼注入）
- `|x| > L`：dE/dt < 0 ⇒ 耗散

⇒ E 既不严格单调减、也不守恒，而是**渐近收敛到限制环上的振荡值**。✓ 单调耗散破。

按 Part A 惯例，T-rev 与 E loss bundled，**算一条 break**。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程系数（`γ, L, ω₀`）autonomous ⇒ ✓

### PAR
- `x → −x, ẋ → −ẋ`:
  - `(|x|/L − 1)` 不变（`|−x| = |x|`） ⇒ ✓
  - `(|x|/L − 1)·ẋ → (|x|/L − 1)·(−ẋ)` ⇒ 整体阻尼项反号
  - LHS 整体在 `x → −x` 下反号 ✓

### LIN-in-stiffness
- 弹性部分 `ω₀² x` 仍线性
- 阻尼非线性但是 baseline LIN 是对系统总响应而言；本 shift 已破单调耗散 ⇒ LIN 也"半破" 但符合 baseline 习惯 ✓

---

## 5. 代码实现逐行核对

```python
def shifted_law(x, v, p):
    gate = (abs(x) / p.L - 1.0)
    return -2.0 * p.gamma * gate * v - p.omega0**2 * x
```

| 代码 | catalog | 一致 |
|---|---|---|
| `gate = (\|x\|/L − 1)` | `(\|x\|/L − 1)` | ✓ |
| `ẍ = −2γ·gate·v − ω₀²·x` | catalog 同 | ✓ |

**完全一致。**

注：`|x|` 在 `x = 0` 处不可导 ⇒ scipy DOP853 在过零时可能精度下降，但 g(0) = −1 是有限非奇点，实践 OK。

---

## 6. 采样分布合理性

```python
omega0 = LogUniform(0.5, 10.0)
gamma = omega0 * LogUniform(0.01, 0.2)   # γ/ω₀ ∈ [0.01, 0.2]
L = LogUniform(0.1, 2.0)
x0 = 0.5 * L                              # IC 在 |x| < L 反阻尼区 ⇒ 振幅会涨
v0 = 0
```

- IC `|x₀| = 0.5L < L` ⇒ 起步在**反阻尼区** ⇒ 振幅自动激增到极限环
- `γ/ω₀ ∈ [0.01, 0.2]`：保 underdamped 振荡
- L ∈ [0.1, 2] m：极限环半径 ~ 2L ∈ [0.2, 4] m

**亮点**：IC 智能放在反阻尼区，**保证 agent 看见极限环现象**。

---

## 7. 安全约束 validator

```python
if not (OMEGA_MIN <= p.omega0 <= OMEGA_MAX): return False
if not (L_MIN <= p.L <= L_MAX): return False
if p.gamma <= 0 or p.m <= 0: return False
if not (0.01 <= p.gamma / p.omega0 <= 0.2): return False
```

**审查**：
- 无显式振幅 bound — 因为极限环天然有界 ~2L
- 总机械能上界 `~ ½m·ω₀²·(2L)² = 2mω₀²L²`，在采样范围内 ≤ `2·100·4 = 800 J` —— 大但有限 ✓

**🟡 critique**：无显式振幅 safety check —— 信任极限环自限。若 `γ` 过小或 IC 太极端，瞬态可能过冲；但当前范围安全。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- DampedHO 场景，输出 `x, v, E`
- **E 直接可见** ⇒ agent 能立刻看见 E 非单调

**Agent 看不到**：
- shift label / "vdP" / "limit cycle" 关键词
- `γ, L, ω₀` 数值

**Agent 必须自己发现**：
1. 振幅**不衰减**（与 textbook damped 矛盾） ⇒ 排除标准 damped HO
2. 渐近极限环 ⇒ van der Pol-type behavior
3. 推断门控阈值 `L` ≈ 极限环半径 / 2
4. 拟合 `γ, L`

**Bonus probe**：`broken_symmetry: "energy_monotone_dissipation"` (or "E") +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | vdP-modified（piecewise vs 多项式） |
| 公式数学正确 | ✅ | dE/dt 符号反转推导 |
| E 单调性真破 | ✅ | 反阻尼区 dE/dt > 0 |
| T-trans / PAR 保留 | ✅ | autonomous + g 偶 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | IC 智能放反阻尼区 |
| 数值安全 | ✅ | 极限环自限 |
| 信息泄漏防御 | 🟡 | E 输出给强 hint |

**🟡 改进点**：
1. `E` 在 step 输出 ⇒ agent 一眼看见 E 不单调 ⇒ 提示过强。考虑只输出 `x, v`
2. `|x|` 在 x=0 不可导 — DOP853 数值上可能 sub-optimal；可改 `√(x²+δ²) − δ` 平滑

---

**δ-3-1 verdict**：物理 / 代码 / 设计**全 PASS**。极限环现象明显，IC 智能。

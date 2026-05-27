# γ-4-1: Pendulum (1−cos θ) 偏置 — 深度审查

> 域 4 / Planar pendulum / γ-tier / shift_id = `gamma_4_1`
> 代码：[`mirrorlab/shifts/pendulum_g_4_1.py`](../../mirrorlab/shifts/pendulum_g_4_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix: `α(1−cos θ)` 替换原 `tanh` 错误形式）

---

## 1. 原始定律：理想平面摆

$$\ddot\theta + \frac{g}{L}\sin\theta = 0$$

势能（按 θ）：
$$V(\theta) = \frac{g}{L}(1 - \cos\theta) \quad\text{（量纲 [s⁻²]，常省略 m·L²/L 因子）}$$

**对称性结构**：

| 对称性 | 验证 | 守恒量 |
|---|---|---|
| **T-trans** | autonomous | E |
| **PAR** (`θ → −θ`) | sin 奇，方程在 `θ → −θ, θ̈ → −θ̈` 下不变 | — |
| **T-rev** | 无 θ̇ | 可逆性 |
| **垂直反射对称** | V(θ) = V(−θ) | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：cross-domain re-skin of **biased rotor potential**（分子物理"倾斜 washboard"，Josephson dynamics），在恢复力矩里加一个**偶函数**项，制造对称破缺。

**改法**（R1-fix 关键）：
$$\ddot\theta + \frac{g}{L}\sin\theta + \frac{g}{L}\alpha\,(1 - \cos\theta) = 0$$

势能：
$$V(\theta) = \frac{g}{L}(1 - \cos\theta) + \frac{g}{L}\alpha\,(\theta - \sin\theta)$$

（`d/dθ(θ − sin θ) = 1 − cos θ`）

**直观行为**：
- `θ = 0`：`(1−cos 0) = 0` ⇒ 平衡点不变 ✓
- `θ > 0`（顺时针偏）：额外 `+α·(1−cos θ)` 项 ⇒ 总恢复力**更大**
- `θ < 0`（逆时针偏）：`(1−cos θ)` 仍 > 0（偶函数！） ⇒ 额外项还是**正方向**恢复 ⇒ 与 sin θ < 0 的恢复方向**冲突** ⇒ 摆向负方向时被"推回正"
- ⇒ 摆动**不对称**，正向和负向角度幅度不同

**R1-fix 教训**：R1 原版用 `sin(θ − α·tanh(θ/θ₀))`，这是 `sin(奇函数)` = 奇函数 ⇒ 整个方程仍 PAR-invariant ⇒ **PAR 没破** ✗。R2 改成 `α(1−cos θ)`（**真正的偶函数**项）才真破 PAR ✓。

---

## 3. 哪条对称性被破了？

**目标**：**只破 PAR**（θ → −θ）。

**PAR 操作下方程**：
$$\theta \to -\theta: \quad \ddot{(-\theta)} + (g/L)\sin(-\theta) + (g/L)\alpha(1-\cos(-\theta))$$
$$= -\ddot\theta - (g/L)\sin\theta + (g/L)\alpha(1-\cos\theta)$$

对比原方程 ×(−1)：
$$-\ddot\theta - (g/L)\sin\theta - (g/L)\alpha(1-\cos\theta)$$

**两式之差**：`+2·(g/L)·α(1−cos θ)` ≠ 0（当 α ≠ 0 且 θ ≠ 0 时）。

⇒ 方程**不在 `θ → −θ` 下不变** ⇒ **PAR 真破** ✓

---

## 4. 哪些对称性必须保住？

### T-trans / E
- 方程系数 autonomous ⇒ ✓
- 势能 V(θ) 定义良好（两项都从 θ=0 起 well-defined）
- ⇒ E = `½(θ̇)²·L² + V(θ)·L²` 等价表达 **守恒** ✓

### T-rev
- 方程无 `θ̇` ⇒ ✓

### 平衡点稳定性（次要 check）
- `V'(0) = (g/L)·sin 0 + (g/L)·α·(1−cos 0) = 0` ✓ 平衡点仍在 θ=0
- `V''(0) = (g/L)·cos 0 + (g/L)·α·sin 0 = g/L > 0` ✓ 稳定
- ⇒ 小振幅线性化仍恢复标准摆 + α 修正

---

## 5. 代码实现逐行核对

```python
def shifted_law(theta, p):
    return -p.g_over_L * math.sin(theta) - p.g_over_L * p.alpha * (1.0 - math.cos(theta))
```

| 代码 | catalog | 一致 |
|---|---|---|
| `−(g/L)·sin(θ)` | `−(g/L)sin θ` | ✓ |
| `−(g/L)·α·(1 − cos(θ))` | `−(g/L)·α·(1−cos θ)` | ✓ |

**完全一致，R2-fix 实现正确。**

---

## 6. 采样分布合理性

```python
GL_MIN, GL_MAX = 1.0, 100.0           # g/L ~ LogUniform(1, 100) s⁻²
ALPHA_MIN, ALPHA_MAX = 0.05, 0.5      # α ~ Uniform(0.05, 0.5)
theta0 = 0.3 rad ≈ 17°                # IC
omega0 = 0.0
```

- `g/L ∈ [1, 100] s⁻²` ⇒ 周期 `T = 2π/√(g/L) ∈ [0.6, 6] s`
- `α ∈ [0.05, 0.5]`：下界保 PAR 破缺可见；上界 0.5 < 1 保平衡点附近稳定
- `θ₀ = 0.3` rad（17°）：足够小，不太接近 π/2 ⇒ 振荡而非翻越

---

## 7. 安全约束 validator

```python
if not (GL_MIN <= p.g_over_L <= GL_MAX): return False
if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX): return False
if p.alpha >= 1.0: return False           # 关键阈值
if abs(p.theta0) > math.pi / 2: return False
```

**审查**：
- `α < 1`：保 V(θ) 局部凸，平衡稳定（参考 catalog "α < 1 keeps the local linearization stable"）
- `|θ₀| < π/2`：保不翻越垂直顶
- 数值安全 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- Pendulum 场景，输出 `theta, omega`
- 工具列表

**Agent 看不到**：
- shift label / "biased rotor" / "Josephson" 关键词
- `g/L, α` 数值
- 无 V 或 E 直接输出 ✓

**Agent 必须自己发现**：
1. 摆向正负角度的最大幅度不同 (`θ_max⁺ ≠ |θ_max⁻|`)
2. 相图非对称 (左右半圆不对称)
3. 推断 EOM 含 PAR-breaking 项
4. 拟合 α

**Bonus probe**：`broken_symmetry: "PAR"` +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | biased rotor (Josephson) |
| 公式数学正确 | ✅ | (1−cos θ) 是真偶函数，PAR 实破 |
| PAR 真破 | ✅ | 差分 = 2(g/L)α(1−cos θ) ≠ 0 |
| T-trans / E / T-rev 保留 | ✅ | autonomous + 无 θ̇ |
| 平衡稳定 | ✅ | V'(0)=0, V''(0)=g/L>0 |
| 代码 ↔ catalog 一致 | ✅ | R2-fix 实现正确 |
| 采样分布合理 | ✅ | α < 1 守 |
| 数值安全 | ✅ | \|θ₀\|<π/2 防翻越 |
| 信息泄漏防御 | ✅ | 不暴露 V/E |

**🟡 改进点**：
1. IC 固定 θ₀=0.3 ⇒ seed 间多样性低；建议 IC 在 [-0.6, 0.6] 随机
2. 振幅 0.3 rad 较小 ⇒ (1−cos 0.3) ≈ 0.045 → α-项相对 sin 0.3 ≈ 0.295 大约只 15% × α，PAR 破缺幅度可能偏低

---

**γ-4-1 verdict**：物理 / 代码 / 设计**全 PASS**。R2-fix 把 R1 的"假 PAR 破"bug 改对了。

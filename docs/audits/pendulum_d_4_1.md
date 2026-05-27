# δ-4-1: Pendulum g(t) 调制 — 深度审查

> 域 4 / Planar pendulum / δ-tier / shift_id = `delta_4_1`
> 代码：[`mirrorlab/shifts/pendulum_d_4_1.py`](../../mirrorlab/shifts/pendulum_d_4_1.py)
> Catalog Round-2 状态：APPROVED（`φ ≡ 0` cos form correctly preserves T-rev）

---

## 1. 原始定律：理想平面摆

$$\ddot\theta + \frac{g}{L}\sin\theta = 0$$

`g` 是恒定 9.81 m/s²。**对称性**（关注）：

| 对称性 | 验证 | 守恒量 |
|---|---|---|
| **T-trans** | autonomous | E |
| **T-rev** | 无 θ̇ | 可逆性 |
| **PAR** | sin 奇 | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：**Kapitza-style** 垂直驱动摆 (parametric drive on `g`)，但故意停在**慢、远离 Mathieu 共振**的工作点（与 Kapitza 快振稳定不同）。

**改法**（R1-fix 已正确实现）：
$$\ddot\theta + \frac{g(t)}{L}\sin\theta = 0, \qquad g(t) = g_0\,[1 + \varepsilon\cos(\Omega t)]$$

**关键 `φ ≡ 0`**：用 `cos(Ωt)` 而非 `cos(Ωt+φ)` ⇒ 函数对 `t=0` 时间偶 ⇒ T-rev 保留。

`Ω` 采样区间 `[0.3, 1.7]·ω₀`，避开主参数共振 `2ω₀`。

---

## 3. 哪条对称性被破了？

**目标**：**只破 T-trans**。

**T-trans 破缺**：方程系数含显式 `t`（通过 `g(t)`） ⇒ ✗ T-trans 破。✓

**E 不守恒（Noether-paired）**：
$$\frac{dE}{dt} = -\frac{\partial V}{\partial t} = -\frac{\partial}{\partial t}\left[mL\cdot g(t)\cdot(1-\cos\theta)\right] = -mL\,\dot g(t)\,(1-\cos\theta)$$
$$= mL\,g_0\,\varepsilon\,\Omega\,\sin(\Omega t)\,(1-\cos\theta)$$
generally ≠ 0 ⇒ E 振荡。

---

## 4. 哪些对称性必须保住？

### T-rev（R2-fix 关键）
- `t → −t`：`cos(Ω·(−t)) = cos(Ωt)` ⇒ `g(t)` 时间偶 ✓
- 方程无 θ̇ ⇒ T-rev 保留 ✓

### PAR
- `θ → −θ`：sin θ 反号 ⇒ 方程整体反号 ⇒ 不变 ✓
- `g(t)` 不依赖 θ ⇒ 不影响 PAR ✓

---

## 5. 代码实现逐行核对

```python
def shifted_law(theta, t, p):
    factor = 1.0 + p.eps * math.cos(p.Omega * t)
    return -p.g0_over_L * factor * math.sin(theta)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `factor = 1 + ε·cos(Ω·t)` | `1 + ε cos(Ω t)` | ✓ |
| `θ̈ = −(g₀/L)·factor·sin(θ)` | catalog 同 | ✓ |
| `φ` 不出现 ⇒ 隐式 0 | R2-fix 关键 | ✓ |

**完全一致。**

---

## 6. 采样分布合理性

```python
g0_over_L = LogUniform(1, 100)
omega0 = √(g0_over_L)
Omega = omega0 * Uniform(0.3, 1.7)         # 避开 2ω₀ 主共振
# Sub-threshold Mathieu: ε ≤ 0.4·|Ω/(2ω₀) − 1|
bound = 0.4 * |Ω/(2ω₀) − 1|
eps = Uniform(0.05, min(0.3, 0.95·bound))
theta0 = 0.3, omega_init = 0
```

**亮点**：sampler 主动按 Mathieu sub-threshold 公式动态计算 `eps_hi`。

- `Ω ∈ [0.3, 1.7]·ω₀` ⇒ 避开 `2ω₀` 主参数共振
- 当 `Ω ≈ ω₀`（`Ω/(2ω₀) ≈ 0.5`）：`bound ≈ 0.4·0.5 = 0.2` ⇒ eps_hi ≈ 0.19 ⇒ ε 收紧
- 当 `Ω` 远离 `2ω₀`（e.g. `Ω = 0.3·ω₀`）：`bound ≈ 0.4·|0.15 − 1| = 0.34` ⇒ eps_hi ≈ 0.3 ⇒ 充分

**🟡 corner case**：`Ω = ω₀` ⇒ `bound ≈ 0.2`，刚好满足 EPS_MIN=0.05；当 `Ω` 太接近 `2ω₀`（e.g. `Ω/ω₀ = 1.7`，则 `Ω/(2ω₀) = 0.85`，`bound = 0.06` ⇒ eps_hi 几乎只能取 EPS_MIN）。sampler 的 fallback `max(eps_hi, EPS_MIN+1e-12)` 处理此 edge。

---

## 7. 安全约束 validator

```python
if not (EPS_MIN <= p.eps <= EPS_MAX): return False
if p.Omega <= 0: return False
omega_nat = √(p.g0_over_L)
if not (0.3 <= p.Omega/omega_nat <= 1.7): return False
bound = 0.4 * abs(p.Omega/(2*omega_nat) - 1.0)
if p.eps > bound: return False                  # 关键 Mathieu sub-threshold
if abs(p.theta0) > π/2: return False
```

**核心**：`ε ≤ 0.4·|Ω/(2ω₀) − 1|`
- 主参数共振阈值（小角线性化分析）：`ε_critical ~ 2|Ω−2ω₀|/ω₀ + 阻尼项`（无阻尼摆下边界）
- catalog 的 `0.4·|...|` 系数留 ~2× 安全余量

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- Pendulum 场景，输出 `theta, omega`
- 工具列表

**Agent 看不到**：
- shift label / "Kapitza" / "parametric" / "Mathieu" 关键词
- `g₀, ε, Ω` 数值
- g(t) 不直接输出 ✓（与 δ-2-1 G_eff 泄漏对比，δ-4-1 没犯同款错）

**Agent 必须自己发现**：
1. 振幅有缓慢拍频调制（参数泵浦签名）
2. 频谱含 `ω₀ ± Ω` 边带
3. 推断 g(t) 调制
4. 拟合 `ε, Ω`

**Bonus probe**：`broken_symmetry: "T-trans"` +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | Kapitza-style slow off-resonant |
| 公式数学正确 | ✅ | dE/dt ≠ 0，T-rev 保留 |
| T-trans 真破 | ✅ | RHS 显式 t |
| T-rev 保留（R2-fix） | ✅ | cos(Ωt) 偶 |
| PAR 保留 | ✅ | g(t) 与 θ 无关 |
| 代码 ↔ catalog 一致 | ✅ | φ=0 实现正确 |
| 采样分布合理 | ✅ | sampler 动态 sub-threshold |
| 数值安全 | ✅ | Mathieu 阈值 |
| 信息泄漏防御 | ✅ | g(t) 不输出（比 δ-2-1 好） |

**🟡 改进点**：
1. corner case `Ω` 极接近 `2ω₀` ⇒ ε 范围窄 ⇒ 部分 seed 可能 PAR-break 太弱可见性差；考虑 reject `Ω ∈ [1.6, 1.7]·ω₀` 或类似
2. T_sim 长度未约束 — sub-threshold 长时间也会缓慢漂移

---

**δ-4-1 verdict**：物理 / 代码 / 设计**全 PASS**。`φ=0` R2-fix 正确，比 δ-2-1 信息隔离做得好。

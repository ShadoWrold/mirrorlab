# γ-4-2: Pendulum 潮汐梯度引力 — 深度审查

> 域 4 / Planar pendulum / γ-tier / shift_id = `gamma_4_2`
> 代码：[`mirrorlab/shifts/pendulum_g_4_2.py`](../../mirrorlab/shifts/pendulum_g_4_2.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：理想平面摆

$$\ddot\theta + (g/L)\sin\theta = 0$$

**关心的不变性**：

| 对称性 | 验证 |
|---|---|
| **垂直 S-trans** | g 是常数，与高度无关 ⇒ 平移系统不影响 |
| **T-trans** | autonomous |
| **PAR** | θ → −θ 不变 |
| **T-rev** | 无 θ̇ |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：cross-domain re-skin of **tidal gradient**（天体力学中潮汐梯度），搬到桌面摆 ⇒ 有效重力随**摆球高度**变化。

**改法**：
$$\ddot\theta + \frac{g_0}{L}\,\left[1 - \alpha\,\frac{L(1-\cos\theta)}{H}\right]\sin\theta = 0$$

其中 `L(1−cos θ)` = 摆球相对最低点的**高度**（geometry）；`H` 是潮汐梯度的特征尺度。

**等价表达**：`g_eff(h) = g₀·[1 − α·h/H]`，其中 `h = L(1−cos θ)`。

**直观行为**：
- `θ = 0`：高度 0 ⇒ `g_eff = g₀` ⇒ 平衡点不变 ✓
- 大角度（高位置）：`g_eff < g₀` ⇒ 摆**变软** ⇒ 大振幅周期延长
- `α > 0`：高处引力弱化（与地球潮汐梯度同号 — 越高 g 越小）

---

## 3. 哪条对称性被破了？

**目标**：**只破垂直 S-trans**（垂直平移不变性）。

**S-trans 破缺验证**：将摆顶点位置整体上移 `Δh`，则任意 θ 对应的高度从 `L(1−cos θ)` 变成 `L(1−cos θ) + Δh`。EOM 变为：
$$\ddot\theta + \frac{g_0}{L}\left[1 - \alpha\frac{L(1-\cos\theta) + \Delta h}{H}\right]\sin\theta$$

含 `Δh` 项 ⇒ EOM 依赖整体高度 ⇒ **不在垂直平移下不变** ✓

（baseline 中 `g` 是常数，平移摆 ⇒ EOM 完全不变；本 shift 让 EOM 知道"绝对高度"）

---

## 4. 哪些对称性必须保住？

### T-trans / E
- 方程系数 autonomous ⇒ ✓
- 势能（catalog）：`V(θ) = mg₀L(1−cos θ) − ½ m g₀ α L²/H · (1−cos θ)²`
- 两项都从 θ=0 起 well-defined ⇒ E **守恒** ✓

### PAR
- `θ → −θ`：`(1−cos θ)` 不变（偶），`sin θ` 反号
- ⇒ `ẍ + (g₀/L)·[1 − α·(...)/H]·sin θ` 中括号项不变，sin θ 反号
- 方程整体反号 ⇒ 方程**不变** ✓

### T-rev
- 无 θ̇ ⇒ ✓

---

## 5. 代码实现逐行核对

```python
def shifted_law(theta, p):
    height = p.L * (1.0 - math.cos(theta))
    g_eff = p.g0_over_L * (1.0 - p.alpha * height / p.H)
    return -g_eff * math.sin(theta)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `h = L(1 − cos θ)` | `L(1−cos θ)` | ✓ |
| `g_eff = g₀·(1 − α·h/H)` | catalog 同 | ✓ |
| `θ̈ = −g_eff·sin θ` | catalog 同 | ✓ |

**完全一致。**

---

## 6. 采样分布合理性

```python
GL_MIN, GL_MAX = 1.0, 100.0
ALPHA_MIN, ALPHA_MAX = 0.02, 0.3
L = LogUniform(0.1, 2.0)
H_min_safe = max(0.5 * L, 4.0 * alpha * L)    # 智能下界
H = H_min_safe * LogUniform(1.0, 50.0)
theta0 = 0.3, omega0 = 0
```

**亮点**：sampler 主动计算 `H_min_safe = max(0.5L, 4αL)` 保证 safety bound `αL/H < 0.5` 总成立。

- `α ∈ [0.02, 0.3]` ⇒ 引力修正最大 30%
- `L ∈ [0.1, 2] m` 桌面尺度
- `H` 跨度大 ⇒ 强 vs 弱潮汐梯度

---

## 7. 安全约束 validator

```python
if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX): return False
if p.L <= 0 or p.H <= 0: return False
if p.alpha * p.L / p.H >= 0.5: return False     # 关键
if abs(p.theta0) > math.pi / 2: return False
```

**核心约束**：`α·L/H < 0.5`
- 在 `|θ| ≤ π/2` 内，`h_max = L(1 − cos(π/2)) = L`
- `α·h/H ≤ α·L/H < 0.5` ⇒ `g_eff = g₀·(1 − α·h/H) > 0.5·g₀ > 0` ✓ 引力始终正向

**sampler 已守 `H ≥ 4αL` ⇒ `α·L/H ≤ 0.25` ⇒ validator 阈值 0.5 是 2× 冗余** ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- Pendulum 场景，输出 `theta, omega`

**Agent 看不到**：
- shift label / "tidal" 关键词
- `g₀, α, L, H` 数值
- 高度概念不显式（agent 须自己想到）

**Agent 必须自己发现**：
1. 大振幅周期与小振幅周期偏差大于 standard pendulum 非线性预期
2. 偏差方向：大振幅周期**更长**（g_eff 变小）
3. 推断 g 依赖于位置 / 高度
4. 拟合 `α, H`

**Bonus probe**：`broken_symmetry: "S-trans"` (or "vertical_translation") +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | tidal gradient 跨域 |
| 公式数学正确 | ✅ | S-trans 破，含 Δh 验证 |
| S-trans 真破 | ✅ | EOM 显式依赖绝对高度 |
| T-trans / E / PAR / T-rev 保留 | ✅ | 势能 well-defined，autonomous |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | sampler 智能 H_min_safe |
| 数值安全 | ✅ | g_eff > 0.5 g₀ |
| 信息泄漏防御 | ✅ | 不输出 g_eff、不暴露 h |

**🟡 改进点**：
1. IC 固定 ⇒ seed 间仅在 `α, L, H, g₀` 上变化
2. agent 难度较高 — S-trans 破缺需"想到 g 与高度相关"，是一个抽象 leap；可考虑提示

---

**γ-4-2 verdict**：物理 / 代码 / 设计**全 PASS**。sampler 智能约束亮眼。

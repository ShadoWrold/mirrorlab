# γ-3-1: Damped HO 振幅记忆刚度 — 深度审查

> 域 3 / Damped harmonic oscillator / γ-tier / shift_id = `gamma_3_1`
> 代码：[`mirrorlab/shifts/damped_ho_g_3_1.py`](../../mirrorlab/shifts/damped_ho_g_3_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：标准 Damped HO

$$\ddot x + 2\gamma\dot x + \omega_0^2 x = 0$$

**注意 baseline 特殊性**：Damped HO 在 baseline 层就已经**破了 T-rev 和 E**（因 `2γẋ` 阻尼项）。所以 T-rev 和 E 不是 γ-tier 的合法 target —— 剩下的可破对称性只有：

| 对称性 | baseline 验证 | 守恒量 |
|---|---|---|
| **T-trans** | autonomous（系数不含 t） | — |
| **PAR** | x → −x ⇒ ẍ → −ẍ, ẋ → −ẋ ⇒ 方程不变 | — |
| **LIN** | 方程在 `x → ax` 下不变 | 叠加原理 |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：cross-domain re-skin of **nonlinear acoustics / hysteretic granular media**（颗粒介质的滞后刚度）。刚度不再是常数，而**记忆最近时间窗口内的振幅平方均值** `⟨x²⟩_τ`。

**改法**：
$$\ddot x + 2\gamma\dot x + \omega_0^2\left[1 + \kappa\,\frac{\langle x^2\rangle_\tau}{x_{\text{ref}}^2}\right]x = 0$$

其中：
$$\langle x^2\rangle_\tau = \frac{1}{\tau}\int_{t-\tau}^{t} x^2(s)\,ds$$

**有效频率**：`ω²_eff(t) = ω₀²[1 + κ·⟨x²⟩_τ/x_ref²]`

**直观行为**：
- 系统刚启动、振幅小：`⟨x²⟩ ≈ 0` ⇒ 标准 ω₀
- 振幅持续大：`⟨x²⟩` 增长 ⇒ `ω_eff` 增大 ⇒ 周期缩短 ⇒ "硬化"
- 衰减后：`⟨x²⟩` 跟随衰减 ⇒ `ω_eff` 回到 ω₀

**与 Duffing 的区别**：Duffing 用瞬时 `x³` 项；这里用**时间窗口均值** `⟨x²⟩_τ` ⇒ **历史依赖** ⇒ 非局域 ⇒ 非标准。

---

## 3. 哪条对称性被破了？

**目标**：**只破 LIN**（线性叠加）。

**LIN 破缺验证**：考虑两个解 `x₁(t), x₂(t)`，叠加 `x = x₁ + x₂`：
$$\langle (x_1+x_2)^2\rangle_\tau = \langle x_1^2\rangle_\tau + 2\langle x_1 x_2\rangle_\tau + \langle x_2^2\rangle_\tau \ne \langle x_1^2\rangle_\tau + \langle x_2^2\rangle_\tau$$

`ω²_eff` 对叠加输入**非线性响应** ⇒ `ẍ = −(ω₀²+κ·⟨(x₁+x₂)²⟩/x_ref²)·(x₁+x₂)` 不等于两个单独解的方程之和。✓ LIN 真破。

或更简单：scale 输入 `x → ax`：
$$\langle (ax)^2\rangle_\tau = a^2\langle x^2\rangle_\tau \quad\Rightarrow\quad \omega^2_{eff}(ax) \ne \omega^2_{eff}(x)$$
当 κ ≠ 0 ⇒ 方程不在 `x → ax` 下尺度协变 ⇒ LIN 破。✓

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程系数（除 `⟨x²⟩_τ` 含历史 t-依赖外）autonomous
- `⟨x²⟩_τ` 通过 **sliding window** 定义 ⇒ 时间平移整个轨迹 `x(t) → x(t-t₀)`，窗口跟随 ⇒ `⟨x²⟩_τ(t) → ⟨x²⟩_τ(t-t₀)` ⇒ 方程形式不变 ✓

### PAR
- `x → −x`：`⟨x²⟩` 是偶函数 ⇒ 不变 ⇒ `ω²_eff` 不变
- 方程线性部分 `ẍ + 2γẋ + ω²_eff·x` 在 `x → −x, ẋ → −ẋ, ẍ → −ẍ` 下整体反号 ⇒ 方程不变 ✓

### T-rev / E
- baseline 已破，不算 γ-3-1 target ⇒ N/A

---

## 5. 代码实现逐行核对

```python
def shifted_law(x, v, x2_mean, p):
    omega2_eff = p.omega0**2 * (1.0 + p.kappa * x2_mean / p.x_ref**2)
    return -2.0 * p.gamma * v - omega2_eff * x
```

`⟨x²⟩_τ` 用 sliding `deque` 实现（窗口长度 `n_hist = ceil(τ/dt)`）：

```python
n_hist = max(2, int(math.ceil(p.tau / dt)))
self._hist: Deque[float] = deque([p.x0 * p.x0] * n_hist, maxlen=n_hist)
...
self._hist.append(self._x * self._x)
def _x2_mean(self): return sum(self._hist) / len(self._hist)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `ω²_eff = ω₀²·(1 + κ·⟨x²⟩/x_ref²)` | catalog 同 | ✓ |
| `ẍ = −2γẋ − ω²_eff·x` | catalog 同 | ✓ |
| `⟨x²⟩_τ` 滑窗 deque | catalog `(1/τ)∫_{t-τ}^t x²ds` 离散化 | ✓ |
| 历史初始化为 `x₀²` | 等价 t<0 假设 x=x₀ const | ✓（合理简化） |

**完全一致。** 注意用了 **手写 RK4** 而非 scipy（因为带历史状态的 ODE 不能简单交给 scipy `solve_ivp`）。

---

## 6. 采样分布合理性

```python
omega0 = LogUniform(0.5, 10.0)      # rad/s
gamma = omega0 * LogUniform(0.01, 0.3)   # γ/ω₀ ∈ [0.01, 0.3] 欠阻尼
kappa = Uniform(0.05, 0.5)
tau = Uniform(0.5, 5.0) / omega0    # 窗口约 0.5-5 个周期
x_ref = LogUniform(0.1, 2.0)        # m
x0 = 0.1, v0 = 0
```

- `γ/ω₀ ∈ [0.01, 0.3]` ⇒ underdamped，保多周期振荡可观
- `κ ∈ [0.05, 0.5]` ⇒ ω_eff 最大变化 ~50%
- `τ` 与周期同量级 ⇒ 窗口"看见"几个完整周期 ⇒ ⟨x²⟩ 是 meaningful
- `x_ref ∈ [0.1, 2]`，相对 `x₀=0.1` ⇒ `x²/x_ref²` 起步在 [0.0025, 1] 之间 ⇒ 初始 κ-项非零但有界

---

## 7. 安全约束 validator

```python
if not (OMEGA_MIN <= p.omega0 <= OMEGA_MAX): return False
if not (KAPPA_MIN <= p.kappa <= KAPPA_MAX): return False
if not (XREF_MIN <= p.x_ref <= XREF_MAX): return False
if p.kappa > 0.6: return False                # 关键
if p.gamma <= 0 or p.tau <= 0 or p.m <= 0: return False
if p.gamma / p.omega0 < 0.01 or p.gamma / p.omega0 > 0.3: return False
```

- `κ ≤ 0.6`：保 `ω²_eff > 0`（即使 ⟨x²⟩/x_ref² 接近 1，1 + 0.6·1 = 1.6 仍正）
- 严格欠阻尼带

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- DampedHO 场景，输出 `x, v`（无 F 直接输出 — 因为有效力依赖历史）

**Agent 看不到**：
- shift label / "amplitude memory" / "Duffing-like" 关键词
- `κ, τ, x_ref, ω₀, γ` 数值
- ⟨x²⟩_τ 历史（不在 step 输出中）

**Agent 必须自己发现**：
1. 周期不稳定：大振幅时周期短，小振幅时周期 → 2π/ω₀
2. 系统**非线性**（叠加不成立）
3. 推断 ω_eff 依赖历史振幅 → 拟合 `κ, τ, x_ref`

**Bonus probe**：`broken_symmetry: "LIN"` +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 颗粒介质 hysteresis，非 Duffing |
| 公式数学正确 | ✅ | LIN 破缺由 ⟨(x₁+x₂)²⟩ ≠ ⟨x₁²⟩+⟨x₂²⟩ 验证 |
| LIN 真破 | ✅ | scale 不协变 |
| T-trans 保留（sliding window） | ✅ | 窗口跟随 t 平移 |
| PAR 保留 | ✅ | x² 偶 |
| 代码 ↔ catalog 一致 | ✅ | 含历史 deque 实现 |
| 采样分布合理 | ✅ | 欠阻尼 + κ ≤ 0.6 |
| 数值安全 | ✅ | ω²_eff > 0 始终 |
| 信息泄漏防御 | ✅ | 不输出 F、不输出 ⟨x²⟩ |

**🟡 改进点**：
1. dt=1e-3 固定，未做 step-size adaptive；高 ω₀ 时可能精度不足，建议 `dt = min(1e-3, 0.01/ω₀)`
2. agent 难度可能偏高（无 F 输出 + 隐藏历史）⇒ 注意 difficulty calibration

---

**γ-3-1 verdict**：物理 / 代码 / 设计**全 PASS**。手写 RK4 是历史依赖 ODE 的正确选择。

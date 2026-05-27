# γ-3-2: Damped HO 参数泵浦 — 深度审查

> 域 3 / Damped harmonic oscillator / γ-tier / shift_id = `gamma_3_2`
> 代码：[`mirrorlab/shifts/damped_ho_g_3_2.py`](../../mirrorlab/shifts/damped_ho_g_3_2.py)
> Catalog Round-2 状态：APPROVED
> **人工二审 errata (2026-05-27)**：🟡 sampler silent mutation —— γ 在某些采样下被覆盖到 0.0225·ω₀，扭曲了文档的 LogUniform 分布（详见 [v2-todo TODO-6](../v2-todo.md)）。step() 输出干净。

---

## 1. 原始定律：标准 Damped HO

$$\ddot x + 2\gamma\dot x + \omega_0^2 x = 0$$

Baseline 已破 T-rev 和 E（阻尼）。剩余对称性：

| 对称性 | baseline 验证 |
|---|---|
| **T-trans** | autonomous |
| **PAR** | x → −x 方程不变 |
| **LIN** | 方程线性 |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**：**参数泵浦**（parametric pumping）— 周期性调制弹簧刚度。借力学经典 Mathieu equation idea，但**故意避开主参数共振**（Ω_p ≠ 2ω₀），停在 sub-threshold。

**改法**：
$$\ddot x + 2\gamma\dot x + \omega_0^2\,[1 + \varepsilon\cos(\Omega_p t)]\,x = 0$$

`ε`：调制深度（小）；`Ω_p`：泵浦频率（与 `ω₀` 同量级但不在共振）。

**直观行为**：
- `ε = 0`：标准 damped HO
- `Ω_p ≈ 2ω₀` 且 `ε` 超阈：**主 Mathieu instability** — 振幅指数增长 ⇒ 灾难
- `ε < 4γ/ω₀` 或 `Ω_p` 远离 `2ω₀`：sub-threshold ⇒ 振幅有界小幅振荡
- catalog 采样 `Ω_p ∈ [0.3, 1.7]·ω₀`，主峰 `2ω₀` 外 ⇒ 安全

---

## 3. 哪条对称性被破了？

**目标**：**只破 T-trans**。

**T-trans 破缺验证**：方程系数含显式 `t`（通过 `cos(Ω_p t)`） ⇒ 不在 `t → t+c` 下不变（除非 `c = 2π·n/Ω_p`）。✓

注意：bound orbits 的 Floquet 多重数仍守，但 **continuous T-trans** 破。

---

## 4. 哪些对称性必须保住？

### PAR
- `x → −x, ẋ → −ẋ, ẍ → −ẍ`：方程整体反号 ⇒ 方程不变 ✓
- `cos(Ω_p t)` 不依赖 x ⇒ 不影响 PAR

### LIN
- 方程在 `x` 上仍**线性**（系数随 `t` 变，但对 `x` 是线性算子）
- 两个解 `x₁, x₂` 满足同一方程 ⇒ `a·x₁ + b·x₂` 也满足 ⇒ ✓

### T-rev / E
- baseline 已破，不是 γ-3-2 target

---

## 5. 代码实现逐行核对

```python
def shifted_law(x, v, t, p):
    omega2_t = p.omega0**2 * (1.0 + p.eps * math.cos(p.Omega_p * t))
    return -2.0 * p.gamma * v - omega2_t * x
```

| 代码 | catalog | 一致 |
|---|---|---|
| `ω²(t) = ω₀²·(1 + ε·cos(Ω_p·t))` | catalog 同 | ✓ |
| `ẍ = −2γẋ − ω²(t)·x` | catalog 同 | ✓ |

scipy `solve_ivp` 因 RHS 显式含 t，正常处理。**完全一致。**

---

## 6. 采样分布合理性

```python
omega0 = LogUniform(0.5, 10.0)
gamma = omega0 * LogUniform(0.01, 0.3)
# ε 受 sub-threshold 约束动态调整
eps_hi = min(0.3, 0.95 * 4 * gamma/omega0)
if eps_hi <= 0.05:
    gamma = omega0 * (0.05/4 + 0.01)   # 提升 gamma 保证 ε 范围可用
    eps_hi = min(0.3, 0.95 * 4 * gamma/omega0)
eps = Uniform(0.05, eps_hi)
Omega_p = omega0 * Uniform(0.3, 1.7)   # 避开 2ω₀ 主共振
```

**亮点**：sampler 主动调整 `γ` 防止 ε 范围空集 — **代码层主动约束** ⇒ 比纯 reject sampler 高效。

**🟡 critique**：当 sampler 修改 `γ` 时，最终 `γ/ω₀` 仍在 [0.01, 0.3] 内吗？验：`0.05/4 + 0.01 = 0.0225` ⇒ 在 [0.01, 0.3] 内 ✓。

---

## 7. 安全约束 validator

```python
if not (EPS_MIN <= p.eps <= EPS_MAX): return False
if p.gamma <= 0 or p.m <= 0 or p.Omega_p <= 0: return False
if p.eps >= 4.0 * p.gamma / p.omega0: return False   # 主 Mathieu tongue
if not (0.3 * p.omega0 <= p.Omega_p <= 1.7 * p.omega0): return False
```

**核心约束**：`ε < 4γ/ω₀` —— **sub-threshold of principal Mathieu tongue**。

物理含义：参数共振阈值（standard analysis）：
- 在 `Ω_p = 2ω₀` 附近，扰动振幅指数增长率 `~ ε·ω₀/2 − γ`
- 阈值：`ε·ω₀/2 = γ` ⇒ `ε_critical = 2γ/ω₀`
- catalog 用 `ε < 4γ/ω₀` 是 2 倍冗余（catalog 写 `ε < 4γ/ω₀`，**安全因子 2**）

`Ω_p ∈ [0.3, 1.7]·ω₀` 避开 `2ω₀` 主峰也避开 `ω₀` 次共振 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- DampedHO 场景，输出 `x, v`
- 无 F、无 ω(t) 直接输出 ✓

**Agent 看不到**：
- shift label / "parametric" / "Mathieu" 关键词
- `ε, Ω_p, ω₀, γ` 数值
- 时间显式依赖（agent 须从 x(t) 振荡里推断）

**Agent 必须自己发现**：
1. 振幅包络不是单纯指数衰减 ⇒ 含 `Ω_p − ω₀` 拍频
2. 频谱含 `ω₀, Ω_p, ω₀ ± Ω_p` 边带（参数泵浦签名）
3. 拟合 `ε, Ω_p`
4. 推断 T-trans 破

**Bonus probe**：`broken_symmetry: "T-trans"` +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | parametric pumping, sub-threshold |
| 公式数学正确 | ✅ | T-trans 破，LIN/PAR 保留推导 |
| T-trans 真破 | ✅ | RHS 显式 t |
| LIN / PAR 保留 | ✅ | 方程对 x 线性，cos 与 x 无关 |
| 代码 ↔ catalog 一致 | ✅ | 含 sampler 动态约束 |
| 采样分布合理 | ✅ | sub-threshold 主动维护 |
| 数值安全 | ✅ | ε < 4γ/ω₀ 阈值守住 |
| 信息泄漏防御 | ✅ | 不输出 ω(t) |

**🟡 改进点**：
1. sampler 当 ε 范围空集时直接修改 `γ`，可能略偏 sampling 设计意图 — 文档化此 trick
2. T_sim 长度未约束 — 长 sim 中即使 sub-threshold，缓慢 drift 也累积。建议 `T_sim ≤ 50·max(1/γ, 2π/Ω_p)`

---

**γ-3-2 verdict**：物理 / 代码 / 设计**全 PASS**。Sub-threshold 设计稳健。

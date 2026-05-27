# γ-7-2: Thermal power-law memory kernel — 深度审查

> 域 7 / Thermal / γ-tier / shift_id = `gamma_7_2`
> 代码：[`mirrorlab/shifts/thermal_g_7_2.py`](../../mirrorlab/shifts/thermal_g_7_2.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：Fourier instantaneous

`q(t) = -k ∂_x T(t)` — flux 仅依赖**瞬时**温度梯度（无记忆 ⇒ Markov）。

抛物 self-similar scale：`(t→λt, x→λ^{½}x)` 让 `∂_t T - α∇²T = 0` form-invariant。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：复杂介质（聚合物、多孔、凝胶）有**时间记忆**。避开经典 Cattaneo-Vernotte 双曲方程，借**分数阶粘弹性**的幂律核形式 — 跨域 motif。

**修法**：
$$q(t) = -\int_{t_0}^{t} G(t-s)\,\partial_x T(s)\,ds,\quad G(\tau) = \frac{k_0 \tau^{-p}}{\Gamma(1-p)},\ \tau \ge \tau_{\min}$$

记忆指数 `p ∈ (0, 1)`，`τ_min` 是下界截断（防 `τ=0` 奇异，sim-level 设为 `Δt_sim`）。

`Γ(1-p)` 是 fractional kernel 标准 normalization。

---

## 3. 哪条对称性被破了？

**目标**：**只破抛物 self-similar scale**。

scaling test：`(t→λt, x→λ^{½}x, T→T)`。
- `∂_x T → λ^{-½}∂_x T`
- 核 `G(τ) = k₀ τ^{-p}/Γ(1-p)`：`τ → λτ ⇒ τ^{-p} → λ^{-p} τ^{-p}`
- 积分 `∫G(τ) ∂_x T(t-τ) dτ`：测度 `dτ → λ dτ`
- 合计：`q → λ^{-p} · λ^{-½} · λ^{1} q = λ^{½ - p} q`

baseline (p=0 极限) ⇒ `q → λ^{½} q`，匹配 Fourier scaling；当 p ≠ 0 ⇒ scaling 指数偏移 ⇒ **scale 破缺** ✓

具体：fractional 系统的新 self-similar 律是 `x → λ^{(1-p)/2} x`，与 baseline 不同。

---

## 4. 哪些对称性必须保住？

### T-trans
- 卷积形式 `G(t-s)` ⇒ 对 t shift 不变（设 `t_0 → -∞` 大窗口极限）⇒ ✓

### SO(3)（在 isotropic G 下，时间核与空间方向无关）
- G 是标量、`∂_x T` 在多 D 推广为 `∇T` ⇒ flux 仍为 vector，rotation-equivariant ✓

### S-trans
- 核与 x 无关 ⇒ ✓

### T → T+c
- 公式只含 `∂_x T` ⇒ ✓

### 能量守恒
- flux 仍写成 `-G * ∇T` 是某 generalized Fick law ⇒ 散度形式仍守恒（在绝热边界下）✓

### Onsager
- G 是 scalar ⇒ 推广到 tensor 形式时仍对称 ✓

---

## 5. 代码实现逐行核对

```python
def shifted_flux(t, params):
    """Steady ∂_x T ⇒ q(t) = -k₀ ΔT/L · ∫_{tau_min}^{t} τ^{-p}/Γ(1-p) dτ."""
    if t <= params.tau_min:
        return 0.0
    grad = (params.T_cold - params.T_hot) / params.L
    integral = (t**(1-p) - tau_min**(1-p)) / (1 - p)
    return -params.k0 * grad * integral / math.gamma(1 - params.p)
```

**推导核对**：在 **steady ∇T** 假设下（即 `∂_x T(s) = const`），
$$q(t) = -\partial_x T \cdot \int_{\tau_{\min}}^t \frac{k_0 \tau^{-p}}{\Gamma(1-p)}d\tau = -\frac{k_0 \partial_x T}{\Gamma(1-p)}\cdot\frac{t^{1-p} - \tau_{\min}^{1-p}}{1-p}$$

代码：
- `∂_x T = (T_cold - T_hot)/L` ✓（slab 几何）
- 积分公式（解析）✓
- 符号 `-k₀ · grad · integral / Γ` ✓

🟡 **简化**：仅评估 steady-gradient case。这让"记忆"表现为 `q(t)` 随 t 增长（不到达 baseline 稳态），但**无法测 transient gradient**（real fractional 系统的特征）。Sprint 工程简化 — v1 OK。

---

## 6. 采样分布合理性

```python
P_MIN, P_MAX = 0.10, 0.55              # 记忆指数
K0_MIN, K0_MAX = 0.1, 50.0
L = 0.1, T_hot = 373, T_cold = 293
tau_min = 1e-3                          # sim-level 截断（不告诉 AI）
```

- p ∈ [0.1, 0.55] — 排除 p→1 退化与 p > 0.6 数值差 ✓
- catalog 写 `p ≤ 0.6` 保 Γ(1-p) 良态；代码上限 0.55 更严 ✓

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (P_MIN <= params.p <= P_MAX): return False
    if not (K0_MIN <= params.k0 <= K0_MAX): return False
    if params.L <= 0 or params.tau_min <= 0: return False
```

- p < 0.55 严守 ✓
- τ_min > 0 ⇒ 截断防奇异 ✓
- `step` 中 `t <= τ_min` 返回 0 ⇒ 边界 well-defined ✓

🟢 OK。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：slab 描述、measure 读 `q(t)`、可调 `T_hot, T_cold, L`。

**Agent 看不到**：shift label、`p, τ_min` 数值、"fractional kernel"motif。

**Agent 必须发现**：
1. q(t) 非瞬时建立（baseline 应是稳态 `-k ΔT/L` 立即）
2. q(t) 按某幂律 `t^{1-p}` 增长
3. 拟合 `(k₀, p)` — 涉及非整数微积分识别

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借分数阶粘弹性 |
| 公式数学正确 | ✅ | steady-grad 解析积分 |
| 抛物 scale 真破 | ✅ | scaling 指数 ½-p |
| T-trans / SO(3) / S-trans / T+c / E / Onsager 保留 | ✅ | 卷积时不变 + 散度形式 |
| 代码 ↔ catalog 一致 | ✅ | steady-state 简化合理 |
| 采样合理 | ✅ | p < 0.55 远离奇异 |
| 数值安全 | ✅ | τ_min 截断 + 解析积分 |
| 信息泄漏防御 | ✅ | 全藏 |

🟡 **改进点**（v2）：
1. 支持 transient ∂_x T（让 AI 测 step response，更鲜明的记忆特征）
2. 多 seed p 不同值，让 AI fit `t^{1-p}` 指数

---

**γ-7-2 verdict**：物理 / 代码 / 设计**全 PASS**。

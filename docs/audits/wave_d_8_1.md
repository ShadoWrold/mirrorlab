# δ-8-1: Wave amplitude-gated viscous damping — 深度审查

> 域 8 / Scalar wave / δ-tier / shift_id = `delta_8_1`
> 代码：[`mirrorlab/shifts/wave_d_8_1.py`](../../mirrorlab/shifts/wave_d_8_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix：amplitude-gated 替代 textbook 线性吸收）

---

## 1. 原始定律

`∂_t² u = c² ∂_x² u` — 无耗散，能量严格守恒。

---

## 2. 怎么改的：物理动机 + 数学形式

**R1 教训（B3）**：原版 `∂_t² u = c²∂_x²u - α₀∂_t u` 是 **textbook 线性阻尼波动方程** ⇒ lookup-style AI 一眼识别 ⇒ attack-resistance FAIL。
**Fix**：振幅门控（sub-linear envelope）— borrow Part A δ-3-1 motif，跨域到 PDE：
$$\partial_t^2 u = c^2 \partial_x^2 u - \alpha_0\cdot\frac{|u|}{u_{\text{ref}}}\cdot \partial_t u$$

阻尼系数随 |u| 线性变 ⇒ 小振幅近似线性传播；大振幅强阻尼。

**Lumped 模型**：plane wave at probe ⇒ modal amplitude 满足
$$\ddot u + \alpha_0 \frac{|u|}{u_{\text{ref}}}\dot u + \omega^2 u = 0,\quad \omega = ck$$

---

## 3. 哪条对称性被破了？

**目标**：**只破能量守恒**（T-rev bundled）。

**能量收支**：
$$\frac{dE}{dt} = -\alpha_0 \frac{|u|}{u_{\text{ref}}}(\partial_t u)^2 \le 0$$

（仅当 u = 0 或 ∂_t u = 0 时等号）⇒ 严格耗散 ⇒ E 单破 ✓

**T-rev bundled**：耗散标准约定。

---

## 4. 哪些对称性必须保住？

### T-trans
- 系数 α₀, u_ref, c, k 常数 ⇒ autonomous ✓

### S-trans
- α 系数 x-无关 ⇒ ✓

### PAR `x → -x`
- 方程 LHS、RHS 全为 x 偶项 ⇒ ✓

### `u → -u` 内部对称
- `|u| → |u|, ∂_t u → -∂_t u, ∂_t² u → -∂_t² u, ∂_x² u → -∂_x² u`
- 整体方程：`-∂_t² u = -c²∂_x² u - α₀(|u|/u_ref)(-∂_t u)`
- 即 `∂_t² u = c²∂_x² u - α₀(|u|/u_ref)(-∂_t u)` ⇒ symbol 不一致... 重新算：
  - LHS: `-∂_t² u`
  - RHS: `c²(-∂_x² u) - α₀(|u|/u_ref)(-∂_t u) = -c² ∂_x² u + α₀(|u|/u_ref) ∂_t u`
  - 整体两边乘 -1: `∂_t² u = c² ∂_x² u - α₀(|u|/u_ref) ∂_t u` ✓ **回到原方程**

⇒ `u → -u` invariant ✓ （catalog 显式列出）

---

## 5. 代码实现逐行核对

```python
def _integrate(self, t_max):
    omega = p.c * p.k
    def rhs(t, y):
        u, v = y
        return (v, -p.alpha0 * (abs(u) / p.u_ref) * v - omega**2 * u)
    sol = solve_ivp(rhs, (0, t_max), [p.A, 0.0], method="DOP853", ...)
```

对照 catalog modal `ü + α₀(|u|/u_ref)u̇ + ω²u = 0`：
- `v = u̇` ✓
- `dv/dt = -α₀(|u|/u_ref)v - ω²u` ✓
- IC: `u(0) = A, du(0)/dt = 0` ✓

🟢 一致。

---

## 6. 采样分布合理性

```python
ALPHA_MIN, ALPHA_MAX = 1e-3, 0.3        # s⁻¹
U_REF_MIN, U_REF_MAX = 1e-3, 1.0        # m, 3 decade
C_MIN, C_MAX = 50, 5000
A = 0.1 m, k = 2 / m                     # fixed
```

- α₀ 3 decade、u_ref 3 decade ⇒ 涵盖弱-强阻尼 regime
- A=0.1 固定 ⇒ A/u_ref ∈ [0.1, 100] ⇒ 阻尼强度 α₀·(A/u_ref) ∈ [10⁻⁴, 30]
- 强阻尼端可能 quickly decay ⇒ 仿真 t_max 自适应

🟡 单 A 仅一种振幅 ⇒ AI 无法直接探测 `|u|` 依赖性的真实形式（可能误以为是线性 α）。建议 v2 多 A 注入。

---

## 7. 安全约束 validator

```python
if not (ALPHA_MIN <= alpha0 <= ALPHA_MAX): return False
if not (U_REF_MIN <= u_ref <= U_REF_MAX): return False
if not (C_MIN <= c <= C_MAX): return False
if k <= 0 or A <= 0: return False
```

- 范围检查 ✓
- 阻尼**单调正** ⇒ E 单调减 ⇒ u 振幅有界 ⇒ 不发散 ✓

🟢 OK。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：1D wave 时间序列 (u(t), du_dt(t))；可选 A 注入。

**Agent 看不到**：shift label、`α₀, u_ref` 数值、振幅门控 motif、与 δ-3-1 跨域同源关系。

**Agent 必须发现**：
1. 振幅随时间衰减（不像无耗散 baseline）
2. 衰减率随当前 |u| 变化（非简单指数）
3. 区分 textbook 线性阻尼 vs 振幅门控（关键：lookup-resistant 设计）

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | δ-3-1 motif 跨域 PDE |
| 公式数学正确 | ✅ | E 单调减、u→-u invariant 验证 |
| E 真破（dissipative bundle）| ✅ | dE/dt ≤ 0 |
| T-trans / S-trans / PAR / u→-u 保留 | ✅ | 全 ✓ |
| 代码 ↔ catalog 一致 | ✅ | modal ODE 形式精确 |
| 采样合理 | ✅ | α, u_ref 3 decade |
| 数值安全 | ✅ | 单调耗散 ⇒ 有界 |
| 信息泄漏防御 | ✅ | step 输出 (u, du_dt) ⇒ 不直接泄漏 ω |
| Attack-resistance（R1 关注）| ✅ | 振幅门控 ≠ textbook 线性吸收 |

🟡 **改进点**（v2）：
1. 多 A 注入序列 ⇒ AI 可直接拟 `α_eff ∝ |u|`
2. 测试 u → 2u scaling：strict 线性时 衰减时标不变；shift 下变快 ⇒ 直接区别 baseline

---

**δ-8-1 verdict**：物理 / 代码 / 设计**全 PASS**（R1-fix 后 attack-resistance 大幅改善）。

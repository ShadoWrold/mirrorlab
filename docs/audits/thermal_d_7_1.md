# δ-7-1: Thermal quadratic-in-excess sink (comoving) — 深度审查

> 域 7 / Thermal / δ-tier / shift_id = `delta_7_1`
> 代码：[`mirrorlab/shifts/thermal_d_7_1.py`](../../mirrorlab/shifts/thermal_d_7_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix：comoving ⟨T⟩ 参考保 T→T+c）

---

## 1. 原始定律

`∂_t T = α∇²T`；绝热边界下 `∫ρc_p T dV = const` 守恒（**能量积分**）。

baseline 不变量包含 `T → T + c`（公式只含 `∇T`）— 这是**独立**于能量守恒的 affine 对称。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：制造 hidden 能量泄漏，避开 Stefan-Boltzmann `T⁴` 标准式。

**R1 教训（B2）**：原版用固定 `T_amb` 参考 ⇒ `T → T + c` 独立破缺（不属 Noether-paired with E）⇒ dual break。
**Fix**：用 **comoving 域内均值** `⟨T⟩_Ω(t)`：
$$\partial_t T = \alpha\nabla^2 T - \lambda\,\frac{(T - \langle T\rangle_\Omega(t))^2}{T_{\text{ref}}}$$

**关键**：`T → T + c ⇒ ⟨T⟩ → ⟨T⟩ + c ⇒ (T - ⟨T⟩) invariant` ⇒ sink 项**不变** ⇒ **T → T + c 保留** ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破能量守恒**（T-rev bundled）。

**能量收支**：
$$\frac{d}{dt}\int_\Omega T\,dV = \int_\Omega \alpha\nabla^2 T\,dV - \frac{\lambda}{T_{\text{ref}}}\int_\Omega (T-\langle T\rangle)^2 dV$$

绝热边界 ⇒ 第一项 = 0；第二项 = `-(λ/T_ref) · |Ω| · Var(T) ≤ 0`。
⇒ E 单调减（除非 T 处处相等）⇒ **E 真破** ✓

**T-rev bundled**：耗散过程标准 bundling（同 δ-1-1 / δ-3-1）。

---

## 4. 哪些对称性必须保住？

### SO(3), S-trans
- 公式只含 scalar field T 和 `∇²T`（rotational/translational invariant）✓

### T-trans（autonomous）
- 系数 `α, λ, T_ref` 常数；`⟨T⟩` 是状态泛函（瞬时计算，非显式 t 函数）⇒ autonomous ✓

### T → T+c（R1-fix 核心）
- `T → T + c ⇒ ⟨T⟩ → ⟨T⟩ + c ⇒ (T - ⟨T⟩)² invariant` ⇒ sink 不变
- `∇²T` 不动（常数被消去）⇒ 整个方程不变 ✓

### Onsager
- 扩散部分 `α∇²T` 仍对称（标量 α）✓

---

## 5. 代码实现逐行核对

```python
def _rhs(t, y, p):
    Ta, Tb = y
    Tmean = 0.5 * (Ta + Tb)
    lap_a = (Tb - Ta) / p.dx**2                       # 2-node 离散 Laplacian
    lap_b = (Ta - Tb) / p.dx**2
    sink_a = -p.lam * (Ta - Tmean)**2 / p.T_ref
    sink_b = -p.lam * (Tb - Tmean)**2 / p.T_ref
    return np.array([p.alpha * lap_a + sink_a, p.alpha * lap_b + sink_b])
```

**离散化核对**：
- 2 节点 lumped 模型，`⟨T⟩ = (T_a + T_b)/2`（comoving 均值）✓
- `(T_a - ⟨T⟩) = (T_a - T_b)/2`，sink 写在每节点上 ✓
- 离散 Laplacian: 1D 二节点 `(T_b - T_a)/dx²` 是**节点 a 处的离散 Laplacian** ✓

**T → T+c 验证**：`T_a → T_a + c, T_b → T_b + c, T_mean → T_mean + c`
- `T_a - T_mean → invariant` ⇒ sink 不变 ✓
- `T_b - T_a → invariant` ⇒ Laplacian 不变 ✓

🟢 离散化与连续方程一致地保 `T → T+c`。

---

## 6. 采样分布合理性

```python
LAM_MIN, LAM_MAX = 1e-5, 1e-2           # sink rate s⁻¹
T_REF_MIN, T_REF_MAX = 50.0, 1000.0     # K
alpha = 1e-4                             # 固定 m²/s
T_a = 373.0, T_b = 293.0                 # 80K 初始差
dx = 0.1
```

- λ 跨 3 decade ⇒ 涵盖弱泄漏 (100s 时标) 到强 (0.01s)
- T_ref 跨 2 decade ⇒ sink 灵敏度可调
- α=1e-4 m²/s ~ 固体扩散率（gold ~1e-4）✓
- ΔT_initial = 80K ⇒ initial Var ~ 1600 K² ⇒ initial sink rate ~ λ·1600/T_ref

🟡 α 固定可能过简；catalog 也允许 α sample。但 v1 单 hidden 参数 (λ, T_ref) 已足够。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (LAM_MIN <= params.lam <= LAM_MAX): return False
    if not (T_REF_MIN <= params.T_ref <= T_REF_MAX): return False
    if params.alpha <= 0 or params.dx <= 0: return False
    if params.T_a <= 0 or params.T_b <= 0: return False
```

- T > 0 检查 ✓（防止 sign 错位）
- catalog 写 "T(0) ≥ 2·max|T(0) - ⟨T(0)⟩| 保证 T ≥ 0 全程"：T_a = 373, T_b = 293, ⟨T⟩ = 333, max|T - ⟨T⟩| = 40 ⇒ T_min = 293 ≥ 2·40 = 80 ✓ 严格满足

🟢 OK。但 validator **没有显式检查** catalog 的 `T(0) ≥ 2·max|T(0)-⟨T⟩|` 约束 — 仅靠 hardcoded IC 满足。若 sampling 拓宽 IC，需补检查。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：2 节点温度系统；measure 读 `T_a, T_b, T_mean`。

**Agent 看不到**：shift label、`λ, T_ref` 数值、"sink"motif。

**Agent 必须发现**：
1. 两节点温度并非单调向 ⟨T⟩ 收敛（baseline Fourier 是指数 → 均衡）
2. 总能量（∝ T_a + T_b）单调减 ⇒ E 不守恒
3. T → T+c 平移测试：手动加 100K 偏置 ⇒ 行为同款 ⇒ `T+c` 仍是对称
4. 拟合 (λ, T_ref)

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | radiation cooling 思想，弃 T⁴ |
| 公式数学正确 | ✅ | comoving mean 保 T→T+c |
| E 真破 | ✅ | `dE/dt = -(λ/T_ref)·|Ω|·Var(T) ≤ 0` |
| SO(3) / S-trans / T-trans / T→T+c / Onsager 保留 | ✅ | comoving fix 关键 |
| 代码 ↔ catalog 一致 | ✅ | 2-节点离散与连续对应 |
| 采样合理 | ✅ | λ 3 decade + T_ref 2 decade |
| 数值安全 | ✅ | IC 满足 T ≥ 2·spread |
| 信息泄漏防御 | ✅ | step 输出 `T_mean` 但这是物理可观测 |

🟡 **改进点**（v2）：
1. validator 显式加 `T(0) ≥ 2·max|T(0)-⟨T⟩|` 检查（catalog 安全条款显式化）
2. 扩展到 3+ 节点 PDE，让 Var(T) 更丰富
3. α 也 sample，避免 single-α 退化

---

**δ-7-1 verdict**：物理 / 代码 / 设计**全 PASS**。

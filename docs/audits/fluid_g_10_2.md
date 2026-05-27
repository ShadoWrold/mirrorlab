# γ-10-2: Bernoulli 非线性重力势 — 深度审查

> 域 10 / Inviscid fluid / γ-tier / shift_id = `gamma_10_2`
> 代码：[`mirrorlab/shifts/fluid_g_10_2.py`](../../mirrorlab/shifts/fluid_g_10_2.py)
> Catalog Round-2 状态：APPROVED（R1-fix：采样级 precondition `|λ|·(h_max/h_0)^q < 0.5`）

---

## 1. 原始定律：Bernoulli + 仿射重力势

$$\tfrac{1}{2}\rho v^2 + \rho g h + p = \text{const}$$

baseline 重力项 `ρgh` 是 `h` 的**仿射函数**（线性 + 常数项可吸入 const）。

**关键不变量**：**垂直平移** `h → h + c` — 由于 `ρg(h+c) = ρgh + ρgc`，常数 `ρgc` 吸入 const → 物理不变。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：浮力分层 / 非均匀有效重力，避免 textbook 等温 / 等熵公式。

**改法**：
$$\tfrac{1}{2}\rho v^2 + \rho g h \cdot \Big(1 + \lambda (h/h_0)^q\Big) + p = \text{const}$$

势能项变成：
$$U(h) = \rho g h (1 + \lambda (h/h_0)^q)$$

不再是 `h` 的仿射函数。

**Round-1 修复（B5）**：原版 `|h| < 10 h_0` 安全界 false（反例 `λ=-0.25, q=2, h=10h_0 ⇒ 1 + (−0.25)(100) = −24`）。Round-2 改成**采样级约束**：

$$|\lambda| \cdot (h_{\max}/h_0)^q < 0.5$$

`h_max = 5.0 m` 物理 envelope；`ε = 0.5 / (h_max/h_0)^q`；`λ ~ Uniform(−ε, ε)`。

**关键性质**：
- `λ = 0` ⇒ baseline 完全恢复
- `q ∈ [0.5, 2.0]`：平方根到二次的幂律
- 修正因子 `(1 + λ(h/h_0)^q) ∈ (0.5, 1.5)` 严格正 → 势能单调凸 → 不发散 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破垂直平移 `h → h + c`**。

baseline：`ρg(h+c) = ρgh + ρgc` → 常数项吸入 const → 物理形式不变 ✓。

shift：
$$U(h+c) = \rho g (h+c) (1 + \lambda ((h+c)/h_0)^q)$$

展开 `(h+c)^{q+1}` 与 `h^{q+1}` 不是仿射关系（当 `q ≠ 0, λ ≠ 0`）→ **无法吸入 const** → **垂直 S-trans 真破**。✓

具体：差值
$$U(h+c) - U(h) = \rho g c + \rho g \lambda h_0^{-q}\Big[(h+c)^{q+1} - h^{q+1}\Big]$$

第二项依赖 `h`（不是单纯常数）→ 物理不变量遭破。

> 垂直 S-trans 破缺的精确数学位置：势能里 `h · λ(h/h_0)^q` 非线性项。

---

## 4. 哪些对称性必须保住？

### 水平 S-trans / SO(2) 水平旋转 / 水平 Galilean
- 公式只依赖 `h`（垂直坐标），水平坐标未触 → 全保留 ✓

### 质量守恒 `∇·v = 0`
- 不可压条件未触 ✓

### T-trans (steady)
- 公式不含 `t` ✓

### 流线能量
- 三项和仍守恒（修改的是势能形式不是耗散）✓

### 可逆性
- 无耗散项 ✓

---

## 5. 代码实现逐行核对

```python
def _gh_potential_per_rho(h, params):
    return params.g * h * (1.0 + params.lam * (h / params.h0) ** params.q)

def shifted_pressure(params):
    p = params
    return p.p1 + 0.5 * p.rho * (p.v1**2 - p.v2**2) + p.rho * (
        _gh_potential_per_rho(p.h1, p) - _gh_potential_per_rho(p.h2, p)
    )
```

| 代码 | catalog | 一致 |
|---|---|---|
| `g * h * (1 + lam * (h/h0)**q)` | `gh(1 + λ(h/h_0)^q)` | ✓ |
| `0.5 * rho * (v1²-v2²)` | KE 差 | ✓ |
| `rho * (U(h1) - U(h2))` | 势能差 | ✓ |

**完全一致**。

---

## 6. 采样分布合理性

```python
Q_MIN, Q_MAX = 0.5, 2.0
H0_MIN, H0_MAX = 1.0, 100.0       # LogUniform
H_MAX = 5.0                       # physical envelope

q ~ Uniform(0.5, 2.0)
h0 ~ LogUniform(1, 100) m
eps = min(0.5, 0.5 / (H_MAX/h0)**q)
while True:
    lam ~ Uniform(-eps, eps)
    if |lam| >= 0.01: break
rho ~ Uniform(800, 1200) kg/m³
g=9.81, h1=2, h2=0, p1=1.01e5
v1=1, v2=3 m/s
```

- **`q ∈ [0.5, 2.0]`**：sub-linear 到 quadratic，跨度合理 ✓
- **`h_0 ∈ [1, 100] m`** LogUniform：弱分层（`h_0 = 100 m`, 修正小）到强分层（`h_0 = 1 m`, 修正大）✓
- **`λ` 自适应采样**：`|λ|·(h_max/h_0)^q < 0.5` 严格守住 → R1 反例不可能再现 ✓
- **`|λ| ≥ 0.01`** 拒邻域 → 避免 baseline 退化 ✓
- **`ρ ∈ [800, 1200] kg/m³`**：水的合理变化（盐水 / 油 / 淡水）✓
- **`h_max = 5 m, h_1 = 2, h_2 = 0`**：实际仅用 `h ∈ [0, 2]`，远小于 `h_max = 5`，余 60% 保守 margin ✓

**🟡 改进点（v2）**：
1. `h_1, h_2` 固定 → seed 间垂直跨度不变。建议把 `h_1 ∈ [0.5, 4.5]` 加入采样让 `(h/h_0)^q` 变化更丰富。
2. `q` 端点 0.5 与 2.0 都是整数 / 半整数 → lookup-friendly。建议避开 `q ∈ {0.5, 1.0, 1.5, 2.0}` 邻域。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (Q_MIN <= params.q <= Q_MAX): return False
    if not (H0_MIN <= params.h0 <= H0_MAX): return False
    if params.rho <= 0: return False
    if abs(params.lam) < 0.01 or abs(params.lam) > 0.5: return False
    # Sampling-level constraint
    if abs(params.lam) * (H_MAX / params.h0) ** params.q >= 0.5: return False
    return True
```

- 边界检查 ✓
- `|λ| ∈ [0.01, 0.5]` 守住 ✓
- **采样级 precondition 硬约束**：直接 validator 拦截 → 即使外部传入也安全 ✓
- 数学验证：在守约束下 `(1 + λ(h/h_0)^q) ∈ (0.5, 1.5)` 在 `|h| ≤ h_max` 上严格正 → 势能单调凸 → 不发散 ✓

**R1 反例不可能通过**：`λ=−0.25, q=2, h_0=0.5 m` ⇒ `|−0.25|·(5/0.5)^2 = 25 >> 0.5` → validator 拒绝 ✓。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 流体场景：`(v, h, p)` 上下游
- 32 工具

**藏**：
- shift label `γ-10-2 / vertical S-trans broken`
- `(1 + λ(h/h_0)^q)` 非线性形式
- `λ, q, h_0` 参数

**Agent 必须发现**：
1. 测同样 `Δh` 在不同 `h_1, h_2` 处的压力差 → baseline 应仅依赖 `Δh`；shift 依赖绝对 `h` → 垂直平移破
2. 拟合 `U(h) − ρgh` 残差 → 揭示幂律形式
3. 双符号 `λ` 注意"sub-linear 加强 / 弱化"图像

**Bonus**：`broken_symmetry: "vertical_translation"` 或 `"h_translation"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 分层浮力 / Part A γ-4-2 跨域 anchor |
| 公式数学正确 | ✅ | 势能凸正定，连续退化到 baseline |
| 垂直 S-trans 真破 | ✅ | 非仿射 → 无法吸入 const |
| 其他对称性保留 | ✅ | 水平 / SO(2) / Galilean / T-trans / 流线 E |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | 自适应 ε 保 (0.5, 1.5)；`|λ|≥0.01` 排斥邻域 |
| 数值安全 | ✅ | precondition 硬约束 → R1 反例已堵 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `h_1` 加入采样，增加垂直跨度多样性
2. `q` 避开 `{0.5, 1, 1.5, 2}` 整数邻域防 lookup attacker

---

**γ-10-2 verdict**：物理 / 代码 / 设计**全 PASS**（R1-fix 教科书级，是 catalog 里 robustness 标杆）。

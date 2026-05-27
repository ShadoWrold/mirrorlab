# γ-10-1: Bernoulli 各向异性动能 — 深度审查

> 域 10 / Inviscid fluid / γ-tier / shift_id = `gamma_10_1`
> 代码：[`mirrorlab/shifts/fluid_g_10_1.py`](../../mirrorlab/shifts/fluid_g_10_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix：完整 Euler 方程 `M_{ij} Dv_j/Dt = −∂_i p − ρg ∂_i h` 补齐）

---

## 1. 原始定律：理想 Bernoulli

沿同一流线（无粘 / 不可压 / 稳态）：
$$\tfrac{1}{2}\rho v^2 + \rho g h + p = \text{const}$$

附质量守恒 `∇·v = 0`。Bernoulli 是 Euler 方程沿流线的积分；二者必须一致。

**对称性结构**：

| 对称性 | 验证 | 含义 |
|---|---|---|
| **SO(3) 各向同性** | 动能 `½ρv²` 标量 | 物理空间各方向等价 |
| **质量守恒** | `∇·v=0` | 不可压 |
| **水平 Galilean** | `v → v + u_∥` 重力势不变 | 平移参考系不变 |
| **`h → h + c`** | 重力势可吸入 const | 高度零点任意 |
| **T-trans (steady)** | 项不含 `t` | 稳态 |
| **流线能量** | 三项和守恒 | 无粘可逆 |
| **可逆性** | 无耗散 | 无粘 |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：取向性多相流（纤维 / 拉伸聚合物）— 借 solid-state effective-mass tensor 搬到流体动能。

**Round-1 修复（B4）**：仅改 Bernoulli scalar 不完备；必须给出对应 Euler 方程。Round-2 补全：

**Euler 层（修改后）**：
$$M_{ij}\Big(\partial_t v_j + (v\cdot\nabla)v_j\Big) = -\partial_i p - \rho g \partial_i h$$

**有效质量张量**（traceless 各向异性）：
$$M_{ij} = \rho\Big[\delta_{ij} + \alpha\big(n_i n_j - \tfrac{1}{3}\delta_{ij}\big)\Big]$$

- `tr(M) = 3ρ`（迹守恒，平均密度不变）
- 各向异性方向 `n̂` 是单位矢
- `α` 控制各向异性强度

**Bernoulli（沿流线积分）**：
$$\tfrac{1}{2}v_i M_{ij} v_j + \rho g h + p = \text{const}$$

**关键性质**：
- `M` 对称正定 → KE-quadratic form 良定义
- `α = 0` ⇒ `M_{ij} = ρ δ_{ij}` ⇒ baseline 完全恢复
- 各向异性引入优先方向 `n̂` → 破 SO(3) ✓
- 与 textbook 有效质量公式（晶格 k·p 模型 `m*_{ij}`）非函数同形：traceless 形式是新组合 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破 SO(3) 各向同性**。

SO(3) 操作：旋转矩阵 `R` 作用 `v → Rv`，物理结果应只依赖 `|v|`。

baseline：`v_i M^{baseline}_{ij} v_j = ρ|v|²` 旋转不变 ✓。

shift：
$$v_i M_{ij} v_j = \rho|v|^2 + \rho\alpha\Big[(n\cdot v)^2 - \tfrac{1}{3}|v|^2\Big]$$

当 `α ≠ 0` 且 `v` 与 `n̂` 不平行也不垂直，`(n·v)²` 依赖于 `v` 在 `n̂` 上的投影 → 旋转 `v` 改变结果 → **SO(3) 真破**。✓

> SO(3) 破缺的精确数学位置：`M` 的 traceless 各向异性部分 `α(n_i n_j − δ_{ij}/3)`。

---

## 4. 哪些对称性必须保住？

### 质量守恒 `∇·v = 0`
- 不可压条件未触 → 保留 ✓

### 水平 Galilean
- `M` 是常张量（不依赖 `v`），变换下不变 ✓

### `h → h + c`
- 重力项 `ρg(h_1 − h_2)` 是差分形式 → 常数加项消去 ✓

### T-trans (steady)
- 公式不含 `t` → 自治 ✓

### 流线能量
- `M` 对称正定 ⇒ 沿同一流线 `½v·Mv + ρgh + p = const` 守恒 ✓

### 可逆性
- 无耗散项 → 无粘可逆 ✓

**invariant-checker Round-2 复审**："Eigenvalues of `M/ρ` positive over sampling range"，全部通过。✓

---

## 5. 代码实现逐行核对

```python
def _M_over_rho(params):
    n = np.asarray(params.n, dtype=float)
    return np.eye(3) + params.alpha * (np.outer(n, n) - np.eye(3) / 3.0)

def shifted_pressure(params):
    Mor = _M_over_rho(params)
    v1 = np.asarray(params.v1, dtype=float)
    v2 = np.asarray(params.v2, dtype=float)
    ke1 = 0.5 * params.rho * (v1 @ Mor @ v1)
    ke2 = 0.5 * params.rho * (v2 @ Mor @ v2)
    return params.p1 + (ke1 - ke2) + params.rho * params.g * (params.h1 - params.h2)
```

逐符号对照 catalog `½ v_i M_{ij} v_j + ρ g h + p = const`：

| 代码 | catalog | 一致 |
|---|---|---|
| `np.eye(3) + alpha * (outer(n,n) - eye/3)` | `δ_{ij} + α(n_i n_j − δ_{ij}/3)` | ✓ |
| `0.5 * rho * (v @ M/ρ @ v)` | `½ v_i M_{ij} v_j` | ✓ |
| `rho * g * (h1 - h2)` | 重力势差 | ✓ |
| Bernoulli 闭合解 `p2 = p1 + (KE1-KE2) + ρg(h1-h2)` | 流线积分 | ✓ |

**完全一致**。`@` 表 `numpy` 矩阵乘符合 quadratic form。

---

## 6. 采样分布合理性

```python
ALPHA_MIN, ALPHA_MAX = -0.4, 1.4
RHO_MIN, RHO_MAX = 50.0, 5e3   # LogUniform
n̂ ~ standard_normal(3) then normalize
g=9.81, h1=2, h2=0, p1=1.01e5
v1=(1,0,0), v2=(3,0,0)
```

- **`α ∈ [-0.4, 1.4]`**：catalog 安全界 `(-1, ∞)`；实际选 `-0.4` 留 60% margin 不达 `α=-1` 奇点 ✓
- **`ρ ∈ [50, 5000] kg/m³`** LogUniform：跨气溶胶到重盐水，覆盖 2 个数量级，物理合理 ✓
- **`n̂` Gaussian 后归一化**：S² 上均匀采样的标准做法（O(3)-不变）✓
- **`v1, v2, h, p` 固定**：单一流线场景，仅参数变化 → seed 间差异主要来自 `(α, n̂, ρ)`

**🟡 改进点（v2）**：
1. `v1, v2` 与 `n̂` 都固定的话，`(n·v)²` 投影变化只来自 `n̂` 旋转。若 `n̂` 接近 `(1,0,0)`，破缺最强；垂直时 `(n·v)² = 0`。建议把 `v1, v2` 加入采样或保证 `n̂ · v̂_1 ≥ 0.3` 避免破缺信号被自然弱化。
2. `α = 0` 在 `[-0.4, 1.4]` 内 → 概率小但有 → 退化到 baseline。建议 `|α| ≥ 0.05` 排斥邻域。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (ALPHA_MIN <= params.alpha <= ALPHA_MAX): return False
    if not (RHO_MIN <= params.rho <= RHO_MAX): return False
    if abs(np.linalg.norm(params.n) - 1.0) > 1e-6: return False
    # M/ρ positive-definite: eigenvalues are 1 - α/3 (perp×2) and 1 + 2α/3 (along n)
    if 1.0 - params.alpha / 3.0 <= 0: return False
    if 1.0 + 2.0 * params.alpha / 3.0 <= 0: return False
    return True
```

**正定性数学验证**：traceless tensor `n_i n_j − δ_{ij}/3` 本征值为 `(2/3, -1/3, -1/3)`。
故 `M/ρ` 本征值：
- 沿 `n̂` 方向：`1 + α·(2/3) = 1 + 2α/3`
- 两个垂直方向：`1 + α·(−1/3) = 1 − α/3`（重根 ×2）

正定 ⇔ 两本征值 > 0：
- `1 − α/3 > 0` ⇒ `α < 3`
- `1 + 2α/3 > 0` ⇒ `α > −3/2`

⇒ 安全区 `α ∈ (−1.5, 3)`。sampler 取 `[-0.4, 1.4]` 严格在内 → **保守 ✓**。

代码注释说 `α < 3` 来自 `1 − α/3` 本征值；与上方推导一致 ✓。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 流体场景：上下游 `(v, h, p)`，求下游 `p_2`
- 32 工具

**藏**：
- shift label `γ-10-1 / SO(3) broken`
- `M` 张量形式 + 优先方向 `n̂`
- `α` 振幅
- Euler 方程修改这一事实

**Agent 必须发现**：
1. Bernoulli 公式给出的 `p_2` 偏离 baseline → 怀疑动能项不是 `½ρ|v|²`
2. 改变 `v` 方向（关于 `n̂` 的取向）→ KE 项变化 → 揭示各向异性
3. 拟合 `M` 张量本征结构 → 揭示 traceless 形式

**Bonus**：`broken_symmetry: "SO(3)"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | effective-mass 借影；Euler 一致性 R1-fixed |
| 公式数学正确 | ✅ | traceless `tr(M)=3ρ`，本征值正定可验证 |
| SO(3) 真破 | ✅ | `(n·v)²` 项不旋转不变 |
| 其他 6 条对称性保留 | ✅ | 质量 / Galilean / h-trans / T-trans / 流线 E / 可逆 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ⚠️ | `α=0` 邻域 + `n̂·v` 投影变化未对齐 |
| 数值安全 | ✅ | 正定本征界保守 `α ∈ [-0.4, 1.4] ⊂ (-1.5, 3)` |
| 信息泄漏防御 | ✅ | shift label / 张量 / 参数全藏 |

**🟡 改进点**（v2）：
1. `|α| ≥ 0.05` 邻域排斥
2. `v_1, v_2` 加入采样，配合 `n̂` 让破缺信号稳定
3. 文档化 Euler 修改：spec 层应在 hidden ground-truth 里记录

---

**γ-10-1 verdict**：物理 / 代码 / 设计**全 PASS**（R1-fix 干净，采样小瑕疵 v2 修）。

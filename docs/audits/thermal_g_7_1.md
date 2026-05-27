# γ-7-1: Thermal constant-β anisotropic conductivity — 深度审查

> 域 7 / Thermal conduction / γ-tier / shift_id = `gamma_7_1`
> 代码：[`mirrorlab/shifts/thermal_g_7_1.py`](../../mirrorlab/shifts/thermal_g_7_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix：constant β + field-independent K）
> **人工二审 errata (2026-05-27)**：🔴 `step()` 输出 `q_x, q_y, q_z` 三分量，但 baseline thermal 只输出标量 `q`。off-axis 分量 (q_y, q_z ≠ 0 当 n̂ 不沿 ∇T) 的存在本身揭示 ROT break。v2 修：只输出标量 `q_norm` 或 `q_along_grad`，让 agent 通过 manipulate `grad_dir` 方向自己发现各向异性（[v2-todo TODO-2](../v2-todo.md)）。

---

## 1. 原始定律：Fourier 各向同性

$$q_i = -k\,\partial_i T,\qquad \partial_t T = \alpha\nabla^2 T,\ \alpha = k/(\rho c_p)$$

| 对称性 | 验证 |
|---|---|
| **SO(3)** 各向同性 | k 标量 |
| **S-trans** | k 与位置无关 |
| **T-trans** | k 与时间无关 |
| **T → T+c** | baseline 仅含 `∇T` |
| **能量积分** `∫ρc_p T dV` | 绝热边界 |
| **Onsager** | `k_{ij} = k_{ji}` |
| **抛物 self-similar** | `(t→λt, x→λ^{½}x)` |

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：借 EM 各向异性介电张量 `ε_{ij} = ε₀(δ_{ij} + χ n_i n_j)` 的代数结构搬到热域。

**R1 教训（B1）**：原版 `tanh(|∇T|/G₀)` 是 field-magnitude-gated 非线性 ⇒ 抛物 self-similar scale 独立破缺 ⇒ dual break。
**Fix**：常数 β + 宽对数随机 + 每 scenario 随机 `n̂`。
$$q_i = -K_{ij}\,\partial_j T,\qquad K_{ij} = k_0[\delta_{ij} + \beta n_i n_j]$$

由于 K **与场无关**（仅几何方向 `n̂` 是 hidden lab constant）：在 `(t→λt, x→λ^{½}x)` 下 ∇T 和 ∇²T 按抛物 scaling 变 ⇒ 方程 form-invariant ⇒ 抛物 self-similar **保留** ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破 SO(3)**（各向同性）。

R∈SO(3) 操作下：`K_{ij} → R_{ia} R_{jb} K_{ab}`。
若 `n̂` 固定 lab 方向（不随 R 转）⇒ `K_{ij}` 不是同一个张量 ⇒ 方程 form 改变 ⇒ ✓ SO(3) 真破。

只有当 R 保持 `n̂` 不变（绕 `n̂` 轴旋转）时 K 不变 ⇒ residual `SO(2) around n̂`。这正是 uniaxial anisotropy 的标志。

---

## 4. 哪些对称性必须保住？

### S-trans, T-trans
- K 与 (x, t) 无关 ⇒ 显然 ✓

### T → T+c
- 公式只含 `∂_j T`，常数项消去 ⇒ ✓

### 能量积分
- K 对称正定（`K_{ij} = k₀ δ_{ij} + k₀ β n_i n_j` ⇒ 对称；本征值 `{k₀, k₀, k₀(1+β)}` 全正若 `β > -1`）
- `∂_t T = -∇·q/(ρc_p) = ∇·(K∇T)/(ρc_p)` 散度形式 ⇒ `∫∂_t T dV = -∮q·n dS = 0`（绝热）⇒ 守恒 ✓

### Onsager 互易
- `K_{ij} = k₀[δ_{ij} + β n_i n_j]` 显式对称（`n_i n_j = n_j n_i`）✓

### 抛物 self-similar scale
- K 不依赖 T 或 ∇T ⇒ scaling argument 通过 ✓（R1-fix 的关键）

---

## 5. 代码实现逐行核对

```python
def _flux_components(params):
    n = np.asarray(params.n)
    d = np.asarray(params.grad_dir)
    K = params.k0 * (np.eye(3) + params.beta * np.outer(n, n))
    grad_T = (params.T_cold - params.T_hot) / params.L * d
    return -K @ grad_T
```

对照 catalog `q_i = -K_{ij} ∂_j T`，`K = k₀(I + β n⊗n)`：
- 张量 `np.outer(n, n) = n_i n_j` ✓
- `K = k₀(I + β n⊗n)` ✓
- `grad_T = ΔT/L · d_hat`（slab 几何）✓
- 矩阵-向量积 `K @ ∇T` 等价 `Σ_j K_{ij} ∂_j T` ✓

🟡 **范围限制**：代码做的是**稳态 1D slab 的 flux 评估**，并未跑全时空 PDE。这是 Sprint 工程简化：足够 expose 各向异性 vs 同性的差异（同 T_hot/T_cold 但 q 方向不与 grad_dir 平行）。

---

## 6. 采样分布合理性

```python
K0_MIN, K0_MAX = 0.1, 50.0                # W/(m·K)
BETA_MIN, BETA_MAX = 0.05, 5.0            # 两 decade 宽
n = standard_normal(3) / norm             # uniform on S²
L = 0.1, T_hot = 373, T_cold = 293        # 100K 跨 10cm 板
```

- k₀ 涵盖空气（0.025）到金属（>50）量级附近 ✓
- **β ∈ [0.05, 5] log-uniform**（不是 [0.05, 0.4]）— catalog 故意宽，**确保非 textbook**（单晶 anisotropy 系数通常窄）✓
- n̂ 球面均匀 — 标准 Gaussian normalize 法 ✓

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (K0_MIN <= params.k0 <= K0_MAX): return False
    if not (BETA_MIN <= params.beta <= BETA_MAX): return False
    if params.L <= 0: return False
    n_norm = np.linalg.norm(params.n)
    if abs(n_norm - 1.0) > 1e-6: return False
```

- β ≥ 0.05 > -1 ⇒ K 正定（本征值 `{k₀, k₀, k₀(1+β)} > 0`）✓
- β ≤ 5 ⇒ `K_∥ = 6 k_⊥` 良态 ✓
- 单位向量校验 ✓

🟢 OK。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：slab 几何描述，可探测沿不同 grad_dir `d̂` 的 flux；measure 读 `q_x, q_y, q_z, q_norm`。

**Agent 看不到**：shift label、β 数值、n̂ 方向、"anisotropic" 关键词。

**Agent 必须发现**：
1. 改变 `d̂` 时 q 方向**不与 d̂ 平行**（同性时一定平行）
2. q_∥ / q_⊥ 比值随 `d̂ 与 n̂ 夹角` 变化
3. 拟合 `(k₀, β, n̂)` 5 参数

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借介电张量代数 |
| 公式数学正确 | ✅ | K 对称正定 + 散度形式 |
| SO(3) 真破 | ✅ | n̂ lab-fixed |
| S-trans / T-trans / T→T+c / E / Onsager / 抛物 scale 保留 | ✅ | K 与 (x, t, T) 无关 |
| 代码 ↔ catalog 一致 | ✅ | K = k₀(I + β n⊗n) |
| 采样合理 | ✅ | β 宽对数 + n̂ 球面 |
| 数值安全 | ✅ | β ≥ 0.05 ⇒ 严格正定 |
| 信息泄漏防御 | ✅ | 全藏 |

🟡 **改进点**（v2）：
1. 代码仅 steady-state slab；催完整 2D/3D PDE 的话能让 AI 测试更多 mode（但增 sim cost）
2. 显式探测多 grad_dir 协议（让 AI 拟合 n̂ 更直接）

---

**γ-7-1 verdict**：物理 / 代码 / 设计**全 PASS**。

# γ-8-2: Wave 2D anisotropic phase speed (dielectric tensor re-skin) — 深度审查

> 域 8 / Scalar wave / γ-tier / shift_id = `gamma_8_2`
> 代码：[`mirrorlab/shifts/wave_g_8_2.py`](../../mirrorlab/shifts/wave_g_8_2.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：2D 各向同性波

$$\partial_t^2 u = c^2 \nabla^2 u$$

色散：`ω² = c²|k|²`，与 `k` 方向无关 ⇒ **SO(2)** 平面旋转对称。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：晶格 / 多层介质各向异性，借 EM 介电张量到声学。

**修法**：
$$\partial_t^2 u = c^2 \partial_i (M_{ij} \partial_j u),\qquad M = R(\theta_0)\,\text{diag}(1, 1+\beta)\,R(\theta_0)^T$$

`R(θ_0)` 为 lab-fixed 主轴系旋转，`diag(1, 1+β)` 是各向异性 stretch 张量。

**色散关系**：plane wave `u = e^{i(k·x - ωt)}`：
- `∂_t² u = -ω² u`
- `∂_i(M_{ij}∂_j u) = -k_i M_{ij} k_j u`

⇒ $\omega^2 = c^2\, k_i M_{ij} k_j$

依赖 `k` 与主轴的夹角 ⇒ 方向相关 phase speed ⇒ 各向异性。

---

## 3. 哪条对称性被破了？

**目标**：**只破 SO(2)**（平面旋转）。

R ∈ SO(2) 操作：`k → Rk`；`M` 是 lab-fixed 张量，不随 R 变。
`k_i M_{ij} k_j → (Rk)_i M_{ij} (Rk)_j = k_a R_{ai} M_{ij} R_{bj} k_b = k_a (R^T M R)_{ab} k_b`

一般 `R^T M R ≠ M` ⇒ ω² 改变 ⇒ ✓ SO(2) 真破

---

## 4. 哪些对称性必须保住？

### T-trans / S-trans
- M lab constant ⇒ 系数与 (x, t) 无关 ✓

### PAR `x → -x`
- `∂_i, ∂_j` 各反号 ⇒ `∂_i(M_{ij} ∂_j u)` 不变 ✓

### T-rev
- `∂_t²` 偶 ⇒ ✓

### 能量
- M 对称正定 ⇒ Hamilton `H = ∫(½π² + ½c² M_{ij} ∂_i u ∂_j u) dx` 良定义守恒 ✓

### LIN
- 线性 in u ✓

---

## 5. 代码实现逐行核对

```python
def _M_matrix(beta, theta0):
    R = [[cos θ0, -sin θ0], [sin θ0, cos θ0]]
    D = diag(1, 1+beta)
    return R @ D @ R.T

def shifted_omega_squared(params):
    M = _M_matrix(beta, theta0)
    k_vec = k * [cos θ_k, sin θ_k]
    return c² · (k_vec @ M @ k_vec)
```

对照 catalog `M = R(θ₀)·diag(1, 1+β)·R(θ₀)ᵀ`，`ω² = c² k_i M_{ij} k_j`：
- 矩阵构造 ✓
- 标量积 `k @ M @ k` ✓

🟢 一致。

---

## 6. 采样分布合理性

```python
BETA_MIN, BETA_MAX = 0.1, 0.8                # < 1 保正定
C_MIN, C_MAX = 50, 5000                       # m/s
beta = uniform(0.1, 0.8)
theta0 = uniform(0, π)                        # 主轴方向
theta_k = uniform(0, π)                       # 波传播方向
A = 0.1, k = 2, x_probe = 0.5
```

- β < 1 ⇒ M 本征值 `{1, 1+β} > 0` ⇒ 正定 ✓
- θ_0, θ_k 独立 uniform ⇒ 各向异性 visibility 随相对夹角变化
- c 跨 2 decade ✓

---

## 7. 安全约束 validator

```python
if not (BETA_MIN <= params.beta <= BETA_MAX): return False
if not (C_MIN <= params.c <= C_MAX): return False
if params.k <= 0 or params.A <= 0: return False
```

- β 范围严格 ⇒ M 正定 ⇒ 双曲，CFL OK ✓
- 无显式正定检查（β > 0 自动保证）

🟢 OK。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：2D wave 描述；measure 读 `(u, ω)`。

**🟡 信息泄漏**：step 输出 `omega`（同 γ-8-1）⇒ 直接给频率。

**Agent 看不到**：shift label、`β, θ_0` 数值、"anisotropic"motif。

**Agent 必须发现**：
1. 不同 θ_k 给出不同 ω ⇒ 各向异性
2. ω(θ_k) 是 cos²(θ_k - θ_0) 形式 ⇒ 推 θ_0
3. 拟合 (β, θ_0, c) 3 参数

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 介电张量到声学 |
| 公式数学正确 | ✅ | M 对称正定 + Hamilton 形式 |
| SO(2) 真破 | ✅ | M lab-fixed |
| T-trans / S-trans / PAR / T-rev / LIN / E 保留 | ✅ | 全部 |
| 代码 ↔ catalog 一致 | ✅ | R·D·R^T + k^T M k |
| 采样合理 | ✅ | β < 1 + θ 均匀 |
| 数值安全 | ✅ | β > 0 自动正定 |
| 信息泄漏防御 | 🟡 | step 输出 ω |

🟡 **改进点**（v2）：
1. step 输出移除 ω，仅返回 (u, du_dt)
2. 允许 AI 注入多 θ_k 探测协议
3. 与 γ-7-1 同源（都是 M 张量）— 可以共享 motif 检测器

---

**γ-8-2 verdict**：物理 / 代码 PASS；信息泄漏需 v2。

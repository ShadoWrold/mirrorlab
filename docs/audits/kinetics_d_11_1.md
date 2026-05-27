# δ-11-1: 反应动力学 暗通道分支 — 深度审查

> 域 11 / Reaction kinetics / δ-tier / shift_id = `delta_11_1`
> 代码：[`mirrorlab/shifts/kinetics_d_11_1.py`](../../mirrorlab/shifts/kinetics_d_11_1.py)
> Catalog Round-2 状态：APPROVED（`η ∈ [0.95, 1.05]` 邻域排斥已接受）

---

## 1. 原始定律：链反应 + 化学计量守恒

baseline `A → B` 链：
$$\frac{dC_A}{dt} = -k C_A^n, \quad \frac{dC_B}{dt} = +k C_A^n$$

**化学计量守恒**：
$$\frac{d(C_A + C_B)}{dt} = 0 \Rightarrow C_A + C_B = \text{const}$$

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：制造 "总摩尔损耗到暗通道 / 热" 的非标准副反应。

**改法**：
$$\frac{dC_A}{dt} = -k C_A^n, \quad \frac{dC_B}{dt} = +\eta \cdot k C_A^n, \quad \eta \neq 1$$

- `η < 1`：B 生成不足 → 净损 → 暗通道吸热
- `η > 1`：B 生成过量 → 净增 → 暗通道供质（"反向"图像，与 Part A δ 双符号风格一致）

**关键性质**：
- `η = 1` 完全退化到 baseline → 必须排斥邻域防 baseline 混淆
- `η` 跨 1 双侧随机 → 与具体核物理 / 化学标准分支表不重叠 ✓
- 与 Part A δ-5-1 (Q 泄漏) 同源 "守恒律 leakage" motif，跨域 anchor

---

## 3. 哪条对称性被破了？

**目标**：**只破化学计量守恒**。

baseline：`d(C_A + C_B)/dt = -kC_A^n + kC_A^n = 0` ✓。

shift：
$$\frac{d(C_A + C_B)}{dt} = -kC_A^n + \eta k C_A^n = (\eta - 1) k C_A^n$$

当 `η ≠ 1` 且 `C_A > 0`，**化学计量真破**。✓

积分：`(C_A + C_B)(t) - (C_A + C_B)(0) = (η-1) ∫_0^t k C_A(s)^n ds`，单调（符号取决于 `η-1`）。

> 化学计量破缺的精确数学位置：B 通道速率前的 `η` 因子。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程不显含 `t` → time-shift 不变 ✓

### Arrhenius
- `k` 仍 Arrhenius `A e^{-E_a/RT}` ✓

### 正定性
- `dC_A/dt < 0` 当 `C_A > 0` → `C_A → 0` 单调减
- `dC_B/dt > 0` 当 `C_A > 0` → `C_B` 单调增（甚至超过 `C_A(0)` 当 `η > 1`，但有限有界）✓

### 稀释 scale 在 `n = 1` 极限
- `n = 1` 时 `dC_A/dt = -kC_A` ⇒ `C_A → λC_A` 严格 scale-invariant
- `dC_B/dt = +η k C_A` ⇒ 同 scale → 保 ✓

### dimensional homogeneity
- 两侧 `mol·m⁻³·s⁻¹` ✓

---

## 5. 代码实现逐行核对

```python
def rhs(t, y):
    CA, CB = y
    r = p.k * max(CA, 0.0) ** p.n
    return (-r, p.eta * r)

sol = solve_ivp(rhs, (0.0, t_max), [p.C_A0, p.C_B0], method="DOP853",
                rtol=1e-9, atol=1e-12, dense_output=True)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `r = k * C_A^n` | 反应速率 | ✓ |
| `(-r, η*r)` | `(dC_A/dt, dC_B/dt) = (-r, ηr)` | ✓ |
| `max(CA, 0.0)` | 正定保护 | ✓ |

**完全一致**。

---

## 6. 采样分布合理性

```python
N_MIN, N_MAX = 0.8, 2.0
K_MIN, K_MAX = 1e-4, 1e-1     # LogUniform

n ~ Uniform(0.8, 2.0)
k ~ LogUniform(1e-4, 1e-1)
# 双段 η: 跳过 [0.95, 1.05]
if rng < 0.5: eta ~ Uniform(0.55, 0.95)
else:         eta ~ Uniform(1.05, 1.45)
C_A0=1, C_B0=0
```

- **`n ∈ [0.8, 2.0]`**：常见反应阶；避开 0.5 / 3 极端 ✓
- **`k ∈ [10⁻⁴, 10⁻¹]`** LogUniform：跨 3 个数量级 ✓
- **`η` 双段跳过 `[0.95, 1.05]`**：50/50 双向选择 → 跨 1 对称 ✓
  - `η ∈ [0.55, 0.95]`：净损 5%–45%
  - `η ∈ [1.05, 1.45]`：净增 5%–45%
  - **邻域排斥宽度 0.05** 足够避免 baseline 混淆 ✓
- **`C_A0 = 1` 固定**：单一初值；agent 通过 `C_A + C_B vs t` 即可揭示破缺

**🟡 改进点（v2）**：
1. `n` 避开 `{1.0, 2.0}` 整数邻域防 lookup
2. `C_A0` 加入采样（特别是与 `k` 配合改变反应时标）

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (N_MIN <= params.n <= N_MAX): return False
    if not (K_MIN <= params.k <= K_MAX): return False
    if 0.95 <= params.eta <= 1.05: return False   # 邻域硬排斥
    if not (0.55 <= params.eta <= 1.45): return False
    if params.C_A0 <= 0: return False
    return True
```

- 边界检查 ✓
- **`η ∈ [0.95, 1.05]` 双重排斥**：sampler 端跳过 + validator 端硬拦截 → R2 接受的邻域排斥严格执行 ✓
- `η ∈ [0.55, 1.45]` 上下界限定 → `C_B` 有界 ≤ `1.45 · C_A(0) = 1.45` → 数值不发散 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 反应场景 `(C_A(t), C_B(t))` 时间序列
- 32 工具

**藏**：
- shift label `δ-11-1 / stoichiometry broken`
- `η` 参数与"暗通道"图像
- "B 速率 ≠ A 消耗" 这一事实

**Agent 必须发现**：
1. 测 `C_A + C_B` vs `t` → baseline 应为常数；shift 单调（增或减）→ 破化学计量
2. 拟合 `(C_A + C_B)(t) - (C_A + C_B)(0)` 与 `∫ k C_A^n ds` 比值 → 揭示 `η - 1`
3. `η > 1` 反向图像注意（不能只想着"损失"）

**Bonus**：`broken_symmetry: "stoichiometry"` 或 `"mass"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | hidden-channel motif；与 Part A δ-5-1 / Part B δ-12-1 同源 |
| 公式数学正确 | ✅ | 化学计量破缺 = `(η-1) k C_A^n` |
| 化学计量真破 | ✅ | 当 `η ≠ 1, C_A > 0` |
| 其他对称性保留 | ✅ | T-trans / Arrhenius / 正定性 / 稀释 scale (n=1) |
| 代码 ↔ catalog 一致 | ✅ | DOP853 高精度 |
| 采样分布合理 | ✅ | `η` 双段 + 邻域排斥严格 |
| 数值安全 | ✅ | `C_B ≤ 1.45·C_A(0)` 有界 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `n` 整数邻域排斥
2. `C_A0` 加入采样

---

**δ-11-1 verdict**：物理 / 代码 / 设计**全 PASS**（`η` 双段采样设计严密）。

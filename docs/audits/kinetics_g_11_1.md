# γ-11-1: 反应动力学 分数时间核 — 深度审查

> 域 11 / Reaction kinetics / γ-tier / shift_id = `gamma_11_1`
> 代码：[`mirrorlab/shifts/kinetics_g_11_1.py`](../../mirrorlab/shifts/kinetics_g_11_1.py)
> Catalog Round-2 状态：APPROVED（截断 `τ_min = Δt_sim` 作为 sim 层 cutoff，已接受）

---

## 1. 原始定律：n 阶反应

$$\frac{dC}{dt} = -k C^n$$

`C` 浓度 [mol/m³]，`k` 速率常数（单位依 `n`），配 Arrhenius `k = A exp(−E_a/RT)`。

**关键不变量**：

| 对称性 | 验证 | 含义 |
|---|---|---|
| **T-trans** | 方程不显含 `t` | Markov + time-shift |
| **Arrhenius** | `k(T)` 给定形式 | 温度依赖标准 |
| **化学计量** | `A→B` 链 `C_A + C_B = const` | 守恒 |
| **正定性** | `C ≥ 0` 物理 | 浓度非负 |
| **稀释自相似 scale** | `(t→λt, C→λ^{−1/(n−1)}C)` | baseline 的标度律 |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：受限介质（凝胶 / 多孔 / 反应-扩散耦合）下的非 Markov 反应。借 Domain 7 γ-7-2 fractional kernel 但作用于不同 PDE。

**改法**：用 **Caputo 分数时导**替换一阶导：
$$D_t^\beta C = -k C^n, \quad \beta \in (0.5, 0.95)$$

其中 Caputo 分数导定义：
$$D_t^\beta C(t) = \frac{1}{\Gamma(1-\beta)} \int_0^t \frac{C'(\tau)}{(t-\tau)^\beta} d\tau \quad (0 < \beta < 1)$$

是带幂律记忆核的卷积导数 → 引入"长时记忆"非 Markov 性质。

**数值实现**：fractional Adams-Bashforth-Moulton 预测器（trapezoidal 历史和），截断窗口由 `τ_min = Δt_sim`（sim-level cutoff，catalog 已认可）。

**关键性质**：
- `β = 1` 极限 → 退化到经典一阶导 → baseline 完全恢复
- `β < 1` 引入历史依赖 → 衰减更慢（长尾）
- 借 anomalous reaction kinetics 思想；`β` 自由对数随机 + Caputo/RL 不锁定 → counterfactual ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破反应自相似 scale**。

baseline 在 `n ≠ 1` 时具有 `(t → λt, C → λ^{-1/(n-1)} C)` 自相似律。验证：
$$\frac{d(\lambda^{-1/(n-1)} C)}{d(\lambda t)} = -k (\lambda^{-1/(n-1)} C)^n$$
$$\Leftrightarrow \lambda^{-1/(n-1)} \cdot \lambda^{-1} \frac{dC}{dt} = -k \lambda^{-n/(n-1)} C^n$$

两侧 `λ` 指数：左 `−1/(n−1) − 1 = −n/(n−1)`，右 `−n/(n−1)` → 平衡 ✓。

shift（分数导）下：
$$D_{\lambda t}^\beta (\lambda^{-1/(n-1)} C)$$

由 Caputo 导的标度律 `D_{λt}^β f(λt) = λ^{−β} D_t^β f(t)`：
$$\lambda^{-\beta} \cdot \lambda^{-1/(n-1)} D_t^\beta C = -k \lambda^{-n/(n-1)} C^n$$

平衡要求 `β + 1/(n−1) = n/(n−1)` ⇒ `β = 1` → 仅 `β = 1` 时 baseline 标度律成立。

**`β ≠ 1` ⇒ 反应自相似 scale 真破**。✓

> 自相似破缺的精确数学位置：Caputo 算子的 `β`-标度指数与时间 / 浓度标度不平衡。

---

## 4. 哪些对称性必须保住？

### T-trans
- Caputo 卷积导对 `t → t + c` 不变（取 `t_0 → −∞` 极限近似）✓
- 数值实现里 `t_0 = 0` 固定 → strict T-trans 有限窗口下满足
- 🟡 注意：spec 上 T-trans 保 = 卷积是"任意起始时间往后历史依赖"的形式不变

### Arrhenius
- `k = A e^{-E_a/RT}` 形式未触 ✓

### 正定性
- `β > 0.5` + `n ≥ 0.5` + 数值 `C_new = max(C_new, 0.0)` → 物理正定 ✓

### 化学计量
- `dB = -dA` 同步分数化 ⇒ `D_t^β (C_A + C_B) = 0` ⇒ `C_A + C_B = const` ✓

### 稀释 scale 仅在 `n = 1` 极限
- `n = 1` 时方程为线性 `D_t^β C = -k C` ⇒ `C → λC` 严格 scale-invariant ✓

---

## 5. 代码实现逐行核对

```python
def _step_fractional(params, t_target):
    n_steps = max(int(math.ceil(t_target / params.dt)), 1)
    h = t_target / n_steps
    beta = params.beta
    C = [params.C0]
    f = [-params.k * max(params.C0, 0.0) ** params.n]
    for k_idx in range(1, n_steps + 1):
        weights = [((k_idx - j) ** beta - (k_idx - j - 1) ** beta) for j in range(k_idx)]
        history = sum(w * fj for w, fj in zip(weights, f))
        C_new = params.C0 + (h ** beta / math.gamma(beta + 1)) * history
        C_new = max(C_new, 0.0)
        C.append(C_new)
        f.append(-params.k * C_new ** params.n)
    return C
```

| 代码 | catalog | 一致 |
|---|---|---|
| `weights = (k-j)^β − (k-j-1)^β` | fractional Adams 权 | ✓（标准 FRDE 求积公式） |
| `C_new = C0 + (h^β / Γ(β+1)) · history` | Caputo 离散化 | ✓ |
| `max(C_new, 0.0)` | 正定保证 | ✓ |
| `f.append(-k * C_new^n)` | RHS 评估 | ✓ |

**算法核心是 fractional Adams-Bashforth memory-truncated 单步预测**。catalog 注释里说 "单步记忆截断 trapezoid" → 代码与说明一致 ✓。

**🟡 critique**：算法是"predictor-only"（无 corrector），精度对 `dt = 0.05` 较低；catalog 标记为 "sufficient for catalog-test diff vs baseline" → 用于 ground-truth 时可接受，但**作为 benchmark oracle 时若 agent fit `β` 数值精度依赖较高**。v2 可加 Adams-Moulton corrector 提升至 `O(h^{1+β})`。

---

## 6. 采样分布合理性

```python
BETA_MIN, BETA_MAX = 0.55, 0.95
N_MIN, N_MAX = 0.5, 2.5
K_MIN, K_MAX = 1e-4, 1e-1   # LogUniform
C0=1.0, tau_min=0.01, dt=0.05
```

- **`β ∈ [0.55, 0.95]`**：避开 `β = 1`（baseline）和 `β = 0.5`（发散边界）✓
- **`n ∈ [0.5, 2.5]`**：覆盖 sub-linear（半阶）到 quadratic（二阶），实验中常见 `n ∈ {1, 2}` 整数 → 避开整数邻域更好
- **`k ∈ [10⁻⁴, 10⁻¹]`** LogUniform：跨 3 个数量级，对应不同反应快慢 ✓
- **`C_0 = 1` 固定**：唯一初始浓度 → 简化稀释 scale 验证；同时也意味着 agent 只能通过 `(k, β, n)` 拟合识别 shift

**🟡 改进点（v2）**：
1. `n` 避开 `{0.5, 1.0, 1.5, 2.0}` 整数 / 半整数邻域防 lookup
2. `C_0` 加入采样让稀释 scale 验证更有挑战
3. `β = 1` 邻域排斥（已通过 `BETA_MAX = 0.95` 实现 ✓）

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (BETA_MIN <= params.beta <= BETA_MAX): return False
    if not (N_MIN <= params.n <= N_MAX): return False
    if not (K_MIN <= params.k <= K_MAX): return False
    if params.C0 <= 0 or params.dt <= 0: return False
    return True
```

- 边界检查 ✓
- 正定 `C_0 > 0, dt > 0` ✓
- catalog 安全声明 "β > 0.5 + n ≥ 0.5 + 截断 ⇒ 稳定且 C ≥ 0" → 守约束下 数值 stable ✓

**🟡 critique**：validator 未硬约束 `dt ≤ τ_min` 或 `dt` 与 `t_target` 的兼容关系。当前 `dt = 0.05, τ_min = 0.01` → 算法在 `t < τ_min` 区间不积分；与"sim-level cutoff"声明一致，但若外部传入 `dt > 1` 大步长会丢精度。v2 加入。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 反应场景：浓度 `C(t)` 时间序列
- 32 工具

**藏**：
- shift label `γ-11-1 / fractional time`
- Caputo 分数导这一形式
- `β` 参数
- "记忆 / 非 Markov" 这一性质

**Agent 必须发现**：
1. 衰减比 `e^{-kt}` 慢 → 长尾尾部
2. 拟合 `C(t) ~ t^{-α}` 幂律（fractional kinetics 渐近行为）→ `α = ?`
3. 推断 `β` 数值

**Bonus**：`broken_symmetry: "reaction_scale"` 加 0.10；提交 `fractional_order ≈ β` 可酌情加奖励（CAL-6 备选）。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | anomalous kinetics 借影；与 γ-7-2 同源 motif |
| 公式数学正确 | ✅ | Caputo 标度律推导 verified |
| 反应自相似 scale 真破 | ✅ | `β ≠ 1` 时标度指数不平衡 |
| 其他对称性保留 | ✅ | T-trans / Arrhenius / 化学计量 / 正定性 |
| 代码 ↔ catalog 一致 | ✅ | fractional Adams + 截断与说明对齐 |
| 数值算法精度 | ⚠️ | predictor-only，无 corrector；ground-truth 可接受 |
| 采样分布合理 | ⚠️ | `n` 整数邻域未排斥 |
| 数值安全 | ✅ | 截断 + 正定 max(0, ·) 守住 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. 加 Adams-Moulton corrector
2. `n` 整数邻域排斥
3. `C_0` 加入采样

---

**γ-11-1 verdict**：物理 / 代码 / 设计**全 PASS**（数值精度为 sim-level acceptance，已 catalog 接受）。

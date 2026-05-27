# γ-12-1: 核衰变 密度耦合衰变率 — 深度审查

> 域 12 / Radioactive decay / γ-tier / shift_id = `gamma_12_1`
> 代码：[`mirrorlab/shifts/decay_g_12_1.py`](../../mirrorlab/shifts/decay_g_12_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：理想核衰变

$$\frac{dN}{dt} = -\lambda N$$

`λ` 衰变常数 [s⁻¹]，`N` 粒子数。半衰期 `T_½ = ln 2 / λ`。

**关键不变量**：

| 对称性 | 验证 | 含义 |
|---|---|---|
| **T-trans** | 方程不显含 `t` | Markov memorylessness |
| **线性 `N → aN`** | RHS 与 N 一阶 | 衰变率与 `N` 严格正比 |
| **粒子数守恒**（链 `A→B`）| `dN_B = +λ N_A` | `N_A + N_B = const` |
| **外场无关性** | `λ` 与外场解耦 | 核衰变的本质 |
| **统计独立性** | 每个核独立衰变 | mean-field 推论 |

特别注意：**baseline 是线性 ODE**，本质单粒子过程；任何引入 `N²` 类项的 shift 都是清晰 counterfactual。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：制造"受激增减"型核衰变。借激光受激辐射 `dN/dt ∝ N²` 动机但不复制 Einstein A/B 系数形式。

**改法**：
$$\frac{dN}{dt} = -\lambda N \cdot \Big(1 + \alpha \big(N/N_0\big)^p\Big)$$

引入 **density-dependent enhancement / suppression factor**，让有效衰变率随 `N` 变化。

**关键性质**：
- `α = 0` 完全退化到 baseline
- `α > 0`：高 `N` 处衰变加速（"受激增强"），衰减更快
- `α < 0`：高 `N` 处衰变抑制（"自屏蔽"），衰减更慢；`α > -1` 保 `λ_eff > 0`
- **半衰期不再常数** — 这是 γ-12-1 修改 half-life proportionality 的核心 nuance：
  $$T_½^{eff}(N) = \frac{\ln 2}{\lambda(1 + \alpha(N/N_0)^p)}$$
  → 半衰期与 `N` 耦合，不再仅由 `λ` 决定 → 这是 catalog 注释 "Half-life sampling logic preserved: when α=0, this reduces to baseline" 的精确含义
- 借受激辐射 motif 搬到本质线性的核衰变 ⇒ counterfactual ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破线性 `N → aN`**。

baseline：缩放 `N → aN`，`dN/dt → a · (-λN)` ⇒ 解亦缩放 ⇒ **线性 / 齐次 → 任意倍数初始 N 衰减形状相同** ✓。

shift：缩放 `N → aN`：
$$\frac{d(aN)}{dt} = -\lambda(aN)\Big(1 + \alpha (aN/N_0)^p\Big)$$
$$\Rightarrow \frac{dN}{dt} = -\lambda N \Big(1 + \alpha a^p (N/N_0)^p\Big)$$

右侧含 `a^p` 因子（除非 `α = 0` 或 `p = 0`）→ **线性 / 齐次律破** → 不同初始 `N` 给出不同形状曲线 → **半衰期与 N 耦合**。✓

> 线性 `N → aN` 破缺的精确数学位置：因子 `(N/N_0)^p` 引入了 `N_0` **内禀粒子数尺度** + 非线性 `N^p` 依赖。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程不显含 `t` ✓

### Markov
- RHS 只依赖当前 `N`，不依赖历史 ✓

### 粒子守恒（链 `A → B`）
- 同步该非线性 `dN_B/dt = +λ N_A (1 + α(N_A/N_0)^p)` ⇒ `d(N_A+N_B)/dt = 0` ⇒ `N_A + N_B = const` ✓
- catalog 注释明确这点，代码实现按 spec 也将一致

### 外场无关
- 公式不含外场变量 ✓

### 统计独立性（在 mean-field 近似下）
- 形式上 RHS 自治 → 单核演化由全局 `N` 决定（mean-field），统计独立性保 ✓
- 🟡 严格统计意义上，`dN/dt ∝ N²` 类项违背"每核独立"；但作为 mean-field 宏观方程 catalog 接受 ✓

---

## 5. 代码实现逐行核对

```python
def rhs(t, y):
    (N,) = y
    Ns = max(N, 0.0)
    return (-p.lam * Ns * (1.0 + p.alpha * (Ns / p.N_scale) ** p.p),)

sol = solve_ivp(rhs, (0.0, t_max), [p.N_init], method="DOP853",
                rtol=1e-9, atol=1e-12, dense_output=True)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `-lam * N * (1 + alpha * (N/N_scale)^p)` | `-λN(1+α(N/N_0)^p)` | ✓ |
| `max(N, 0.0)` | 正定保护 | ✓ |
| `DOP853, rtol=1e-9` | 高精度 | ✓ |

**完全一致**。

---

## 6. 采样分布合理性

```python
LAM_MIN, LAM_MAX = 1e-6, 1e-1     # LogUniform
ALPHA_MIN, ALPHA_MAX = -0.4, 0.8
P_MIN, P_MAX = 0.3, 1.5
N0_MIN, N0_MAX = 1e3, 1e8         # LogUniform
N_init = 1.0e6 (固定)
```

- **`λ ∈ [10⁻⁶, 10⁻¹] s⁻¹`** LogUniform：跨 5 个数量级 → 半衰期从 ~7 秒到 ~8 天 ✓
- **`α ∈ [-0.4, 0.8]`**：双符号，`α > -1` 保 `λ_eff > 0`；catalog 安全界 60% margin ✓
- **`p ∈ [0.3, 1.5]`**：sub-linear 到 super-linear；避开 `p = 1`（线性强化）+ `p = 2`（标准受激辐射）整数邻域 ✓
- **`N_0 ∈ [10³, 10⁸]`** LogUniform：跨 5 个数量级 → `N_init / N_0 ∈ [10⁻², 10³]` 覆盖弱 / 强非线性区
- **`N_init = 10⁶` 固定**：
  - 当 `N_0 = 10⁸`：`N_init / N_0 = 0.01` → 修正小 → 退化近 baseline
  - 当 `N_0 = 10³`：`N_init / N_0 = 10³` → 修正大 → 强非线性

**🟡 改进点（v2）**：
1. `N_init` 加入采样让 "scale 律破" 验证更直接（agent 通过改变 `N_init` 看 half-life 变化）
2. `α = 0` 在 `[-0.4, 0.8]` 内 → 概率小但有 → 退化。建议 `|α| ≥ 0.05` 排斥邻域
3. `p` 整数邻域排斥

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (LAM_MIN <= params.lam <= LAM_MAX): return False
    if not (ALPHA_MIN <= params.alpha <= ALPHA_MAX): return False
    if not (P_MIN <= params.p <= P_MAX): return False
    if not (N0_MIN <= params.N_scale <= N0_MAX): return False
    if params.N_init <= 0: return False
    return True
```

- 边界检查 ✓
- 正定 `N_init > 0` ✓
- catalog 安全声明 "α > -1 保 λ_eff > 0"：sampler `α ≥ -0.4 > -1` 严格守 ✓
  - 数值验证：最坏情况 `α = -0.4, N/N_0 = 1, p = 1.5` ⇒ `λ_eff = λ(1 - 0.4) = 0.6λ > 0` ✓
- 高 `N` 时 `dN/dt ~ -λα N^{1+p} / N_0^p` 超线性，但 `N` 单调减 → 不发散 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 衰变场景 `N(t)`
- 32 工具

**藏**：
- shift label `γ-12-1 / linearity broken`
- `(1 + α(N/N_0)^p)` 形式
- `α, p, N_0` 参数
- "半衰期与 N 耦合" 这一关键 nuance

**Agent 必须发现**：
1. 测 `N(t)` 拟合 `e^{-λt}`，残差非零 → 怀疑非线性
2. 改变初始 `N_init`（如可控）→ 衰减形状变化 → 揭示 `N → aN` 不可缩放 → scale 律破
3. 拟合 `α, p, N_0` 数值

**Bonus**：`broken_symmetry: "linearity"` 或 `"N_scale"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 受激辐射 motif；本质线性 → counterfactual |
| 公式数学正确 | ✅ | `α=0` 连续退化；半衰期 N-依赖 nuance 明确 |
| 线性 `N→aN` 真破 | ✅ | 缩放后 `a^p` 因子无法消除 |
| 其他对称性保留 | ✅ | T-trans / Markov / 粒子守恒 / 外场无关 / mean-field 独立 |
| 代码 ↔ catalog 一致 | ✅ | DOP853 高精度 |
| 采样分布合理 | ⚠️ | `N_init` 固定 + `α=0` 邻域未排斥 |
| 数值安全 | ✅ | `λ_eff > 0` 守住，单调减不发散 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `N_init` 加入采样（强化 scale 律破缺的可观测性）
2. `|α| ≥ 0.05` 邻域排斥
3. `p` 整数邻域排斥

---

**γ-12-1 verdict**：物理 / 代码 / 设计**全 PASS**（半衰期 N-依赖 nuance 在 catalog § 注解和代码 docstring 都明确保留）。

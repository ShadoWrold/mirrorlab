# δ-12-1: 核衰变 暗通道分支 — 深度审查

> 域 12 / Radioactive decay / δ-tier / shift_id = `delta_12_1`
> 代码：[`mirrorlab/shifts/decay_d_12_1.py`](../../mirrorlab/shifts/decay_d_12_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：链衰变 + 粒子守恒

baseline 链 `A → B`：
$$\frac{dN_A}{dt} = -\lambda N_A, \quad \frac{dN_B}{dt} = +\lambda N_A$$

**粒子守恒**：
$$\frac{d(N_A + N_B)}{dt} = 0 \Rightarrow N_A + N_B = \text{const}$$

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：仿"中微子 / 暗物质损失通道"但不复制标准模型分支比表。

**改法**：
$$\frac{dN_A}{dt} = -\lambda N_A, \quad \frac{dN_B}{dt} = +(1 - \xi) \lambda N_A$$

`ξ ∈ (0, 1)` 是分支比损失系数：A 全部衰变，但只有 `(1-ξ)` 进 B，`ξ` 进 hidden / dark 通道。

**闭式解**：
$$N_A(t) = N_A(0) e^{-\lambda t}$$
$$N_B(t) = N_B(0) + (1-\xi)\big[N_A(0) - N_A(t)\big]$$

**关键性质**：
- `ξ = 0` 完全退化到 baseline
- `ξ ∈ [0.05, 0.45]` → 损失 5%–45% 进暗通道
- 与 Part A δ-5-1 (Q 泄漏) / Part B δ-11-1 (化学计量) 同源 "守恒律 leakage" motif，三域 anchor ✓
- 不复制标准模型 branching ratio 表（无明确核素） → counterfactual ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破粒子数守恒**。

baseline：`d(N_A + N_B)/dt = -λN_A + λN_A = 0` ✓。

shift：
$$\frac{d(N_A + N_B)}{dt} = -\lambda N_A + (1-\xi)\lambda N_A = -\xi \lambda N_A$$

当 `ξ > 0` 且 `N_A > 0`，**粒子守恒真破**（单调减）。✓

积分：`(N_A + N_B)(t) = (N_A + N_B)(0) - ξ · (N_A(0) - N_A(t))` → 总损失上界为 `ξ · N_A(0)`。

> 粒子守恒破缺的精确数学位置：B 通道速率前的 `(1-ξ)` 因子（缺的 `ξ` 部分入 dark）。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程不显含 `t` → time-shift 不变 ✓

### Markov
- A 自身演化只依赖当前 `N_A` ✓

### 线性 `N → aN`
- A 方程 `dN_A/dt = -λN_A` → 缩放 `N_A → aN_A` 解亦缩放
- B 方程 `dN_B/dt = +(1-ξ) λ N_A` → 同 scale → 保 ✓

### 外场无关性
- `λ, ξ` 都是常数（不依赖外场）✓

### 统计独立性
- 形式上 RHS 自治线性 → 每核独立衰变 + 独立 branching → 严格保 ✓

---

## 5. 代码实现逐行核对

```python
def step(self, t):
    p = self._params
    N_A = p.N_A0 * math.exp(-p.lam * t)
    N_B = p.N_B0 + (1.0 - p.xi) * (p.N_A0 - N_A)
    return {"t": t, "N_A": N_A, "N_B": N_B}
```

| 代码 | catalog | 一致 |
|---|---|---|
| `N_A = N_A0 * exp(-λt)` | A 闭式解 | ✓ |
| `N_B = N_B0 + (1-ξ)(N_A0 - N_A)` | B 闭式解（积分得） | ✓ |

**完全一致**。**闭式解避免数值 ODE**，精度无误差。

---

## 6. 采样分布合理性

```python
LAM_MIN, LAM_MAX = 1e-6, 1e-1   # LogUniform
XI_MIN, XI_MAX = 0.05, 0.45

lam ~ LogUniform(1e-6, 1e-1)
xi ~ Uniform(0.05, 0.45)
N_A0 = 1e6, N_B0 = 0 (固定)
```

- **`λ ∈ [10⁻⁶, 10⁻¹]`** LogUniform：跨 5 个数量级 → 半衰期 7 秒到 8 天 ✓
- **`ξ ∈ [0.05, 0.45]`**：
  - 下界 0.05 避免 baseline 退化 ✓
  - 上界 0.45 → 最坏一半粒子入 dark，仍 < 0.5 防止 B 通道极弱 ✓
- **`N_A0 = 10⁶, N_B0 = 0`** 固定：与 γ-12-1 一致；线性 ODE 下 scale 不影响 shape

**🟡 改进点（v2）**：
1. `N_B0 = 0` 固定 → agent 总从空 B 通道开始；若 `N_B0 ≠ 0`，B 演化的"初始 offset" 可独立测试
2. `ξ` 是单符号（仅"损失"），与 Part B δ-11-1 双符号 `η` 设计风格不同；考虑统一为双段（包括"获得"图像）— 但物理上 dark channel "供质" 反向图像较弱，单符号也 OK

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (LAM_MIN <= params.lam <= LAM_MAX): return False
    if not (XI_MIN <= params.xi <= XI_MAX): return False
    if params.N_A0 <= 0: return False
    return True
```

- 边界检查 ✓
- 正定 `N_A0 > 0` ✓
- catalog 安全声明 "ξ ∈ (0, 1) ⇒ N_B 单调增到 `(1-ξ) · N_A(0)`；无发散"：当前 `ξ ∈ [0.05, 0.45]` 严格在 `(0, 1)` 内 ✓
- `N_B` 上界 `(1 - 0.05) · 10⁶ = 9.5 × 10⁵`，有限有界 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 衰变场景 `(N_A(t), N_B(t))`
- 32 工具

**藏**：
- shift label `δ-12-1 / particle conservation broken`
- `(1-ξ)` 因子与"暗通道"图像
- `ξ` 参数

**Agent 必须发现**：
1. 测 `N_A + N_B` vs `t` → baseline 应为常数；shift 单调减 → 破粒子守恒
2. 拟合 `(N_A + N_B)(t) / (N_A + N_B)(0)` 与 `N_A(t) / N_A(0)` 关系 → 揭示 `ξ`
3. 注意：A 的衰减仍是纯指数（`λ` 不变），破缺仅在 B 端

**Bonus**：`broken_symmetry: "particle_number"` 或 `"mass"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | dark-channel motif；三域跨 anchor (A δ-5-1, B δ-11-1, B δ-12-1) |
| 公式数学正确 | ✅ | 闭式解干净，无数值误差 |
| 粒子守恒真破 | ✅ | `d(N_A+N_B)/dt = -ξλN_A < 0` |
| 其他对称性保留 | ✅ | T-trans / Markov / 线性 / 外场无关 / 统计独立 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | 范围合理，邻域排斥严格 |
| 数值安全 | ✅ | 闭式解无发散；`N_B` 有界 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `N_B0` 加入采样（增加 offset 多样性）
2. 考虑 `ξ` 双符号化（统一 Part B δ-tier 风格）— 物理上不强需求，可选

---

**δ-12-1 verdict**：物理 / 代码 / 设计**全 PASS**（结构最简洁的 δ-tier，是 leakage motif 的 reference instantiation）。

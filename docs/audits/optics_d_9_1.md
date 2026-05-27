# δ-9-1: Snell 角度幂律能量泄漏 — 深度审查

> 域 9 / Geometric optics / δ-tier / shift_id = `delta_9_1`
> 代码：[`mirrorlab/shifts/optics_d_9_1.py`](../../mirrorlab/shifts/optics_d_9_1.py)
> Catalog Round-2 状态：APPROVED
> **人工二审 errata (2026-05-27)**：🔴 `step()` 输出 `R_plus_T` —— 能量预算 = 1 − leak，直接显示 E-break。同 δ-1-1 / δ-7-1 模式（[v2-todo TODO-2](../v2-todo.md)）。

---

## 1. 原始定律：Snell + 能量收支

角度律：`n_1 sin θ_i = n_2 sin θ_t`。
能量律（标量近似 Fresnel）：`R + T = 1`。

baseline 把"角度"和"强度"两套定律完全解耦，二者各自独立。该 shift **只动强度律**。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：仿 Part A δ-5-1 "field-gated leakage" — law 不变、附加守恒律破。在光学界面上做"角度依赖的能量泄漏 / 吸收"。

**改法**：
- 角度方程：**保持 Snell baseline**
- 强度方程：
$$R + T = 1 - \xi \cdot |\sin\theta_i|^p$$

`ξ` 可正可负：
- `ξ > 0`：能量"流失"到 hidden mode（吸收 / 倏逝）
- `ξ < 0`：能量"获得"（外部 hidden mode 耦合回主光路，物理上对应"散射进 → 再耦合回"图像）

**关键性质**：
- 角度律不变 → Snell-related 不变量全保
- 强度律变 → 只破能量守恒
- 与 Beer-Lambert（指数）、Fresnel（幅度平方）形式都不同 → counterfactual ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破能量守恒**（`R + T ≠ 1`）。

baseline：`R + T = 1`，输入光强 `I_i = R·I_i + T·I_i` 闭合。

shift：
$$R + T = 1 - \xi |\sin\theta_i|^p$$
$$\Rightarrow R\cdot I_i + T\cdot I_i = (1 - \xi|\sin\theta_i|^p)\cdot I_i \neq I_i$$

当 `ξ ≠ 0` 且 `θ_i ≠ 0`，**能量收支破缺**。✓

> 能量守恒破缺的精确数学位置：`(1 - ξ|sin θ_i|^p)` 中的 `-ξ|...|^p` 项。

---

## 4. 哪些对称性必须保住？

### Snell 角度律
- 代码 `s2 = p.n1 / p.n2 * sin(p.theta_i)` 严格 baseline ✓

### 互易性（损失系数对入 / 出射方向同）
- `|sin θ_i|^p` 在 `i ↔ t` 下用 Snell 角度律换算给出对称损失 → reciprocity 保留 ✓

### SO(2) 绕法线 / Fermat / 切向波矢 / 偏振 U(1)
- 角度律未动 → 全保留 ✓

### 介质交换 `1↔2`
- 损失只依赖 `|sin θ_i|^p`（绝对值幂律），不依赖介质标号 → 交换不变 ✓

---

## 5. 代码实现逐行核对

```python
def step(self, t: float):
    p = self._params
    s2 = p.n1 / p.n2 * sin(p.theta_i)
    theta_t = asin(s2) if -1.0 <= s2 <= 1.0 else nan
    leak = p.xi * abs(sin(p.theta_i)) ** p.p
    budget = 1.0 - leak  # = R + T
    return {"t": ..., "theta_t": ..., "R_plus_T": budget}
```

| 代码 | catalog | 一致 |
|---|---|---|
| `n1/n2 * sin(θ_i)` | Snell baseline | ✓ |
| `xi * abs(sin(θ_i))**p` | `ξ |sin θ_i|^p` | ✓ |
| `1.0 - leak` | `1 − ξ|sin θ_i|^p` | ✓ |

**完全一致**。`R_plus_T` 直接作为 observable 输出，agent 可直接量到能量收支。

---

## 6. 采样分布合理性

```python
XI_LO, XI_HI = -0.15, 0.40        # 双符号
P_MIN, P_MAX = 1.2, 3.0
n_1, n_2 ~ Uniform(1.0, 2.0) 独立
theta_i = 0.3 (固定)
```

- **`ξ ∈ [-0.15, 0.40]`**：单边 / 双符号，覆盖损失 + 增益两种 hidden-channel 图像 ✓
  - `ξ < 0` 上界 `|−0.15|·1 = 0.15` → `R+T ≤ 1.15`，与 catalog 安全界 1.5 一致
- **`p ∈ [1.2, 3.0]`**：1.2 接近线性，3.0 强角度依赖；避开 `p=2` 易识别整数值
- **`θ_i = 0.3 rad`**：`|sin 0.3|^p ∈ [0.296^3, 0.296^{1.2}] = [0.026, 0.22]`
  - `ξ_max · 0.22 ≈ 0.088` → 典型 `R+T = 0.91` 左右，明显偏离 1 ✓

**🟡 改进点（v2）**：
1. `ξ = 0` 在 `[−0.15, 0.40]` 端点开区间附近有概率采到极小值 → 破缺信号弱。建议 `|ξ| ≥ 0.05` 排斥邻域。
2. `θ_i` 固定 → 只能在单角度上观察损耗。scan `θ_i` 是 agent 揭示 `|sin θ_i|^p` 形式的关键手段，建议 `θ_i` 加入采样。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (XI_LO <= params.xi <= XI_HI): return False
    if not (P_MIN <= params.p <= P_MAX): return False
    if params.n1 <= 0 or params.n2 <= 0: return False
    return True
```

- 边界检查 ✓
- 正定性：`n_1, n_2 > 0` ✓
- **未检 `R, T ∈ [0, 1.5]`** 范围：当前采样 `ξ ∈ [-0.15, 0.40], θ_i = 0.3`，`R+T = 1 - ξ|sin 0.3|^p ∈ [0.91, 1.04]`，**远在 [0, 1.5] 内** ✓
- **🟡 critique**：validator 对 `ξ`、`p` 的范围检查依赖 sampler 边界，与 catalog `|ξ| < 0.5` 总安全条件没做硬约束。若 v2 把 `θ_i` 放开到接近 `π/2`，需要复算 `|R+T|` 上界。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 光学界面，可观测 `θ_t` 与 `R+T`（intensity budget）
- 工具集 32 个

**藏**：
- shift label `δ-9-1 / energy non-conservation`
- 公式 `1 - ξ|sin θ_i|^p`
- `ξ`、`p` 参数值
- "角度律未改、强度律改" 这个非对称性

**Agent 必须发现**：
1. 通过测 `R+T` 偏离 1 → 怀疑能量守恒破缺
2. 通过 scan `θ_i` 拟合幂律 → 揭示 `|sin θ_i|^p` 形式
3. `ξ` 双符号 → 注意"获得"图像不只是吸收

**Bonus**：`broken_symmetry: "energy"` 加 0.10 分。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | δ-5-1 跨域 anchor，hidden-channel motif |
| 公式数学正确 | ✅ | 角度律 / 强度律解耦，破缺定位干净 |
| 能量守恒真破 | ✅ | `R+T ≠ 1` 当 `ξ ≠ 0, θ_i ≠ 0` |
| Snell / 其他对称性保留 | ✅ | 角度律未动 → 全保 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ⚠️ | `θ_i` 固定 + `ξ → 0` 邻域未排斥 |
| 数值安全 | ✅ | `|R+T| ∈ [0.91, 1.04]` 当前采样 |
| 信息泄漏防御 | ✅ | shift label / 公式 / 参数全藏 |

**🟡 改进点**（v2）：
1. `|ξ| ≥ 0.05` 邻域排斥避免 baseline 退化
2. `θ_i` 加入采样，放大幂律可观测性
3. validator 对 `R+T` 上下界加硬约束（外部 params 防御）

---

**δ-9-1 verdict**：物理 / 代码 / 设计**全 PASS**（采样优化为 v2 待办）。

# γ-9-1: Snell 偏振调制折射率 — 深度审查

> 域 9 / Geometric optics / γ-tier / shift_id = `gamma_9_1`
> 代码：[`mirrorlab/shifts/optics_g_9_1.py`](../../mirrorlab/shifts/optics_g_9_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：Snell + 标量近似

**Snell 折射定律**：
$$n_1 \sin\theta_1 = n_2 \sin\theta_2$$

界面上入射 / 出射方向的切向波矢守恒。Fresnel 标量近似下 `R + T = 1`（能量收支闭合）。

**对称性结构**（标量 Snell baseline 拥有的）：

| 对称性 | 验证 | 物理含义 |
|---|---|---|
| **偏振 U(1)** | `n` 不含 `θ_pol` | 旋转偏振面光路不变 |
| **互易性 / Reciprocity** | 角度方程在 `i↔t` 交换下对称 | 光路时间反演 |
| **介质 `1↔2`** | 交换 `(n₁, θ₁) ↔ (n₂, θ₂)` 公式同形 | 物理界面无内禀朝向 |
| **SO(2) 绕法线** | 角度只关心入射面 | 绕法线轴旋转不变 |
| **Fermat** | `θ` 由极值原理给出 | 平稳光程 |
| **能量** | `R + T = 1` | 标量 Fresnel 闭合 |

标量 Snell 是完美 polarization-isotropic 的界面定律。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：crystal birefringence 借影 — 单 / 双轴晶体里 `n` 随偏振角变化。

我们的改法（**borrow not copy**：不照抄 `n_e, n_o` 双折射张量公式）：
$$n_{\text{eff}}(\theta_{\text{pol}}) = n_0 + \delta n \cdot \sin^2(2\theta_{\text{pol}} - \varphi)$$

Snell 改为：
$$n_1 \sin\theta_1 = n_{\text{eff}}(\theta_{\text{pol}}) \sin\theta_2$$

拆开看：
- `n_0` = 各向同性基底（标准折射率）
- `δn · sin²(2θ_pol − φ)` = 偏振门控修正，**周期 π**（双瓣形）

**关键性质**：
- `sin²(2θ_pol−φ)` 周期 `π`，与标准单轴 `cos²θ_pol`（周期 2π）形式上正交
- 振幅 `δn ∈ [0.02, 0.30]`，`n_eff` 总在 `[n_0, n_0+δn]` 之间，恒正
- lookup attacker 一查 "uniaxial birefringence" 拿到 `n_e cos² + n_o sin²` 这种公式 → 与我们的双瓣形不重合 → counterfactual ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破偏振 U(1)**。

U(1) 操作：`θ_pol → θ_pol + Δ`，物理结果应不变。

验证：
$$n_{\text{eff}}(\theta_{\text{pol}} + \Delta) = n_0 + \delta n \cdot \sin^2(2\theta_{\text{pol}} + 2\Delta - \varphi)$$

当 `δn ≠ 0` 且 `Δ ∉ {0, π/2, π, ...}` 时 `n_eff` **改变** → `θ_2` 改变 → **U(1) 真破**。✓

本质：baseline 的 `n` 是 `θ_pol` 的零阶常函数；shift 引入显式 `θ_pol` 依赖（双瓣周期 π）。

> 偏振 U(1) 破缺的精确数学位置：`n_eff` 对 `θ_pol` 的非零导数。

---

## 4. 哪些对称性必须保住？

### 互易性 / Reciprocity
- 固定 `θ_pol` 后，方程 `n_1 sin θ_1 = n_eff sin θ_2` 在 `(1,θ_1) ↔ (2,θ_2)` 对称
- 光路可逆 ✓

### 介质 `1↔2` 交换
- 公式形上：把 `n_1 ↔ n_eff` 互换、`θ_1 ↔ θ_2` 互换 → 同形 ✓

### SO(2) 绕法线
- `n_eff` 只依赖 `θ_pol`（偏振面与法线的关系），与"绕法线把入射面整体旋转"无关 ✓

### Fermat / 切向波矢守恒
- Snell 律本身是 Fermat 推论；切向 `k_∥ = (ω/c) n sin θ` 在两侧相等（按定义保留）✓

### 能量 `R + T = 1`
- γ-9-1 不动 Fresnel 振幅，标量收支保留 ✓

**invariant-checker Round-2 复审：5/5 通过**。

---

## 5. 代码实现逐行核对

```python
def n_eff(params: OpticsGamma91Params) -> float:
    return params.n0 + params.dn * math.sin(2 * params.theta_pol - params.phi) ** 2

# Snell 用法
ne = n_eff(p)
s2 = p.n1 / ne * sin(p.theta1)
theta2 = asin(s2) if -1.0 <= s2 <= 1.0 else nan
```

逐符号对照 catalog `n_eff = n_0 + δn·sin²(2θ_pol − φ)`：

| 代码 | catalog | 一致 |
|---|---|---|
| `params.n0 + params.dn * ...` | `n_0 + δn · ...` | ✓ |
| `sin(2 * theta_pol - phi) ** 2` | `sin²(2θ_pol − φ)` | ✓ |
| `p.n1 / ne * sin(p.theta1)` | `sin θ_2 = (n_1/n_eff) sin θ_1` | ✓ |

**完全一致，无 bug**。`asin` 越界返回 `nan`（TIR 全反射）符合物理。

---

## 6. 采样分布合理性

```python
N0_MIN, N0_MAX = 1.3, 2.2        # n_0 ~ Uniform(1.3, 2.2)
DN_MIN, DN_MAX = 0.02, 0.30      # δn ~ Uniform(0.02, 0.30)
phi   ~ Uniform(0, π)
theta_pol ~ Uniform(0, π)
n1 = 1.0 (固定空气侧)
theta1 = 0.3 rad (固定 ≈ 17°)
```

- **`n_0 ∈ [1.3, 2.2]`**：覆盖玻璃 (1.5)、聚合物 (1.4)、蓝宝石 (1.77)、ZnS (2.2)，物理合理 ✓
- **`δn ∈ [0.02, 0.30]`**：双折射典型量级（方解石 ~0.17，BBO ~0.12，强 LC ~0.30）✓
- **`δn / n_0 ≤ 0.23`**：相对调制不过载，TIR 临界角偏移有限
- **`φ ∈ [0, π)`** 配 `sin²(...)` 周期 π → 全相位覆盖且无重复 ✓
- **`θ_pol ∈ [0, π)`** 同理覆盖完整偏振相空间 ✓
- **`θ_1 = 0.3 rad` 固定**：`sin θ_1 ≈ 0.296`，与 `n_2 ∈ [1.32, 2.5]` 配合，`sin θ_2 ∈ [0.12, 0.22]` 远离 TIR 边界 ✓

**🟡 改进点（v2）**：`θ_1` 单点固定 → seed 间多样性来自 `(n_0, δn, φ, θ_pol)`。若要测 TIR 边界附近的 PAR-break 增强，可把 `θ_1` 也加入采样（Uniform(0.1, 0.5)）。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (N0_MIN <= params.n0 <= N0_MAX): return False
    if not (DN_MIN <= params.dn <= DN_MAX): return False
    if params.n1 <= 0: return False
    return True
```

- 边界检查：sampler 已守，validator 双保险 ✓
- 正定性：`n_eff = n_0 + δn · [0,1] ∈ [1.3, 2.5] > 0` 恒成立 ✓
- 未显式拒 TIR：当 `n_eff < n_1 sin θ_1` 时 `step()` 返回 `nan`（受控失败，非崩溃）✓

**🟡 critique**：`φ`、`θ_pol` 没在 validator 里 range-check。代码注释里说 sampler 会守，但若外部直接构 params 可能传入超出 `[0, π)` 的值 → 不影响 `sin²` 周期性，**无实际危害**，但破坏了"validator 是外部 params 防御"的语义一致性。v1 可忽略。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 物理场景描述（"一个光学界面，可调入射角与偏振角，观测折射角"）
- 32 个工具（measure / manipulate / analyze / knowledge）
- 量纲签名（角度无量纲）

**Agent 看不到**：
- shift label `γ-9-1` 或 `polarization U(1) broken`
- `sin²(2θ_pol − φ)` 双瓣形式
- 参数 `n_0, δn, φ`
- "这是被改过的 Snell" 这个事实

**Agent 必须自己发现的**：
1. 折射角随 `θ_pol` 周期性变化（baseline 不会）
2. 周期为 `π/2`？`π`？需要扫 `θ_pol` 并拟合
3. 拟合 `n_eff(θ_pol)` 的具体形式

**Bonus probe**：提交 `broken_symmetry: "polarization U(1)"` 加 0.10 分。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | birefringence 借影 + 双瓣形独创 |
| 公式数学正确 | ✅ | `n_eff` 恒正，周期 π 干净 |
| 偏振 U(1) 真破 | ✅ | `∂n_eff/∂θ_pol ≠ 0` |
| 其他 5 条对称性保留 | ✅ | reciprocity / 1↔2 / SO(2) / Fermat / R+T |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | 真实晶体量级 |
| 数值安全 | ✅ | `n_eff > 0` 恒成立，TIR 受控 nan |
| 信息泄漏防御 | ✅ | shift label / 公式 / 参数全藏 |

**🟡 改进点**（v2）：
1. `θ_1` 加入采样 → 更丰富的角度依赖测试
2. validator 给 `φ, θ_pol` 加 range-check → 外部 params 防御完整

---

**γ-9-1 verdict**：物理 / 代码 / 设计**全 PASS**。

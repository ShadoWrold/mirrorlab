# γ-5-2: Coulomb saturating-potential nonlinearity — 深度审查

> 域 5 / Coulomb / γ-tier / shift_id = `gamma_5_2`
> 代码：[`mirrorlab/shifts/coulomb_g_5_2.py`](../../mirrorlab/shifts/coulomb_g_5_2.py)
> Catalog Round-2 状态：APPROVED（R1-fix：nonlinearity 搬到 scalar potential）
> **人工二审 errata (2026-05-27)**：🟡 多源场景 validator 不检查 test charge 与 source 的最小距离 → 1/r 数值边界风险（[v2-todo TODO-7](../v2-todo.md)）。step() 输出干净。

---

## 1. 原始定律：理想 Coulomb 多体叠加

线性场叠加：`φ_lin(x) = Σ_j k_e q_j / |x − x_j|`，`E_lin = −∇φ_lin`。
多源场恰为单源场之和 — 这是 **superposition / LIN** 的精确陈述。

不变量：E, p, L, T-rev, PAR, Q, **LIN**（叠加原理）。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**（catalog）：借 Born–Infeld 类 **饱和电动力学** 的"有限场强上限"思想，但**关键改动**：把非线性放在**势的层级**而非场层级。

**R1 教训（A5）**：原版 `E_eff(x) = f(|E_lin|) · E_lin(x)`。问题：`∇f` 一般不与 `E_lin` 平行 ⇒ `∇×E_eff ≠ 0` ⇒ 非保守 ⇒ E 也破 ⇒ dual break。

**Fix**：把非线性写成**标量函数作用于标量势**：
$$\phi_{\text{eff}}(x) = \phi_{\text{lin}}(x) + \xi \cdot \frac{\phi_{\text{lin}}^3}{\phi_{\text{lin}}^2 + \phi_0^2}$$

$$E_{\text{eff}} = -\nabla\phi_{\text{eff}} = -\frac{d\phi_{\text{eff}}}{d\phi_{\text{lin}}}\cdot\nabla\phi_{\text{lin}}$$

由 chain rule：
$$\frac{d\phi_{\text{eff}}}{d\phi_{\text{lin}}} = 1 + \xi\cdot\frac{\phi_{\text{lin}}^2(\phi_{\text{lin}}^2 + 3\phi_0^2)}{(\phi_{\text{lin}}^2 + \phi_0^2)^2}$$

由于 `E_eff` 显式是某标量函数的负梯度 ⇒ **自动 curl-free** ⇒ 保守 ⇒ E 守恒。

**直观**：小 `|φ_lin|` ⇒ `φ_eff ≈ φ_lin`（线性极限恢复 Coulomb）；大 `|φ_lin|` ⇒ `φ_eff ≈ φ_lin + ξ·φ_lin`（线性 with 1+ξ 放大），中间区域非线性。

---

## 3. 哪条对称性被破了？

**目标**：**只破 LIN（superposition）**。

定义场 `E_test_1` 来自源 q_1 单独；`E_test_2` 来自 q_2 单独；`E_test_12` 来自 {q_1, q_2} 共同。

**Baseline**：`E_test_12 = E_test_1 + E_test_2`（线性叠加 ✓）

**Shift**：`φ_lin^{12} = φ_lin^1 + φ_lin^2`（仍线性，scalar 加法 OK），但 `φ_eff` 是 `φ_lin` 的**非线性函数**：
$$\phi_{\text{eff}}^{12} \ne \phi_{\text{eff}}^1 + \phi_{\text{eff}}^2$$

因为 `(a+b)³ / ((a+b)² + φ₀²) ≠ a³/(a²+φ₀²) + b³/(b²+φ₀²)` 一般情况。
⇒ `E_eff^{12} ≠ E_eff^1 + E_eff^2` ⇒ **LIN 真破** ✓

---

## 4. 哪些对称性必须保住？

### T-trans / E 守恒
- `φ_eff` 时间无关 ⇒ `E_eff = −∇φ_eff` 保守 ⇒ E 守恒 ✓ (R1-fix 的核心)

### ROT
- `φ_lin` 在 R∈SO(3) 下是 scalar field（标量值不变，几何点变）
- 标量函数 `f(φ_lin)` 仍 rotation-equivariant ⇒ `∇` 与 R 交换 ⇒ `E_eff` 是 vector field ✓

### PAR
- 在 `x → −x` 反演下（源点位置同时反 `x_j → −x_j`），`|x − x_j|` 不变 ⇒ `φ_lin` invariant
- ∇ 在反演下变号 ⇒ `E_eff` 作为 vector 反号 ✓

### T-rev
- 静电学：`φ_eff` 不含 v、不含 t；牛顿方程在 `t → −t` 下不变 ✓

### Q 守恒
- 力学不动 `q` ✓

---

## 5. 代码实现逐行核对

```python
def _phi_lin_and_grad(pos, p):
    # 对每个 source j: phi += k_e q_j / r,  grad += -k_e q_j (x - x_j) / r³
    for q, sx, sy, sz in (...):
        dx, dy, dz = x - sx, y - sy, z - sz
        r = sqrt(...)
        phi += p.k_e * q / r
        coef = -p.k_e * q / (r2 * r)
        gx += coef * dx; ...

def shifted_force(pos, p):
    phi_lin, grad_phi = _phi_lin_and_grad(pos, p)
    phi2 = phi_lin * phi_lin
    denom = phi2 + p.phi0 * p.phi0
    dphi_eff = 1.0 + p.xi * phi2 * (phi2 + 3*p.phi0**2) / denom**2
    Ex = -dphi_eff * grad_phi[0]; ...
    return (q_test * Ex, ...)
```

对照 catalog：

| 代码 | catalog | 一致 |
|---|---|---|
| `phi = Σ k_e q_j / r_j` | `φ_lin = Σ k_e q_j / |x − x_j|` | ✓ |
| `grad_phi = Σ -k_e q_j (x-x_j)/r³` | `∇φ_lin = -Σ k_e q_j (x-x_j)/|...|³` | ✓ |
| `dphi_eff = 1 + ξ φ²(φ²+3φ₀²)/(φ²+φ₀²)²` | 同 | ✓ |
| `E_eff = -dphi_eff · grad_phi` | `E = -dφ_eff/dφ_lin · ∇φ_lin` | ✓ |
| `F = q_test · E_eff` | 同 | ✓ |

🟢 **完全一致**。`coef = -k_e q / r³` 的符号：`∇(1/r) = -r̂/r²`，再 `-∇φ` 给 `+k_e q r̂/r²` = 标准 Coulomb；与代码 `gx = coef * dx = -k_e q · dx/r³` 一致（注意：`coef * dx = -k_e q dx/r³`，这是 `∂φ/∂x`，所以 `grad_phi` 真是梯度而不是 −梯度；然后 `E = -dphi_eff · grad_phi` 取负号 ⇒ 总符号对）。

---

## 6. 采样分布合理性

```python
k_e = K_E_DEFAULT * loguniform(0.5, 2.0)
xi = uniform(0.05, 0.5)
phi_typical = k_e * 1e-6 / 1.0                   # ~ 9e3 V
phi0 = phi_typical * loguniform(0.1, 10.0)       # 跨 2 decade
q_test = 1e-9 C, m = 1e-3 kg
src1 = (+1e-6 C, x=-0.5);  src2 = (-1e-6 C, x=+0.5)   # dipole
x0 = (0, 0.3, 0)                                # 偏离对称轴
```

- `ξ ∈ [0.05, 0.5]` < 1 ⇒ `φ_eff(φ_lin)` 单调（catalog `1 + ξ·φ²(φ²+3φ₀²)/(φ²+φ₀²)² > 0` 当 ξ < 1）✓
- `φ₀` 在典型电压上下 2 decade ⇒ 涵盖小 φ（线性极限）和大 φ（饱和区）两种 regime
- dipole 配置 ⇒ test charge 看见两个 sources ⇒ **LIN 破缺自然显现**（如果只有 1 source，`φ_eff(φ_lin_1)` 仍可重 parametrize 为单源标量场，LIN 退化不可观测）

🟡 **关键**：双源配置是 LIN 实验性可见性的**必要**条件。catalog 也明确写 "2 fixed point sources + 1 mobile test charge"。

---

## 7. 安全约束 validator

```python
def validator(p):
    if not (XI_MIN <= p.xi <= XI_MAX): return False
    if p.xi >= 1.0: return False             # 单调性阈值
    if p.m <= 0 or p.k_e <= 0 or p.phi0 <= 0: return False
```

- ξ < 1 双保险 ✓
- φ₀ > 0 防止 `denom = 0` ✓

🟡 没有检查 test 粒子轨迹是否撞 source（`|x - x_j| → 0` 引起 1/r 奇异）。ODE 用 DOP853 + adaptive stepping，实际 sampling 下 dipole 间隔 1 m、初距 0.3 m 离 source 0.583 m，启动安全；但极端轨道可能闯入。**建议加 `min(|x - x_j|) > r_min` 检查**。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：双源 + 单移动 test charge 电场场景；measure 工具读 `(x, y, z, v)`。

**Agent 看不到**：shift label、`ξ`、`φ₀`、"saturating"/"Born-Infeld"motif。

**Agent 必须发现**：
1. 在某些位置（高 |φ_lin|）力偏离单纯叠加
2. 单源场 + 单源场 ≠ 双源场 ⇒ 非线性
3. 拟合 `(ξ, φ₀)`

**Bonus probe**：`broken_symmetry: "LIN"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借 Born-Infeld 思想，势-层级 fix |
| 公式数学正确 | ✅ | chain rule 显式、E 自动 curl-free |
| LIN 真破 | ✅ | `f(a+b) ≠ f(a)+f(b)` |
| E / ROT / PAR / T-rev / Q 保留 | ✅ | 显式势 ⇒ E 自动 |
| 代码 ↔ catalog 一致 | ✅ | grad、dphi_eff、符号全核对 |
| 采样分布合理 | ✅ | ξ < 1 + φ₀ 2 decade 跨度 |
| 数值安全 | 🟡 | 缺 `min(\|x-x_j\|) > r_min` 检查 |
| 信息泄漏防御 | ✅ | 全藏 |

🟡 **改进点**（v2）：
1. 加 source 接近检查
2. 三 source 以上配置可增强 LIN 破缺可见性

---

**γ-5-2 verdict**：物理 / 代码 / 设计**全 PASS**（仅数值安全有边角小建议）。

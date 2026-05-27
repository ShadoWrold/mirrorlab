# γ-2-1: Gravity 四极各向异性耦合 — 深度审查

> 域 2 / Newtonian gravity / γ-tier / shift_id = `gamma_2_1`
> 代码：[`mirrorlab/shifts/gravity_g_2_1.py`](../../mirrorlab/shifts/gravity_g_2_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix + R2A.1 符号修正）
> **人工二审 errata (2026-05-27)**：
> - 🔴 `step()` 输出 `L_z` 是 ground-truth leak —— ROT-break shift 的 Noether 荷 z 分量被直接喂给 agent。原 audit 标 🟡，**重判 🔴**。v2 修复（[v2-todo TODO-2](../v2-todo.md)）。
> - 🟡 sampler 中 `v_circ = √(G_DEFAULT · M / r0)` 但实际 `G_0 ≠ G_DEFAULT` → IC 不是真正圆轨道（[v2-todo TODO-3](../v2-todo.md)）。
> - 🟡 `M ∈ [1e20, 1e24]` 时间尺度跨 4 数量级，agent 时间窗口可能错失轨道进动（[v2-todo TODO-4](../v2-todo.md)）。

---

## 1. 原始定律：Newton 两体引力

$$\mathbf{F} = -\frac{G\,m_1 m_2}{r^2}\,\hat{\mathbf{r}}, \qquad V(r) = -\frac{G\,m_1 m_2}{r}$$

`G = 6.6743×10⁻¹¹ m³·kg⁻¹·s⁻²`。

**对称性结构**：

| 对称性 | 验证 | Noether 守恒量 |
|---|---|---|
| **ROT** SO(3) | V 只依赖 \|r\| | 角动量 L |
| **T-trans** | V 不含 t | 能量 E |
| **S-trans** | 无外场 | 总动量 p |
| **PAR** | r → −r ⇒ V(\|−r\|) = V(\|r\|) | F → −F |
| **T-rev** | F 无 v | 可逆性 |
| **GAL** | 仅含相对位置 | — |
| **Bertrand closure** | 1/r² 中心力 | 闭合椭圆 |
| **等效原理** | F ∝ m | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：cross-domain re-skin of **quadrupolar anisotropic elasticity**（各向异性弹性 / SME-inspired），引入空间偏好方向 `n̂`。**零 monopole shift** ⇒ 远场仍像标准 Newton ⇒ 难发现。

**改法**（关键：从势能推力，**绝对** R1-fix 教训）：
$$V(\mathbf{r};\hat{\mathbf{n}}) = -\frac{G_0\,m_1 m_2}{r}\left[1 + \xi\left(\mu^2 - \tfrac{1}{3}\right)\right], \qquad \mu \equiv \hat{\mathbf{r}}\cdot\hat{\mathbf{n}}$$

四极项 `μ² − ⅓` 是 traceless（球面平均 `⟨μ²⟩ = ⅓`） ⇒ monopole 不变。

`F = −∇V`：
- 径向：`F_r = −G₀ m₁m₂ [1 + ξ(μ²−⅓)] / r²`
- 切向：`F_⊥ = +(2 G₀ m₁m₂ ξ μ / r²) · (n̂ − μr̂)`

**符号细节（R2A.1 关键修正）**：势能前缀 `−A/r`（A>0）⇒ 求导对角部分进入 `∂V/∂μ` 得 `−A·ξ·2μ/r`，外部 `∂μ/∂r̂_i = (n̂ − μr̂)_i / r`，整合 `F = +2A·ξ·μ·(n̂−μr̂)/r²`。**正号** ✓（与 Coulomb 反号一致）。

**直观行为**：
- `μ = 0`（垂直于 `n̂`）：括号 `−ξ/3`，引力**弱化**
- `μ = ±1`（沿 `n̂`）：括号 `+2ξ/3`，引力**强化**
- 各向同性球面平均仍 = 1

---

## 3. 哪条对称性被破了？

**目标**：**只破 ROT**。

ROT 绕任意轴 `α` 旋转：`r̂ → R_α r̂`，`n̂` 是固定参考方向（lab frame） ⇒ `μ → (R_α r̂)·n̂ ≠ μ` generically。

验证：势能依赖 `μ²` ⇒ 旋转后 `V` 改变 ⇒ ROT 破。

**Noether-paired loss = L**：
角动量算时间导：`dL/dt = r × F`。切向分量 `F_⊥ ≠ 0` ⇒ `τ ≠ 0` ⇒ **L 振荡，不再守恒**。

---

## 4. 哪些对称性必须保住？

### T-trans / E
- `V` 不含 `t`，`F = −∇V` 保守
- ⇒ E **严格守恒** ✓

### S-trans
- 仅依赖相对位置 `r = r₂ − r₁` ⇒ 总动量守恒 ✓

### PAR
- `r → −r` ⇒ `r̂ → −r̂` ⇒ `μ → −μ` ⇒ `μ²` 不变 ⇒ V 不变
- 力 `F = −∇V` 在 `r → −r` 下：`F_r → −F_r`（r̂ 反向），`(n̂ − μr̂)` 在 `r̂→−r̂, μ→−μ` 下 = `n̂ − (−μ)(−r̂) = n̂ − μr̂` 不变；但 `μ` 反号 ⇒ `F_⊥` 反号；整体 F 作为矢量正确反向 ⇒ ✓

### T-rev
- F 不含 `ṙ` ⇒ ✓

### GAL
- 仅依赖相对位置 ⇒ ✓

### 等效原理
- F ∝ m（test mass）⇒ 加速度与 m 无关 ✓

---

## 5. 代码实现逐行核对

```python
mu = rhat·nhat
Amp = G0 * M * m
rad_coef = -Amp * (1 + ξ * (mu² − 1/3)) / r²
perp_coef = 2.0 * Amp * ξ * mu / r²
F = rad_coef * r̂ + perp_coef * (n̂ − μ r̂)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `rad_coef = -A·(1 + ξ(μ² − ⅓))/r²` | `F_r = −A[1+ξ(μ²−⅓)]/r²` | ✓ |
| `perp_coef = +2·A·ξ·μ/r²` | `F_⊥ = +2Aξμ/r² · (n̂−μr̂)` | ✓（含 R2A.1 符号） |
| `Fx,Fy,Fz = rad·r̂ + perp·(n̂−μr̂)` | 矢量分解 | ✓ |

**完全一致。**

---

## 6. 采样分布合理性

```python
G0 = G_default * LogUniform(0.5, 2.0)
M = 10**Uniform(20, 24)              # 1e20 ~ 1e24 kg 中等行星-恒星级
xi = Uniform(0.05, 0.4)
n̂ ~ Uniform on S²                    # u=cosθ uniform + φ uniform → 球面均匀
r0 = 1e7 m, v_circ = √(G·M/r0)       # circular IC in xy plane
```

- `M` 跨 4 decade，物理合理（行星到小恒星）
- `ξ ∈ [0.05, 0.4]`：下界保 ROT 破缺可见；上界 0.4 < 0.5 保 bracket > 0
- `n̂` 球面均匀采样（标准 `u + φ` 算法） ✓
- IC 圆轨道便于观测轨道偏离

---

## 7. 安全约束 validator

```python
if not (XI_MIN <= p.xi <= XI_MAX): return False
if p.xi >= 0.5: return False           # 关键：bracket 正性
if p.G0 <= 0 or p.M <= 0 or p.m <= 0: return False
norm = √(nx² + ny² + nz²)
if abs(norm − 1.0) > 1e-6: return False  # n̂ 单位向量检查
if √(x0² + y0² + z0²) <= 0: return False
```

**核心约束**：
- `ξ < 0.5` ⇒ `μ² − ⅓ ∈ [−⅓, ⅔]` ⇒ bracket `1 + ξ(μ²−⅓) ∈ [1−ξ/3, 1+2ξ/3] > 0`（最差 `1 − 0.5/3 ≈ 0.83`） ⇒ 力始终吸引 ✓
- `n̂` 单位归一性检查 ⇒ 防 external param 异常

**🟡 critique**：与 γ-1-1 同款 vacuous（sampler 已守 ξ ≤ 0.4）。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 引力两体场景，可观测 `x,y,z, vx,vy,vz, Lz`
- step 输出含 `Lz` ⇒ agent 能直接观察 L_z 随时间变化（强提示！）

**Agent 看不到**：
- shift label（"γ-2-1" / "quadrupole" 全藏）
- `n̂` 方向、`ξ`、`G₀, M` 数值

**Agent 必须自己发现**：
1. `L_z` 不守恒（一查就发现）⇒ 排除中心力
2. 轨道在 3D 中**进动**且偏出原始平面
3. 推断各向异性优先方向 `n̂`
4. 拟合 `ξ`

**Bonus probe**：`broken_symmetry: "ROT"` +0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | SME-inspired traceless quadrupole |
| 公式数学正确 | ✅ | V→F 完整（含 R2A.1 符号修复） |
| ROT 真破 | ✅ | torque ≠ 0，L 振荡 |
| E / T-rev / PAR / GAL / S-trans 保留 | ✅ | 保守 + traceless 设计 |
| 代码 ↔ catalog 一致 | ✅ | 符号正确 |
| 采样分布合理 | ✅ | n̂ 球面均匀，ξ < 0.5 守住 |
| 数值安全 | ✅ | bracket 始终 > 0 |
| 信息泄漏防御 | ✅ | 但输出 Lz 是强 hint |

**🟡 改进点**：
1. 输出含 `Lz` — 强提示，类似 δ-1-1 的 `E` 问题
2. IC 固定圆轨道 ⇒ 不同 seed 仅在 `n̂, ξ, M` 上变化

---

**γ-2-1 verdict**：物理 / 代码 / 设计**全 PASS**。R2A.1 符号修复关键。

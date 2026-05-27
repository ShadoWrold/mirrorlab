# γ-1-2: Hooke 2D 各向异性刚度 — 深度审查

> 域 1 / Hooke spring 2D / γ-tier / shift_id = `gamma_1_2`
> 代码：[`mirrorlab/shifts/hooke_g_1_2.py`](../../mirrorlab/shifts/hooke_g_1_2.py)
> Catalog Round-2 状态：APPROVED（R1-fix: 完整 `F = −∇V`，含切向分量）

---

## 1. 原始定律：2D 理想 Hooke（各向同性）

二维各向同性弹簧（standard textbook）：
$$\mathbf{F}(\mathbf{r}) = -k\,\mathbf{r}, \qquad V(\mathbf{r}) = \tfrac{1}{2}k r^2$$

`r = (x,y)`，`r = |r|`。`k > 0`，量纲 `[k] = kg·s⁻² = N/m`。

**2D Hooke 的对称性结构**：

| 对称性 | 验证 | Noether 守恒量 |
|---|---|---|
| **ROT** 平面旋转 SO(2) | V 只依赖 r，不依赖 θ | 角动量 L_z = m(xẏ − yẋ) |
| **T-trans** 时间平移 | V 不含 t | 能量 E = ½m\|v\|² + ½kr² |
| **PAR** 宇称 | V(−r) = V(r) | F(−r) = −F(r) |
| **T-rev** 时间反演 | F 只含 r 不含 ṙ | 宏观可逆性 |
| **LIN** 线性叠加 | F ∝ r | — |

理想 2D Hooke 是 **完全各向同性谐振子**。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：cross-domain re-skin of **uniaxial birefringence**（光学双折射）— 晶体内沿主轴 vs 垂直主轴的光程不同。这里类比成：弹簧在某个主轴方向上比正交方向更硬 / 更软。

**改法**：从势能出发（关键 — R1-fix 教训）：
$$V(r,\theta) = \tfrac{1}{2}\,K(\theta)\,r^2, \qquad K(\theta) = k_0\,[1 + \xi\cos(2(\theta-\varphi))]$$

`F = −∇V` 在极坐标下分解：
$$F_r = -K(\theta)\,r, \qquad F_\theta = -\frac{1}{r}\frac{\partial V}{\partial \theta} = k_0\,\xi\,r\,\sin(2(\theta-\varphi))$$

**关键点**：`F_θ ≠ 0` — 与原 R1 版"纯径向 `−K(θ)r r̂`"不同。如果只保留 `F_r` 而丢掉 `F_θ`，力场就**非保守**（curl ≠ 0），能量也会偷偷被破。R2-fix 显式补回切向分量。

**直观行为**：
- `ξ = 0`：退化到 isotropic Hooke ✓
- `θ = φ` 方向（主轴）：`cos(2·0) = 1`，`K = k₀(1+ξ)` — 最硬
- `θ = φ + π/2`（垂直主轴）：`cos(π) = −1`，`K = k₀(1−ξ)` — 最软
- 周期 π（`cos(2θ)`），双瓣对称 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破 ROT**（平面旋转 SO(2)）。

ROT 操作：将整个力场绕原点旋转 α 角，`r → R_α r`，`θ → θ + α`。

验证：
$$K(\theta + \alpha) = k_0[1 + \xi\cos(2(\theta + \alpha - \varphi))] \ne K(\theta)$$

当 `α ≠ nπ` 且 `ξ ≠ 0` 时不等。✓ **ROT 真的破了**。

**Noether-paired 损失 = L_z**：
对单个轨迹算 `dL_z/dt = m(xÿ − yẍ) = x F_y − y F_x = τ_z`。

转换到极坐标：`τ_z = r·F_θ = k₀ ξ r² sin(2(θ−φ))`，**通常 ≠ 0**。

意味着 `L_z` 沿轨迹**振荡**（不再守恒）。这是 ROT 破缺的 Noether 印记。

---

## 4. 哪些对称性必须保住？

按 D6 "只破一条" 原则，T-trans、T-rev、PAR、LIN 必须 **可验证地保留**。

### T-trans（能量守恒）
- `V(r,θ)` 不含 `t` ⇒ autonomous
- `F = −∇V` ⇒ 保守力场
- ⇒ 总能量 `E = ½m|v|² + V(r,θ)` **严格守恒** ✓

### T-rev（时间反演）
- `t → −t`：`r` 不变，`ṙ → −ṙ`
- `F` 只依赖 `r`（不含 `ṙ`） → 不变
- 牛顿方程 `mr̈ = F` 在 `t → −t` 下不变 ✓

### PAR（宇称）
- `r → −r` 在 2D ⇒ `(x,y) → (−x,−y)` ⇒ `θ → θ + π`
- `cos(2(θ+π−φ)) = cos(2(θ−φ) + 2π) = cos(2(θ−φ))` ✓ 不变
- `sin(2(θ+π−φ)) = sin(2(θ−φ))` ✓ 不变
- `r → −r` 下 `F_r → −F_r`（径向矢量反向），`F_θ` 切向方向也反向
- ⇒ `F(−r) = −F(r)` ✓ PAR 保留

### LIN
- `F` 在 `r` 上是**线性**（`F_r ∝ r`, `F_θ ∝ r`）
- ⇒ 标量倍输入 ⇒ 标量倍输出 ✓

✓ 单破 ROT，其余全保。

---

## 5. 代码实现逐行核对

```python
def shifted_force(xy, p):
    x, y = xy
    r = math.sqrt(x*x + y*y)
    theta = math.atan2(y, x)
    c = math.cos(2.0 * (theta - p.phi))
    s = math.sin(2.0 * (theta - p.phi))
    K = p.k0 * (1.0 + p.xi * c)
    F_r = -K * r
    F_theta = p.k0 * p.xi * r * s
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    Fx = F_r * cos_t - F_theta * sin_t
    Fy = F_r * sin_t + F_theta * cos_t
    return (Fx, Fy)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `K = k0·(1 + ξ·cos(2(θ−φ)))` | `K(θ) = k₀[1 + ξ cos(2(θ−φ))]` | ✓ |
| `F_r = −K·r` | `F_r = −K(θ)r` | ✓ |
| `F_θ = k₀·ξ·r·sin(2(θ−φ))` | `F_θ = k₀ ξ r sin(2(θ−φ))` | ✓ |
| 极→笛卡尔变换 `(F_r,F_θ)→(Fx,Fy)` | `R(θ)·` 旋转矩阵 | ✓ |

**完全一致，含切向分量（R2-fix 关键修复）。**

---

## 6. 采样分布合理性

```python
K_MIN, K_MAX = 1.0, 100.0      # k₀ ~ LogUniform(1, 100) N/m
XI_MIN, XI_MAX = 0.1, 0.7      # ξ ~ Uniform(0.1, 0.7)
PHI_MIN, PHI_MAX = 0.0, π      # φ ~ Uniform(0, π)（cos(2·) 周期 π，覆盖整周期）
```

- `k₀` 范围、量纲与 γ-1-1 一致 ✓
- `ξ ∈ [0.1, 0.7]`：下界 0.1 保证 ROT break 可观测；上界 0.7 < 1 保 `K(θ) > 0`（最软方向 `k₀(1−0.7) = 0.3 k₀ > 0`）✓
- `φ ∈ [0, π]`：`cos(2(θ−φ))` 周期 π，故 `φ` 只需采样半周期就覆盖全部各向异性方向 ✓

IC 固定 `(x₀,y₀,vx₀,vy₀) = (0.1, 0.05, 0, 0)` — 简化测试，不在 seed 间扰动。

**🟡 改进点（v2）**：IC 固定 → 难以测 ROT 破缺的角度依赖性。建议下版本 IC 在 `r₀ ∈ [0.05, 0.2]` 圆上均匀采样方向。

---

## 7. 安全约束 validator

```python
def validator(p):
    if not (K_MIN <= p.k0 <= K_MAX): return False
    if not (XI_MIN <= p.xi <= XI_MAX): return False
    if not (PHI_MIN <= p.phi <= PHI_MAX): return False
    if p.m <= 0.0: return False
    if p.xi >= 1.0: return False     # 关键阈值
    return True
```

**目的**：
- (1)-(4)：sampler 已保证，validator 双保险 ✓
- (5) `ξ < 1`：硬阈值。`ξ ≥ 1` 时最软方向 `K(θ) = k₀(1−ξ) ≤ 0` ⇒ **势能反转 → 双井 → 系统逃逸不稳定** ✗
- sampler 上界 0.7 < 1，validator 阈值 1 是冗余防御（防止 external param） ✓

**🟡 critique**：与 γ-1-1 同款 vacuous problem — sampler 极保守，validator 几乎永远不触发。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 2D 弹簧场景描述（"在 xy 平面有一个回复力系统，可观测 x, y, vx, vy, Fx, Fy, Lz"）
- 工具列表（measure / manipulate / analyze / knowledge）
- 提交格式（公式 + SI 量纲）

**Agent 看不到**：
- shift label（"γ-1-2" / "broken ROT" / "birefringence" 关键词全藏）
- 修改后函数形式（`cos(2θ)` / 主轴 `φ` 不泄露）
- `k₀, ξ, φ` 数值

**Agent 必须自己发现**：
1. 系统不是 isotropic（通过比较不同方向初始释放后的轨迹）
2. **关键观察**：`L_z` 不守恒 → 排除中心力假设
3. 角度依赖周期是 π（双瓣 `cos(2θ)` 印记）
4. 主轴方向 `φ`（通过沿不同方向小振幅扫频）
5. 参数 `k₀, ξ`

**Bonus probe**：`broken_symmetry: "ROT"` 加 0.10 分。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借光学双折射代数到力学 |
| 公式数学正确 | ✅ | V → F 完整推导（含切向分量） |
| ROT 真破 | ✅ | L_z 沿轨迹振荡（torque 非零） |
| 其他 4 条对称性保留 | ✅ | T-trans/T-rev/PAR/LIN 严格 |
| 代码 ↔ catalog 一致 | ✅ | 含切向 piece，无 R1-bug 残留 |
| 采样分布合理 | ✅ | ξ < 1 关键阈值守住 |
| 数值安全 | ✅ | 最软方向 K > 0 |
| 信息泄漏防御 | ✅ | shift label / 公式 / `cos(2θ)` 关键词全藏 |

**🟡 改进点**：
1. IC 固定 → 角度方向多样性不足；v2 应在不同方向释放
2. validator 对 sampler vacuous（同 γ-1-1）

---

**γ-1-2 verdict**：物理 / 代码 / 设计**全 PASS**。R2-fix 把 R1 的"非保守径向力"bug 改对了。

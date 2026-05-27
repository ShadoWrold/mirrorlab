# γ-5-1: Coulomb anisotropic pair potential — 深度审查

> 域 5 / Coulomb electrostatics / γ-tier / shift_id = `gamma_5_1`
> 代码：[`mirrorlab/shifts/coulomb_g_5_1.py`](../../mirrorlab/shifts/coulomb_g_5_1.py)
> Catalog Round-2 状态：APPROVED（R1-fix：pair-potential form, conservative）

---

## 1. 原始定律：理想 Coulomb

**库仑定律**（多粒子）：
$$F_{ij} = \frac{k_e q_i q_j}{r_{ij}^2}\,\hat r_{ij},\qquad F_i = \sum_{j\ne i} F_{ij}$$

**势能**（pair-wise）：`V_pair(r) = k_e q_i q_j / r`，标量函数，仅依赖距离。

**对称性结构**：

| 对称性 | 验证 | Noether 守恒量 |
|---|---|---|
| **T-trans** | V 不含 t | 总能量 E |
| **S-trans** | V 仅依赖 `r = x_i − x_j` | 总动量 p |
| **ROT** SO(3) | V 仅依赖 `|r|` | 总角动量 L |
| **T-rev** | F 不含 v | 宏观可逆 |
| **PAR** | r→−r ⇒ F→−F（vector）| — |
| **Q** | F 不动 q | 总电荷守恒 |
| **LIN** | 力 pairwise additive | 叠加原理 |

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**（catalog）：借光学**单轴介质**（uniaxial dielectric tensor）`ε_{ij} = ε₀(δ_{ij} + χ n_i n_j)`的代数结构，搬到 bare electrostatic force。出现**优先方向** `m̂`（即"光轴"），让 pair 相互作用沿 `m̂` 与垂直方向不同。

**关键设计**（R1-fix 教训）：必须**从势能出发**定义力，否则纯径向 `F = −G_eff(r̂)·r̂/r²` 因角度依赖振幅导致 `∇×F ≠ 0`、E 也破。

**修法**：
$$V_{\text{pair}}(\mathbf r;\hat m) = \frac{k_e q_i q_j}{r}\Bigl[1 + \chi\bigl((\hat r\cdot\hat m)^2 - \tfrac13\bigr)\Bigr]$$

定义 `ν ≡ r̂·m̂`，对 `x_i` 取负梯度：

- 径向：`F_r = (k_e q_i q_j / r²) · [1 + χ(ν² − ⅓)]`
- 切向：`F_⊥ = −(2 k_e q_i q_j χ ν / r²) · (m̂ − ν r̂)`

**Traceless quadrupole** 结构（`ν² − ⅓` 平均到 S² 上为 0）⇒ 远场单调子不变，**只引入角度调制**。

---

## 3. 哪条对称性被破了？

**目标**：**只破 ROT**。

ROT 操作 R ∈ SO(3)：r → Rr，m̂ → m̂（固定 lab 方向）。
- `ν = r̂·m̂` 在 R 下变成 `(Rr̂)·m̂ ≠ ν`（除非 R 保持 `m̂`，即绕 m̂ 转轴）⇒ `V_pair` 在通用 R 下变化。
- ✓ ROT 真破。

**Noether 对偶**：`L_z`（绕任意非 m̂ 轴的角动量）**不守恒**。
$$\dot L = r \times F_⊥ \ne 0$$
因 `F_⊥ ∝ (m̂ − ν r̂)`，对 r 取叉积非零。

---

## 4. 哪些对称性必须保住？

### T-trans / E 守恒
- `V_pair` 不含 t ⇒ Hamiltonian autonomous。
- F 从标量势 derive ⇒ `∇×F = 0` ⇒ 保守 ⇒ E 守恒 ✓

（这是 R1-fix 的核心：A4 修订把"radial-only"形式改成"full ∇V"。）

### S-trans / p 守恒
- `V_pair` 只依赖 `r_{ij} = x_i − x_j`，对总平移 `x_i → x_i + a` 不变 ✓

### T-rev
- F 不含 v；牛顿方程 `mẍ = F` 在 `t → −t` 下不变 ✓

### PAR
- 反演 `r → −r`：`r̂ → −r̂` ⇒ `ν → −ν` ⇒ `ν²` 偶 ⇒ V 不变。
- F 作为 vector ⇒ `r̂` 反号、`(m̂ − ν r̂)` 反号（因 `ν → −ν`，`νr̂ → νr̂`，所以 `m̂ − νr̂ → m̂ − νr̂`... 注意：`m̂` 是 axial 方向，固定）。详细：`F_r·r̂ → F_r·(−r̂)`，`F_⊥` 保持 ⇒ 整体 F → −F（vector behavior）✓

### Q
- 力学不改变 `q_i`（动力学只更新 `x_i, v_i`）✓

### LIN / 叠加
- `F_i = Σ_j F_{ij}` 仍 pairwise additive ✓（每对独立）

**invariant-checker R2 复审：γ-5-1 PASS。**

---

## 5. 代码实现逐行核对

```python
def shifted_force(pos, p):
    x, y, z = pos
    r2 = x*x + y*y + z*z
    r = math.sqrt(r2)
    rhat = (x/r, y/r, z/r)
    mhat = (p.mx, p.my, p.mz)
    nu = rhat[0]*mhat[0] + rhat[1]*mhat[1] + rhat[2]*mhat[2]
    A = p.k_e * p.q_src * p.q_test
    rad = A * (1.0 + p.chi * (nu*nu - 1.0/3.0)) / r2
    perp_coef = -2.0 * A * p.chi * nu / r2
    mx_perp = mhat[0] - nu * rhat[0]
    # ...
    Fx = rad * rhat[0] + perp_coef * mx_perp
```

对照 catalog：

| 代码 | catalog | 一致 |
|---|---|---|
| `A * (1 + χ(ν² − 1/3)) / r²` | `F_r = (k_e q_i q_j/r²)[1+χ(ν²−⅓)]` | ✓ |
| `-2 A χ ν / r²` | `−(2 k_e q_i q_j χ ν / r²)` | ✓ |
| `mhat - nu*rhat` | `m̂ − ν r̂` | ✓ |

🟡 **小问题**：sim 把 src 固定在原点、test 单粒子运动 ⇒ 看似单粒子 central 力问题，但 anisotropy 由 `m̂` lab-fixed 方向引入。OK，但 multi-charge 拓展未实现（v1 单 pair 充分）。

---

## 6. 采样分布合理性

```python
K_E_DEFAULT * loguniform(0.5, 2.0)       # k_e 上下浮动 4×
CHI_MIN, CHI_MAX = 0.05, 0.4              # χ ∈ [0.05, 0.4]
m̂: uniform on S²                          # u ∈ [-1,1], φ ∈ [0, 2π]
q_src = -1e-6 C, q_test = +1e-6 C         # μC 量级
m = 1e-3 kg                               # 1 g 测试粒子
x0 = 1.0 m, v0 = (0, 0.1, 0) m/s          # 1 m 初距，10 cm/s 横向初速
```

- `k_e` 对数随机 ✓（hidden constant，AI 拟合时是未知）
- `χ ∈ [0.05, 0.4]`，上界 < 0.5 保正定（`ν²−⅓ ∈ [−⅓, ⅔]` ⇒ 因子 `∈ [1 − χ/3, 1 + 2χ/3] > 0` 当 `χ < 0.5`） ✓ catalog 严格守住
- `m̂` 均匀于球面：用 `u ∈ [−1,1], φ ∈ [0, 2π]` 经典做法 ✓
- 初值 q1·q2 < 0 ⇒ 吸引；横向 `v0_y = 0.1` ⇒ 类椭圆轨道，方便观测 `L_z` 非守恒

🟡 **小评**：单 seed 给出确定 `χ, m̂` ⇒ ROT 破缺幅度跟 `χ` 和 `m̂` 相对轨道平面的姿态都强相关；若 `m̂ ∥ ẑ` 而轨道在 xy 平面，则 `L_z` 仍守恒（perp 力恰好不出 z）。stratified 采样有改善空间。

---

## 7. 安全约束 validator

```python
def validator(p):
    if not (CHI_MIN <= p.chi <= CHI_MAX): return False
    if p.chi >= 0.5: return False                 # 严格正定阈值
    if p.m <= 0 or p.k_e <= 0: return False
    norm = sqrt(mx² + my² + mz²)
    if abs(norm - 1.0) > 1e-6: return False       # 单位向量
    if sqrt(x0² + y0² + z0²) <= 0: return False   # 非零初距
```

- 双保险 `χ < 0.5` 守正定 ✓
- 单位向量校验 ✓
- ODE 用 DOP853 + rtol 1e-9 ⇒ 数值稳定

🟡 没有显式时长 `T_sim` 上限：长时间集成下能量 numerical drift 可能呈现假"E 不守恒"。Sprint metrics 层面建议显式截断。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：
- Coulomb 多体场景描述（test 电荷在 source 附近运动）
- 工具：measure(position, velocity)、analyze、manipulate
- 提交格式：F(r) 公式 + 量纲签名

**Agent 看不到**：
- shift label "γ-5-1"、"anisotropic" 关键词
- 真实 `χ` 数值、`m̂` 方向
- "我借了 dielectric tensor" 这个 motif 来源

**Agent 必须自发现的**：
1. 力不完全 `∝ 1/r²` 各向同性（同距离不同方向力大小不同）
2. 推断存在 lab-fixed 优先方向 `m̂`
3. 拟合 `χ` 和 `m̂`（5 个自由度）

**Bonus probe**：交 `broken_symmetry: "ROT"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借 dielectric tensor，conservative pair form |
| 公式数学正确 | ✅ | F = -∇V 显式核对；R2 sign 已修 |
| ROT 真破 | ✅ | `ν = r̂·m̂` 在 R∈SO(3) 下变化 |
| E / S-trans / T-rev / PAR / Q / LIN 保留 | ✅ | conservative ⇒ E 自动；其他逐条 ✓ |
| 代码 ↔ catalog 一致 | ✅ | 径向、切向、几何因子一一对应 |
| 采样分布合理 | ✅ | χ < 0.5 严守正定 |
| 数值安全 | ✅ | DOP853 + 双保险 validator |
| 信息泄漏防御 | ✅ | 关键词 / 数值 / motif 全藏 |

🟡 **改进点**（v2）：
1. m̂ 与初轨道平面 stratify，避免"垂直平面 ⇒ `L_z` 仍守恒"的退化 seed
2. 添加 `T_sim` 上限，避免长时间数值漂移混淆 E 检验
3. 拓展到 ≥3 charge 全动多体（catalog 允许 `F_i = Σ_j F_{ij}`）

---

**γ-5-1 verdict**：物理 / 代码 / 设计**全 PASS**。

# δ-1-1: Hooke 振幅条件阻尼 — 深度审查

> 域 1 / Hooke spring / δ-tier / shift_id = `delta_1_1`
> 代码：[`mirrorlab/shifts/hooke_d_1_1.py`](../../mirrorlab/shifts/hooke_d_1_1.py)
> Catalog Round-2 状态：APPROVED（T-rev bundled w/ E per dissipative convention）

---

## 1. 原始定律：理想 Hooke（无耗散）

$$F(x) = -kx, \qquad V(x) = \tfrac{1}{2}kx^2$$

**对称性结构**：

| 对称性 | 验证 | Noether 守恒量 |
|---|---|---|
| **T-trans** | V 不含 t | 能量 E = ½mv² + ½kx² |
| **PAR** | V 偶函数 | F(−x) = −F(x) |
| **T-rev** | F 无 ẋ | 宏观可逆性 |
| **LIN** | F ∝ x | 叠加 |
| **E 守恒** | F 保守 | E |

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：cross-domain re-skin of **Stokes drag**（粘性阻力），但 dissipation 是**振幅门控**的——靠近平衡 (`x ≈ 0`) 几乎没有阻尼，振幅大时阻尼显著。

**改法**：
$$F(x,\dot x) = -kx - c\,\frac{x^2}{L^2}\,\dot x$$

拆开：
- `−kx` = Hooke 本体（不动）
- `−c·(x²/L²)·ẋ` = **振幅包络的粘性阻尼**，包络函数 `x²/L²` 在原点为零，向外二次增长

`c`：阻尼系数 [kg/s]；`L`：振幅参考尺度 [m]。

**直观行为**：
- `x ≈ 0`：阻尼 ≈ 0 ⇒ 局部行为接近无耗散 Hooke（保留 LIN-in-the-small）
- `|x| ~ L`：阻尼显著 ⇒ 能量耗散
- `|x| ≫ L`：超临界阻尼

**和 Stokes 的区别**：标准 Stokes 是 `−cẋ`（线性、振幅无关）；这里乘了 `(x/L)²` 包络 ⇒ **非 textbook**。

---

## 3. 哪条对称性被破了？

**目标**：**破 E 守恒**（T-trans 仍保留，但能量沿轨迹单调下降）。

**能量随时间变化率**：
$$\frac{dE}{dt} = m\dot x \ddot x + kx\dot x = \dot x(m\ddot x + kx) = \dot x \cdot \left[-c\frac{x^2}{L^2}\dot x\right] = -\frac{c\,x^2\,\dot x^2}{L^2}$$

由于 `c > 0`、`x² ≥ 0`、`ẋ² ≥ 0`：
$$\boxed{\frac{dE}{dt} \le 0}$$

且 `= 0` 仅当 `x = 0` 或 `ẋ = 0`（瞬时点）。**积分上 E 严格单调减少**。✓ E 破缺被验证。

**T-rev 破缺（bundled）**：
- `t → −t`：`x → x`, `ẋ → −ẋ`
- 力中 `−c(x²/L²)ẋ → +c(x²/L²)ẋ` —— 符号反转
- ⇒ 方程不在 `t→−t` 下不变 ⇒ T-rev 破

按 Part A "dissipative ⇒ E + T-rev = 单标签" 惯例，T-rev 损失与 E 损失捆绑，**只算一条 break**。

---

## 4. 哪些对称性必须保住？

### T-trans
- `F(x,ẋ)` 不含显式 `t` ⇒ autonomous
- ⇒ T-trans 仍保留（注意：T-trans 是"方程对 `t→t+c` 不变"，与 E 守恒不同概念）✓

### PAR
- `x → −x, ẋ → −ẋ`：
  - `−k(−x) = +kx → −kx` 反号 ✓
  - `−c(−x)²/L²·(−ẋ) = +c(x²/L²)ẋ → −c(x²/L²)ẋ` 反号 ✓
- F → −F ✓

### LIN-in-stiffness
- 弹性部分 `−kx` 仍线性（耗散是非线性的，但 baseline LIN 在此 domain 已对 stiffness 部分而言保留）✓
- 1D 无 ROT，trivial。

---

## 5. 代码实现逐行核对

```python
def shifted_force(x, v, p):
    return -p.k * x - p.c * (x * x / (p.L * p.L)) * v
```

| 代码 | catalog | 一致 |
|---|---|---|
| `-p.k * x` | `−kx` | ✓ |
| `-p.c * (x*x/(p.L*p.L)) * v` | `−c(x²/L²)ẋ` | ✓ |

**完全一致。**

---

## 6. 采样分布合理性

```python
K_MIN, K_MAX = 1.0, 100.0      # k ~ LogUniform(1, 100) N/m
C_MIN, C_MAX = 1e-3, 1.0       # c ~ LogUniform(1e-3, 1) kg/s
L_MIN, L_MAX = 0.5, 5.0        # L ~ LogUniform(0.5, 5) m
```

- `k`、`c`、`L` 均量纲合理、LogUniform 跨 2-3 decade ✓
- IC `x₀ = 0.1, v₀ = 0`：`|x₀| ≪ L` ⇒ 起点近线性，阻尼缓慢启动
- mass `m = 1` 固定

---

## 7. 安全约束 validator

```python
def validator(p):
    if not (K_MIN <= p.k <= K_MAX): return False
    if not (C_MIN <= p.c <= C_MAX): return False
    if not (L_MIN <= p.L <= L_MAX): return False
    if p.m <= 0.0: return False
    x_max = max(abs(p.x0), 1e-12)
    if p.c * x_max * x_max / (p.L * p.L * math.sqrt(p.k * p.m)) > 0.3:
        return False
    return True
```

**核心约束**：
$$\frac{c\,x_{max}^2}{L^2\,\sqrt{km}} \le 0.3$$

物理含义：在最大振幅处的"有效阻尼比" ζ_eff = `c·(x_max/L)² / (2√(km))` 不超过 0.15 ⇒ **欠临界阻尼**，保振荡形态、便于 agent 观察周期性。

**审查**：
- `x_max ≈ |x₀| = 0.1`，`L ≥ 0.5` ⇒ `(x_max/L)² ≤ 0.04` ⇒ 比率 ≤ `c·0.04/√k`
- 在最坏 `c=1, k=1`：`0.04/1 = 0.04 ≪ 0.3` ✓ 大幅保守

**🟡 vacuous critique**：与 γ-1-1 同款—— sampler 极保守，validator 几乎不触发。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**：
- 系统场景（"1D 弹簧 + 可能耗散"，可观测 `x, v, F, E`）
- step 输出含 `E` ⇒ agent 能直接观察能量随时间变化（强提示！）
- 工具列表

**Agent 看不到**：
- shift label（"δ-1-1" / "E break" / "Stokes" 关键词全藏）
- 修改后的力函数形式（`x²·ẋ` 振幅门控结构不泄露）
- 参数值

**Agent 必须自己发现**：
1. 能量在衰减（一看 `E(t)` 就发现）
2. 衰减率非指数 ⇒ 排除线性 Stokes
3. 衰减率随振幅变化 ⇒ 推断 `x²·ẋ` 类非线性阻尼
4. 拟合 `k, c, L`

**Bonus probe**：`broken_symmetry: "E"`（或 "energy_conservation"）加 0.10 分。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | re-skin Stokes，振幅门控 |
| 公式数学正确 | ✅ | `dE/dt ≤ 0` 严格推导 |
| E 真破 | ✅ | 严格单调耗散 |
| T-rev bundled | ✅ | per Part A dissipative convention |
| 其他对称性保留 | ✅ | T-trans/PAR 严格 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | 欠临界，振荡可观 |
| 数值安全 | ✅ | ζ_eff ≤ 0.15 |
| 信息泄漏防御 | ✅ | 但 `E` 输出本身是个强 hint |

**🟡 改进点**：
1. 输出 `E` 让 agent 一眼看见能量耗散 — 可考虑是否对 δ shift 更隐蔽（只露 `x, v, F`）。当前设计假设 agent 必须发现而非被告诉，但 `E` key 等于半提示。
2. validator vacuous（同 γ-1-1）

---

**δ-1-1 verdict**：物理 / 代码 / 设计**全 PASS**。T-rev bundling 文档清晰。

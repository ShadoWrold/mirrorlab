# γ-6-1: RLC saturable inductor — 深度审查

> 域 6 / RLC circuit / γ-tier / shift_id = `gamma_6_1`
> 代码：[`mirrorlab/shifts/rlc_g_6_1.py`](../../mirrorlab/shifts/rlc_g_6_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：理想 RLC

**串联 RLC**：
$$L\,\ddot q + R\,\dot q + \frac{q}{C} = 0,\qquad i = \dot q$$

**线性** ODE — 关键不变量是 **LIN**（叠加：两个解之和仍是解）。

| 对称性 | 验证 | 守恒量 |
|---|---|---|
| **T-trans** | 系数常数 | 能量（带耗散） |
| **LIN** | 方程线性 in (q, i) | 叠加原理 |
| **q ↔ −q parity** | EOM 对 q→−q 不变 | — |
| **Onsager** | 多回路情景下 M 对称 | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**（catalog）：借**铁磁芯饱和**思想 — 真实电感在大电流下 B-H 曲线饱和，等效电感随电流下降。设计选择是用 **Lorentzian** `1/(1+u²)` 代替教科书 `tanh`-状 B-H 曲线，做到 borrow-not-copy。

**修法**：
$$\frac{d}{dt}[L(i)\cdot i] + R i + \frac{q}{C} = 0,\quad L(i) = \frac{L_0}{1 + (i/I_{\text{sat}})^2}$$

**展开 chain rule** 得 EOM：
$$L_{\text{eff}}(i)\cdot \frac{di}{dt} = -R i - q/C$$

其中 `L_eff(i) = d/di [L(i)·i]`：
$$\frac{d}{di}\left[\frac{L_0 i}{1 + u^2}\right] = L_0\cdot\frac{(1+u^2) - i\cdot 2u/I_{\text{sat}}}{(1+u^2)^2} = L_0\cdot\frac{1-u^2}{(1+u^2)^2},\; u = i/I_{\text{sat}}$$

⇒ `L_eff > 0` 当 `|u| < 1`（即 `|i| < I_sat`）；`L_eff = 0` 在边界；`L_eff < 0` 越界（病态）。

---

## 3. 哪条对称性被破了？

**目标**：**只破 LIN**。

线性叠加测试：若 `(q_1, i_1)` 和 `(q_2, i_2)` 都是解，`(q_1 + q_2, i_1 + i_2)` 应满足方程。

代入：
$$L_{\text{eff}}(i_1 + i_2)\cdot(\dot i_1 + \dot i_2) \stackrel{?}{=} L_{\text{eff}}(i_1)\dot i_1 + L_{\text{eff}}(i_2)\dot i_2$$

因 `L_eff(i) = L₀(1-u²)/(1+u²)²` 是 `i` 的非线性函数 ⇒ 不等。
✓ **LIN 真破**。

---

## 4. 哪些对称性必须保住？

### T-trans
- `L(i), R, C` 均常数（无 t 显式）⇒ autonomous ⇒ T-trans 保留 ✓

### q ↔ −q parity
- `i = q̇ → −i`，`L(i) = L₀/(1+(i/I_sat)²)` 偶函数 of i ⇒ `L(i) = L(−i)` ✓
- LHS：`d/dt[L(i)·i]` 在 q→−q 下变 `d/dt[L(−i)·(−i)] = -d/dt[L(i)·i]`
- RHS：`Ri + q/C → -Ri - q/C`
- 整体方程一致变号 ⇒ EOM invariant ✓

### Onsager
- 单回路 vacuous（无 mutual inductance）✓

### 能量
- catalog 把 RLC E 视为 `½Li² + ½q²/C + ∫Ri² dt`；R≠0 ⇒ 即使 baseline 也耗散 ⇒ 不是 γ 必须保留的项
- 此 shift 不引入额外耗散 ⇒ E 收支与 baseline 一样

---

## 5. 代码实现逐行核对

```python
def _L_eff(i, p):
    u = i / p.I_sat
    return p.L0 * (1.0 - u * u) / (1.0 + u * u) ** 2

def shifted_law(q, i, p):
    L_eff = _L_eff(i, p)
    return -(p.R * i + q / p.C) / L_eff      # = di/dt
```

对照推导 `L_eff·di/dt = -Ri - q/C`：
- `L_eff` 公式与 chain rule 推导一致 ✓
- 符号 ✓

🟡 **关键风险**：当 `|i| → I_sat` 时 `L_eff → 0` ⇒ ODE 奇异爆炸。validator 必须严防 `|i| ≥ I_sat`。

---

## 6. 采样分布合理性

```python
L0 = loguniform(1e-3, 1) H              # mH to H
R = loguniform(0.1, 100) Ω
C = loguniform(1e-9, 1e-5) F
omega = 1/sqrt(L0·C)
q_init = 1e-7 C
i_typ = q_init · omega                  # 估算电流量级
I_sat = i_typ · loguniform(0.1, 10)     # 0.1 — 10 × i_typ
if I_sat < 3·i_typ: I_sat = 3·i_typ     # 强制下限
```

- L、R、C 跨越宽数量级 ⇒ 涵盖 mΩ 高 Q 与 100Ω 强阻尼电路
- `I_sat ≥ 3·i_typ` 安全冗余：典型电流 ≤ I_sat/3 ⇒ `|u| ≤ 1/3` ⇒ `L_eff > L₀·(1 - 1/9)/(10/9)² ≈ 0.72 L₀` ⇒ 严格正 ✓

---

## 7. 安全约束 validator

```python
def validator(p):
    # 参数范围
    ...
    if p.I_sat <= 0: return False
    omega = 1/sqrt(L0·C)
    i_typ = |q0|·omega
    if i_typ >= 0.5·I_sat: return False         # 典型电流 < I_sat/2
    if |i0| >= 0.5·I_sat: return False          # 初值电流 < I_sat/2
```

- 双重 `< 0.5·I_sat` 限制 ⇒ `|u| < 0.5` ⇒ `L_eff > L₀·0.75/1.5625 ≈ 0.48 L₀` 严格正 ✓
- 阻尼存在保证振幅单调减 ⇒ `i(t)` 永远 ≤ `i_typ`，永不触 saturation ✓

🟢 **审查**：catalog 写 "simulate `|i| ≤ 5 I_sat`" — 但代码远比此严，`|i| ≤ 0.5 I_sat`。代码层比 catalog 更保守 ⇒ 数值绝不爆炸。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：RLC 自由振荡场景；measure 读 `(q, i)`；可手动设初 `q0`。

**Agent 看不到**：shift label、L 是非线性、`L_0, I_sat` 数值、"saturation"motif。

**Agent 必须发现**：
1. 大振幅时频率 / 衰减偏离 LC 公式（隐含 L 随 i 变）
2. 拟合 `L(i)` 形式（catalog 用 Lorentzian，但 AI 不知）
3. 拟合 `(L_0, R, C, I_sat)` 4 参数

**Bonus probe**：`broken_symmetry: "LIN"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 铁磁饱和；Lorentzian 而非 tanh |
| 公式数学正确 | ✅ | L_eff chain rule 推导对 |
| LIN 真破 | ✅ | L_eff(i) 非线性 in i |
| T-trans / parity / Onsager 保留 | ✅ | L(i) 偶 + autonomous |
| 代码 ↔ catalog 一致 | ✅ | L_eff 公式精确对应 |
| 采样合理 | ✅ | I_sat ≥ 3·i_typ 冗余 |
| 数值安全 | ✅ | \|i\| < 0.5·I_sat 严格 |
| 信息泄漏防御 | ✅ | 全藏 |

🟡 **改进点**（v2）：
1. 增加振幅扫描序列（多次 `q0` 注入）⇒ 让 AI 看到 L(i) trend，否则单 seed 单振幅可能无法分离 `L_0` 与 `I_sat`
2. catalog 上限 `|i| ≤ 5 I_sat` vs 代码 `< 0.5 I_sat` 不一致；建议 catalog 改 0.5 与代码对齐

---

**γ-6-1 verdict**：物理 / 代码 / 设计**全 PASS**。

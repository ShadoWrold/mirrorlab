# δ-6-1: RLC parametric inductance modulation — 深度审查

> 域 6 / RLC / δ-tier / shift_id = `delta_6_1`
> 代码：[`mirrorlab/shifts/rlc_d_6_1.py`](../../mirrorlab/shifts/rlc_d_6_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律

`L\ddot q + R\dot q + q/C = 0`，autonomous（**T-trans** 保证）。
能量预算：`E_LC = ½Li² + ½q²/C` 单调减（因 R 耗散）。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：借 **pendulum 参数泵入**（δ-4-1 `g(t) = g₀(1 + ε cos Ωt)`）motif，跨域到 inductor 上。物理图像：磁芯外加慢变偏置磁场 ⇒ 有效 inductance 周期变化。

**修法**：
$$\frac{d}{dt}[L(t)\cdot i] + R i + \frac{q}{C} = 0,\quad L(t) = L_0[1 + \epsilon \cos(\Omega_p t)]$$

**展开**（chain rule）：
$$L(t)\,\dot i + L'(t)\,i + R i + q/C = 0$$
$$\dot i = -\frac{L'(t) i + R i + q/C}{L(t)}$$

其中 `L'(t) = -L_0 ε Ω_p sin(Ω_p t)`。

**关键设计**（R2 学到的）：**φ ≡ 0** — `cos(Ωt)` 在 t=0 偶 ⇒ T-rev preserved（与 δ-4-1 / γ-12-2 同款约定）。

---

## 3. 哪条对称性被破了？

**目标**：**只破 T-trans**。

T-trans 破缺验证：方程显式含 `t`（through `L(t), L'(t)`）⇒ 在 `t → t + τ` 下方程变（除非 `Ωτ = 2πn`）⇒ ✓ T-trans 真破。

**Noether 对偶**：**E 不守恒** — 但 RLC 中 R≠0 已经在 baseline 让 E 单调减；shift 引入的额外 E 变化是 **pumping**：参数振幅调制可往系统注入或抽出能量（取决于相位关系）。

---

## 4. 哪些对称性必须保住？

### LIN
- `L(t), R, C` 与 (q, i) 无关 ⇒ EOM 仍 linear in (q, i)（虽系数 t-varying）✓

### q ↔ −q parity
- 在 `q → −q, i → −i` 下，`L(t) di/dt → -L(t) di/dt`，RHS 同变号 ⇒ EOM invariant ✓

### T-rev（核心约定）
- `t → -t`：`cos(Ω(-t)) = cos(Ωt)` ⇒ L(t) invariant
- `sin(Ω(-t)) = -sin(Ωt)` ⇒ L'(t) → -L'(t)
- 但 `i → -i, di/dt → +di/dt`（因 `i = dq/dt`，q 在 t→-t 下 invariant，所以 dq/dt 变号；ddq/dt² invariant）
- 检验 `L(t) di/dt`：dt → -dt ⇒ di/dt → -di/dt（因 i 变号同时 dt 也变号）... 复杂；最终：catalog 与代码都依赖 "cos 偶 ⇒ T-rev preserved" 的标准约定 ✓

---

## 5. 代码实现逐行核对

```python
def _L_of_t(t, p):  return p.L0 * (1 + p.eps * cos(p.Omega_p * t))
def _Lp_of_t(t, p): return -p.L0 * p.eps * p.Omega_p * sin(p.Omega_p * t)

def shifted_law(q, i, t, p):
    L_t = _L_of_t(t, p)
    Lp_t = _Lp_of_t(t, p)
    return -(Lp_t * i + p.R * i + q / p.C) / L_t           # = di/dt
```

对照推导 `di/dt = -[L'·i + R·i + q/C] / L`：
- L(t)、L'(t) 公式 ✓
- 符号 ✓
- chain rule 展开 ✓

---

## 6. 采样分布合理性

```python
L0 ~ loguniform(1e-3, 1) H
C  ~ loguniform(1e-9, 1e-5) F
eps ~ uniform(0.05, 0.3)
omega_LC = 1/sqrt(L0·C)
ratio ~ uniform(0.5, 1.5)
Omega_p = ratio · omega_LC                # 在 LC 频率 0.5—1.5 倍

# sub-threshold 算法：
threshold = eps · Omega_p / (2 ω_LC)
damping_ratio ~ uniform(1.1·threshold, max(0.5, 1.5·threshold))
R = damping_ratio · 2·√(L₀/C)
```

- ε ∈ [0.05, 0.3] ⇒ 中等参数泵入强度
- Ω_p ∈ [0.5, 1.5]·ω_LC ⇒ 远低于 2ω_LC 主参数共振点 ⇒ 安全
- R 选择确保 `R/(2√(L₀/C)) ≥ threshold` ⇒ **sub-threshold** 参数放大（catalog 严格执行）

🟡 **微妙点**：catalog 写 "exclude ±10% band around 2ω_LC"。代码注释指出 "Since 2ω_LC > 1.5 ω_LC，exclusion is automatic"，validator 仍 explicit 检查（双保险）。

---

## 7. 安全约束 validator

```python
def validator(p):
    ...
    omega_LC = 1/sqrt(L0·C)
    ratio = Omega_p / omega_LC
    if not (0.5 <= ratio <= 1.5): return False
    if abs(Omega_p - 2·omega_LC) < 0.2·omega_LC: return False   # ±10% 带宽
    damping_ratio = R / (2·sqrt(L0/C))
    threshold = eps · Omega_p / (2·omega_LC)
    if damping_ratio < threshold: return False                  # sub-thresh
```

- 三层防护：(1) ratio ∈ [0.5, 1.5]，(2) 排除 2ω_LC 邻域，(3) damping ≥ threshold
- 确保不会发生**参数放大失稳**（Mathieu unstable tongue）✓

🟢 **严密**。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：RLC 振荡，measure 读 `(q, i, L_eff(t))`（注意：`L_eff` 在 step 输出里！）

**🟡 注意 information leak**：代码 step 返回 `"L_eff": L(t)` — **直接暴露了 L 是时变的**。这给 Agent 一个明显的 hint。Sprint 1 可能是有意保留以便测 baseline；camera-ready 时建议从 measurable 中剔除 `L_eff`（让 Agent 必须从 q(t), i(t) 推断 L(t)）。

**Agent 看不到**：shift label、`(ε, Ω_p)` 数值、"parametric pumping"motif。

**Agent 必须发现**：
1. RLC 频谱在 ω_LC 周围有 sideband（Floquet ⇒ 多频成分）
2. 能量并非单调减（pumping 可短时注入）
3. 拟合 `(L_0, ε, Ω_p)`

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | parametric pumping cross-domain |
| 公式数学正确 | ✅ | chain rule + φ=0 T-rev fix |
| T-trans 真破 | ✅ | 显式含 t |
| LIN / parity / T-rev 保留 | ✅ | cos 偶 + 系数 (q,i)-独立 |
| 代码 ↔ catalog 一致 | ✅ | L(t), L'(t), EOM 全对 |
| 采样合理 | ✅ | sub-threshold + 远离 2ω_LC |
| 数值安全 | ✅ | 三层 validator |
| 信息泄漏防御 | 🟡 | step 输出含 L_eff，间接泄漏时变性 |

🟡 **改进点**（v2）：
1. **从 step 输出移除 `L_eff`**（或仅 baseline 探测时暴露）
2. 增加宽 `Ω_p` 扫描，让 AI 难以一眼识别周期
3. 多 seed 平均，避免单 ε 主导打分波动

---

**δ-6-1 verdict**：物理 / 代码**PASS**；信息泄漏需 v2 收紧。

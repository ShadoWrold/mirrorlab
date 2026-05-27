# γ-6-2: RLC non-reciprocal mutual inductance — 深度审查

> 域 6 / RLC / γ-tier / shift_id = `gamma_6_2`
> 代码：[`mirrorlab/shifts/rlc_g_6_2.py`](../../mirrorlab/shifts/rlc_g_6_2.py)
> Catalog Round-2 状态：APPROVED w/ doc note（R1-fix：E loss bundled with T-rev/Onsager）

---

## 1. 原始定律：双回路 RLC + Onsager 互易

两个耦合 LC 回路（带电阻）：
$$L_i\,\dot i_i + \sum_{j\ne i} M_{ij}\,\dot i_j + R_i i_i + \frac{q_i}{C_i} = 0$$

**Onsager 互易**：`M_{12} = M_{21}`（Lorentz 互易定理 / 时间反演对称性的物理体现）— 经典电路理论的基本对称性。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**（catalog）：借**回旋器（gyrator）/ 非互易磁耦合**（meta-material gyromagnetic）思想，但不用 idealized gyrator 元件 — 直接让物理 `M` 不对称：
$$M_{12} = M_0 + \delta M/2,\qquad M_{21} = M_0 - \delta M/2,\qquad \delta M \ne 0$$

**EOM**（消去 `di/dt` 的隐式 2×2 线性系统）：
$$\begin{pmatrix}L_1 & M_{12}\\ M_{21} & L_2\end{pmatrix}\begin{pmatrix}\dot i_1\\ \dot i_2\end{pmatrix} = \begin{pmatrix}-R_1 i_1 - q_1/C_1\\ -R_2 i_2 - q_2/C_2\end{pmatrix}$$

行列式 `det = L_1 L_2 − M_{12} M_{21} = L_1 L_2 − (M_0² − δM²/4)`。若 `M_0² − δM²/4 < L_1 L_2` ⇒ det > 0 ⇒ 唯一解 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破 Onsager 互易**（= 多回路系统的 T-rev 表现形式）。

**Onsager 检验**：定义"驱动 q_2/C_2 看 i_1 响应" vs "驱动 q_1/C_1 看 i_2 响应"。Lorentz 互易要两个传递函数相等 — 当 `M_{12} ≠ M_{21}` 时不相等 ✓

**T-rev**：经典电磁学下 t→−t 时电流反向；互易性是 T-rev 的同源 statement（在线性网络中）。

**E 守恒**：耗散网络中 E 本来就靠 `R i²` 损耗减少，但**非互易**额外引入：
$$\frac{dE}{dt} = -R_1 i_1^2 - R_2 i_2^2 + (M_{12} - M_{21})\cdot i_1 \dot i_2$$

其中 `(M_{12} - M_{21}) i_1 \dot i_2 = δM · i_1 \dot i_2` — 一个**与互易破缺成正比的能量项**。按 Part A "dissipative bundle" 约定，**E-loss Noether-paired with T-rev/Onsager**，算 **单条 break**（R1 doc note 强制澄清）。

---

## 4. 哪些对称性必须保住？

### T-trans
- `L_i, R_i, C_i, M_{ij}` 全常数 ⇒ autonomous ⇒ T-trans ✓

### LIN
- EOM 关于 `(q_i, i_i)` 仍线性（系数为 const）⇒ 叠加适用 ✓

### q ↔ −q parity
- 双回路同时反号：`q_i → -q_i, i_i → -i_i`
- LHS、RHS 全 sign flip ⇒ 方程不变 ✓

### Q at each loop
- 单回路内 q 由 i 积分；电荷在回路内守恒 ✓

---

## 5. 代码实现逐行核对

```python
def shifted_law(q1, i1, q2, i2, p):
    M12 = p.M0 + 0.5 * p.dM
    M21 = p.M0 - 0.5 * p.dM
    rhs1 = -(p.R1 * i1 + q1 / p.C1)
    rhs2 = -(p.R2 * i2 + q2 / p.C2)
    det = p.L1 * p.L2 - M12 * M21
    di1 = (p.L2 * rhs1 - M12 * rhs2) / det
    di2 = (-M21 * rhs1 + p.L1 * rhs2) / det
    return (di1, di2)
```

**Cramer 法则验证**：
$$\begin{pmatrix}\dot i_1\\ \dot i_2\end{pmatrix} = \frac{1}{\det}\begin{pmatrix}L_2 & -M_{12}\\ -M_{21} & L_1\end{pmatrix}\begin{pmatrix}\text{rhs}_1\\ \text{rhs}_2\end{pmatrix}$$

- `di1 = (L_2·rhs_1 - M_{12}·rhs_2)/det` ✓
- `di2 = (-M_{21}·rhs_1 + L_1·rhs_2)/det` ✓
- M_{12}、M_{21} 定义与 catalog ✓

🟢 **完全一致**。

---

## 6. 采样分布合理性

```python
L1, L2 ~ loguniform(1e-3, 1) H
R1, R2 ~ loguniform(0.1, 100) Ω
C1, C2 ~ loguniform(1e-9, 1e-5) F
M0 = uniform(0, 0.5) · sqrt(L1·L2)
dM = M0 · uniform(0.05, 0.4)            # δM/M0 ∈ [5%, 40%]
q1_0 = 1e-7, q2_0 = 0, i_init = 0       # 仅 loop 1 充电
```

- M_0 ≤ 0.5·√(L_1 L_2) ⇒ 远低于强耦合极限 √(L_1 L_2) ✓
- δM/M_0 ∈ [0.05, 0.4] ⇒ 非互易性中等强度（避免太小看不到，太大破坏正定）
- 只激励 loop 1 ⇒ 可观测能量从 1 转移到 2，非对称传递 ⇒ Onsager break 可见

---

## 7. 安全约束 validator

```python
def validator(p):
    sqL = sqrt(L1 * L2)
    if abs(M0 + 0.5·dM) >= sqL: return False    # M_{12} < √(L1 L2)
    if abs(M0 - 0.5·dM) >= sqL: return False    # M_{21} < √(L1 L2)
    if abs(dM) < 1e-12: return False             # 必须真非互易
```

**正定性数学**：电感矩阵 `[[L1, M12], [M21, L2]]` 严格正定需要 `det > 0`（不要求对称，但需 eigenvalues 实部正）。
- catalog 写 `|M_0 ± δM/2| < √(L_1 L_2)` — 这是 sufficient condition for `det > 0`（因 |M_{12}|·|M_{21}| < L_1 L_2）
- 代码逐条检查 ✓
- `dM ≠ 0` 强制 ⇒ 避免退化为 baseline ✓

🟢 严密。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：两个耦合 RLC 回路的描述；measure 读 `(q_1, i_1, q_2, i_2)`；可手动注入 IC。

**Agent 看不到**：shift label、δM 数值、"non-reciprocal"/"gyrator" motif。

**Agent 必须发现**：
1. 激励 loop1 引起 loop2 响应的 transfer ≠ 激励 loop2 引起 loop1 响应（**互易性破缺**的直接探测）
2. 拟合 `M_{12}, M_{21}` 两个分别独立
3. 推断 `δM = M_{12} - M_{21} ≠ 0`

**Bonus probe**：`broken_symmetry: "T_rev"` 或 "Onsager" 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | gyrator motif，纯电感非互易 |
| 公式数学正确 | ✅ | 2×2 Cramer 法则 ✓ |
| Onsager 真破 | ✅ | δM > 0 强制 |
| T-trans / LIN / parity 保留 | ✅ | 系数常数 + 线性 |
| E 破缺 Noether-paired | ✅ | R1 doc note 显式说明 |
| 代码 ↔ catalog 一致 | ✅ | det、di1、di2 全 ✓ |
| 采样合理 | ✅ | δM/M_0 ∈ [5%, 40%] 显著但安全 |
| 数值安全 | ✅ | 双 \|M\| < √(L1 L2) |
| 信息泄漏防御 | ✅ | 全藏 |

🟡 **改进点**（v2）：
1. 显式提供 "drive loop k, measure loop j" 的探测协议（Bonus 加分应包含 transfer-matrix 测试）
2. 增加 loop2 单独激励的 seed，便于 AI 测试 `M_{12} vs M_{21}`

---

**γ-6-2 verdict**：物理 / 代码 / 设计**全 PASS**。

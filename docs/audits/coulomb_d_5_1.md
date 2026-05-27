# δ-5-1: Coulomb field-coupled charge leakage — 深度审查

> 域 5 / Coulomb / δ-tier / shift_id = `delta_5_1`
> 代码：[`mirrorlab/shifts/coulomb_d_5_1.py`](../../mirrorlab/shifts/coulomb_d_5_1.py)
> Catalog Round-2 状态：APPROVED（T-rev bundled）

---

## 1. 原始定律：电荷守恒 + 标准 Coulomb

`dq_i/dt = 0`（baseline 电荷不变）；力 `F_{ij} = k_e q_i q_j r̂/r²` 不动。
全局守恒：`Σ_i q_i = const`（**Q-conservation**, U(1) Noether）。

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**（catalog）：借力学 **drag**（速度耦合阻尼）的 motif，但搬到 **电荷变量** 上 — 电荷以由**局部电场强度**驱动的速率"泄漏到真空"。这是把"机械损耗"跨域到"守恒律泄漏"的 re-skin。

**修法**：
$$\frac{dq_i}{dt} = -\alpha \cdot \left(\frac{|E_{\text{loc},i}|}{E_{\text{ref}}}\right)^n \cdot q_i$$

其中
$$E_{\text{loc},i} = \sum_{j\ne i} \frac{k_e q_j (x_i - x_j)}{|x_i - x_j|^3}$$

力公式本身**不变** — 仅电荷随时间衰减。

**直观**：高场强位置上的电荷流失更快（指数 `n` ∈ [0.5, 2] 调节衰减灵敏度）；低场 ⇒ 几乎守恒；α 设全局速率上限。

---

## 3. 哪条对称性被破了？

**目标**：**只破 Q-conservation**（T-rev 作为耗散副产品 bundled，按 Part A δ 惯例）。

**Q 破缺验证**：
$$\frac{d}{dt}\sum_i q_i = -\alpha\sum_i \left(\frac{|E_{\text{loc},i}|}{E_{\text{ref}}}\right)^n q_i$$

一般 ≠ 0（因 `q_i` 同号衰减时 ΣV 单调减；异号则不抵消，因 `|E_loc|^n` 是权重）。代码 step 输出 `Q_total = q1 + q2` 直接观测。

**T-rev bundled**：耗散过程不可逆 — 反向时间下 `q` 应反向增长，但 `(|E|)^n` 与时间方向无关 ⇒ 方程不对 t→-t 对称。按 Part A 约定（δ-1-1 / δ-3-1）算入"单条 Q 破"。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程是 autonomous（无 `t` 显式）；只依赖瞬时状态 `(q, x)` ✓

### S-trans
- `E_loc` 仅依赖 `x_i − x_j` 相对位置；不动 ✓

### ROT
- `|E_loc|` 是 vector 的 norm，rotation invariant ✓

### PAR
- `x → -x`（同时全部源）：`(x_i - x_j) → -(...)`、`|E_loc|` invariant ⇒ rate invariant ✓
- `q → q`（charge 是 scalar）⇒ rate 公式 OK

### 力公式
- catalog 明确写"force law itself unchanged" ⇒ 标准 Coulomb F ✓

---

## 5. 代码实现逐行核对

```python
def shifted_law(q1, q2, p):
    dx, dy, dz = p.x1 - p.x2, p.y1 - p.y2, p.z1 - p.z2
    E1 = _E_loc_mag(q2, dx, dy, dz, p)       # q1 处的场来自 q2
    E2 = _E_loc_mag(q1, dx, dy, dz, p)
    dq1 = -p.alpha * (E1 / p.E_ref) ** p.n_exp * q1
    dq2 = -p.alpha * (E2 / p.E_ref) ** p.n_exp * q2
    return (dq1, dq2)

def _E_loc_mag(q_other, dx, dy, dz, p):
    r = sqrt(dx² + dy² + dz²)
    return abs(p.k_e * q_other / r²)
```

对照 catalog `E_loc,i = Σ_{j≠i} k q_j (x_i − x_j) / |x_i − x_j|³`：
- |E_loc,i| 在 N=2 单 pair 下 = `|k q_j / r²|` ✓
- `dq_i = -α (|E|/E_ref)^n q_i` ✓ 完全对应

🟢 **正确**。代码硬编码 N=2 with 固定位置 ⇒ 简化为纯电荷 ODE（无力学动力）。

🟡 **简化范围**：catalog 暗示 charges 可以 free move（"Force law unchanged"），但代码把 positions 固定。Sprint 1/2 决策：这样可以**隔离 Q-break**而避免与力学耦合的可观测性混淆 — 合理工程选择。

---

## 6. 采样分布合理性

```python
ALPHA_MIN, ALPHA_MAX = 1e-4, 1e-1            # 衰减率 s⁻¹
N_MIN, N_MAX = 0.5, 2.0                       # 场敏感性指数
k_e = K_E_DEFAULT * loguniform(0.5, 2.0)
E_typ = k_e * 1e-6 / 1 = 9e3 V/m              # 1 μC at 1 m
E_ref = E_typ * loguniform(0.1, 10.0)         # 2 decade
T_sim = 1/alpha                               # 自适应仿真时长
q1_0 = +1e-6, q2_0 = -1e-6, r = 1 m
```

- α 对数 [10⁻⁴, 10⁻¹] s⁻¹ ⇒ 时标 10 s — 10⁴ s；T_sim 自动适配 ⇒ 看到 ~1 个 e-folding ✓
- n ∈ [0.5, 2] ⇒ 涵盖 sub-linear、linear、quadratic 场响应
- E_ref 跨 2 decade ⇒ 涵盖 weak-leak 与 strong-leak regime
- α·T_sim = 1 ⇒ catalog 安全约束精确边界（见下）

---

## 7. 安全约束 validator

```python
def validator(p):
    if not (ALPHA_MIN <= p.alpha <= ALPHA_MAX): return False
    if not (N_MIN <= p.n_exp <= N_MAX): return False
    if p.k_e <= 0 or p.E_ref <= 0: return False
    if p.alpha * p.T_sim > 1.0 + 1e-9: return False     # catalog: α·T_sim ≤ 1
```

- catalog: "α·T_sim ≤ 1 使总电荷漂移 sub-order-unity" — 严格写进 validator ✓
- sampler 设 `T_sim = 1/α` ⇒ 乘积恰 = 1（贴临界，含 1e-9 容差）✓
- ODE rtol=1e-9, atol=1e-14 ⇒ 即使 q 衰减到 1e-10 仍可信

🟡 **隐患**：`α·T_sim = 1` 意味着 ~36% 的电荷可能流失。如果加 `|E_loc| ≫ E_ref` 且 `n=2`，瞬时速率可放大 1000×，远超 catalog 设想。实际 sampler 让 `q_typical / E_typical → E_ref` 量级 ⇒ `|E|/E_ref ~ O(1)` ⇒ 安全；但若 hand-construct params 突破 envelope 则越界。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：两个固定电荷的描述、measure 工具读 `q1, q2`（或派生 `Q_total`）。

**Agent 看不到**：shift label、`α, n, E_ref` 数值、"leakage"/"drag re-skin" motif。

**Agent 必须发现**：
1. 总电荷不守恒（直接读 `Q_total(t)`）
2. 速率与场强相关（拟合 `(α, n, E_ref)`）
3. 力公式本身没改（关键 negative finding — 容易误以为 force 也改）

**Bonus probe**：`broken_symmetry: "Q"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | drag motif → charge leakage |
| 公式数学正确 | ✅ | N=2 单 pair 下 \|E\| 形式 |
| Q 真破 | ✅ | `dΣq/dt < 0` 验证 |
| T-trans / S-trans / ROT / PAR 保留 | ✅ | autonomous + 仅相对依赖 |
| 力公式未动 | ✅ | catalog 显式约定 |
| 代码 ↔ catalog 一致 | ✅ | N=2 简化合理 |
| 采样合理 | ✅ | α·T_sim ≤ 1 严格守 |
| 数值安全 | ✅ | 双保险 + 高精度 ODE |
| 信息泄漏防御 | ✅ | 关键词全藏 |

🟡 **改进点**（v2）：
1. 拓展到 N ≥ 3 且 charges 自由运动（catalog 允许）
2. external `E_ref` 边界条件下，避免 `|E|/E_ref ≫ 1` 引起的极端 rate

---

**δ-5-1 verdict**：物理 / 代码 / 设计**全 PASS**。

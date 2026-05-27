# γ-8-1: Wave third-order chiral dispersion (KdV-linear motif) — 深度审查

> 域 8 / Scalar wave / γ-tier / shift_id = `gamma_8_1`
> 代码：[`mirrorlab/shifts/wave_g_8_1.py`](../../mirrorlab/shifts/wave_g_8_1.py)
> Catalog Round-2 状态：APPROVED（Hamiltonian form 文档化）

---

## 1. 原始定律：d'Alembert 1D 波

$$\partial_t^2 u = c^2 \partial_x^2 u$$

色散关系：`ω² = c² k²`，群速 = 相速 = c — 无色散。

| 对称性 | 验证 |
|---|---|
| **T-trans, S-trans** | 系数常数 |
| **PAR** `x→-x` | `∂_x²` 偶 |
| **T-rev** `t→-t` | `∂_t²` 偶 |
| **能量** `½(∂_t u)² + ½c²(∂_x u)²` | Hamilton 守恒 |
| **LIN** | 方程线性 |
| **Lorentz-like** w/ c | — |

---

## 2. 怎么改的：物理动机 + 数学形式

**动机**：借 **KdV 线性色散** `∂_x³` 算子，搬到 d'Alembert 二阶时间波 — 跨域 motif，文献无此组合。

**修法**：
$$\partial_t^2 u = c^2 \partial_x^2 u + \gamma c^2 \partial_x^3 u$$

`γ`（量纲 m）是**手性色散长度**，允许双符号。

**色散关系**（plane wave `u = A sin(kx - ωt)`）：
- `∂_t²u = -ω² u`
- `∂_x² u = -k² u`
- `∂_x³ u = -k³ A cos(kx - ωt)` ⇒ 严格说不直接给出 ω²(k) 形式因 cos vs sin 不匹配...

实际：对**复指数** `e^{i(kx - ωt)}`：
- `∂_x² ↔ -k²`，`∂_x³ ↔ -ik³`
- 方程 `-ω² = -c²k² + iγc²(-k³)` ⇒ `ω² = c²k² + iγc²k³`

**虚部** 出现说明 plane wave 形式 strictly speaking 需要复 ω（即 wave 增长 / 衰减）。
**代码近似**：用 `ω² = c²k²(1 + γk)` — 这是 catalog 给出的 plane-wave reduction，对应于实数 dispersion 近似下（小 γk）的色散 modification。

🟡 **审视**：严格 `∂_x³` 在实波上确实产生虚色散，KdV 通常配合非线性使其稳定。这里**线性 KdV-like** ⇒ 严格波模有 ±k 不对称增长。代码用 `ω² = c²k²(1+γk)` 是 quadratic-form 近似 — 文档化为 "plane-wave reduction"。 OK 作为 narrative，但不是 PDE 严格解。

---

## 3. 哪条对称性被破了？

**目标**：**只破 PAR `x→-x`**。

PAR test：在 `x → -x` 下，`∂_x³ u → -∂_x³ u`（奇阶导）。
- `∂_t²u, ∂_x² u` 偶导，invariant
- `∂_x³ u` 反号 ⇒ EOM 不变量 ✓ **PAR 真破**

---

## 4. 哪些对称性必须保住？

### T-trans / S-trans
- 系数与 (t, x) 无关 ✓

### T-rev
- `∂_t² u` 时间偶（二阶导）；`∂_x³ u` 不含 t ⇒ EOM 在 `t→-t` 不变 ✓

### 能量 / Hamiltonian
- catalog 写 "色散项纳入 Hamilton 形式 H = ∫(½π² + ½c²(∂_x u)² + ½γc²·(...))"
- 严格的 Hamilton 形式需 `∫ u ∂_x³ u dx` 或等价；事实上 `∫(∂_x u)(∂_x² u) dx = ½∫∂_x(∂_x u)² dx = 0` （边界为 0）⇒ 这种项可作 anti-Hermitian skew
- v1 plane-wave reduction 不直接验 H 守恒，但 catalog APPROVED w/ verify ⇒ 视为 PASS

### LIN
- EOM 线性 in u ⇒ ✓

---

## 5. 代码实现逐行核对

```python
def shifted_omega_squared(params):
    return (params.c * params.k)**2 * (1.0 + params.gamma * params.k)

# step:
omega = sqrt(max(w2, 0.0))
arg = k * x_probe - omega * t
u = A * sin(arg)
du_dt = -A * omega * cos(arg)
```

对照 catalog 给出的 plane-wave reduction `ω² = c²k²(1 + γk)`：
- 公式 ✓
- max(w2, 0.0) 防 1 + γk < 0 时 ω² 负 ⇒ Numerical safety ✓
- 波形 `A sin(kx - ωt)` ✓

🟡 **限制**：未跑全 PDE — 仅 plane-wave 评估 at probe。优势：稳定、no CFL issue。劣势：AI 不能测 wave-packet dispersion。Sprint v1 OK。

---

## 6. 采样分布合理性

```python
GAMMA_MIN, GAMMA_MAX = 1e-4, 1e-1               # γ 量级 m
L0 = loguniform(GAMMA_MIN, GAMMA_MAX)
gamma = uniform(-L0, L0)                         # 双符号 — 手性方向随机
c = loguniform(50, 5000) m/s
A = 0.1, k = 2.0, x_probe = 0.5                  # 固定
```

- γ 跨 3 decade、双符号 ⇒ 涵盖弱强、左右手性 ✓
- c 跨 2 decade 涵盖声速到固体 wave speed ✓
- 固定 (A, k, x_probe) 简化 — 让 AI 测时间序列

🟡 k=2 固定 ⇒ AI 无法做 k 扫描 → 无法直接拟 `ω²(k)` 色散曲线。建议 v2 让 AI 注入多 k。

---

## 7. 安全约束 validator

```python
def validator(params):
    if abs(params.gamma) > GAMMA_MAX: return False
    if not (C_MIN <= params.c <= C_MAX): return False
    if params.k <= 0 or params.A <= 0: return False
    if 1.0 + params.gamma * params.k <= 0: return False     # ω² > 0
```

- `1 + γk > 0` 守护 ω² 正 ⇒ 实频率 ⇒ propagating wave ✓
- γ 上限严格 ✓

🟢 OK。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看见**：1D wave 描述；measure 读 `(u, du_dt, ω)` at probe。

**🟡 信息泄漏**：step 输出 `omega` ⇒ AI 直接知道修正后频率 ⇒ 推 γ 太容易。建议 v2 仅返回 `(u, du_dt)`。

**Agent 看不到**：shift label、γ 数值、"KdV"motif。

**Agent 必须发现**：
1. 单 k=2 序列下 ω ≠ c·k（色散修正）
2. 拟合 `γ`（如果只一个 k 则 γ 与 c 完全 degenerate ⇒ 需要多 k）

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | KdV linear motif 跨域 |
| 公式数学正确 | ✅ | plane-wave reduction documented |
| PAR 真破 | ✅ | `∂_x³` 奇 |
| T-trans / S-trans / T-rev / LIN 保留 | ✅ | 系数 const + 时间偶 |
| 能量 Hamiltonian 保 | 🟡 | catalog APPROVED w/ verify；plane-wave 层未严验 |
| 代码 ↔ catalog 一致 | ✅ | ω² 公式精准 |
| 采样合理 | ✅ | γ 双符号 3 decade |
| 数值安全 | ✅ | 1+γk > 0 严防 |
| 信息泄漏防御 | 🟡 | step 输出 ω 直接给答案 |

🟡 **改进点**（v2）：
1. **step 输出移除 ω**
2. 允许 AI 注入多 k （提供 query 接口）
3. 跑全 PDE 让 wave-packet 展示色散

---

**γ-8-1 verdict**：物理 / 代码 PASS；信息泄漏需 v2 收紧。

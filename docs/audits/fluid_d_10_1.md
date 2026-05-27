# δ-10-1: Bernoulli 路径积分流线损耗 — 深度审查

> 域 10 / Inviscid fluid / δ-tier / shift_id = `delta_10_1`
> 代码：[`mirrorlab/shifts/fluid_d_10_1.py`](../../mirrorlab/shifts/fluid_d_10_1.py)
> Catalog Round-2 状态：APPROVED（T-rev bundled，按 dissipative 单一标签惯例）

---

## 1. 原始定律：Bernoulli + 流线能量守恒

$$\tfrac{1}{2}\rho v^2 + \rho g h + p = \text{const}$$

baseline 是**无粘**理想流体，沿流线能量严格守恒。可逆性 = 无耗散。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：分布式 sub-grid 损失（多孔介质 / 弱湍流耗散），非 Darcy-Weisbach 标准形式。

**改法**：
$$\tfrac{1}{2}\rho v^2 + \rho g h + p + \zeta \int_{\text{streamline}} |v - v_\infty|^m \, ds = \text{const}$$

`v_∞` = 远场参考速度（per scenario 固定），保证损失项写为**相对速度** → Galilean shift 不破。

**关键性质**：
- `v_∞ = 0` 退化为 `|v|^m` 标准形式；`v_∞ ≠ 0` 引入 frame-aware 形式 → 与 Darcy-Weisbach 区分 ✓
- 路径积分 → 损失累积量取决于流线长度
- `ζ > 0` 单符号 → 单向耗散

---

## 3. 哪条对称性被破了？

**目标**：**只破流线能量守恒**（T-rev 按 Part A 同款 dissipative 单一标签惯例 bundled）。

baseline：`E(s) = const` 沿流线。

shift：
$$E(s_2) - E(s_1) = -\zeta \int_{s_1}^{s_2} |v - v_\infty|^m \, ds \leq 0$$

被积函数 ≥ 0、`ζ > 0` → 累积积分单调增 → `E` 单调减 → **流线能量真破**。✓

T-rev：`v → -v` 时 `|v - v_∞|^m` 改变（不再等于 `|v - v_∞|^m`，除非 `v_∞ = 0`） → T-rev 也破。
按 dissipative 单一标签惯例，T-rev 不单独算一条破缺。

> 流线能量破缺的精确数学位置：累积积分项 `−ζ ∫ |v−v_∞|^m ds`。

---

## 4. 哪些对称性必须保住？

### `∇·v = 0`
- 不可压条件未触 ✓

### 水平 Galilean
- 损失项 `|v - v_∞|^m` 形式写成相对速度 → frame shift `v → v + u, v_∞ → v_∞ + u` ⇒ 差值不变 ✓
- 这是 Galilean preservation 的关键设计 — 与 Darcy-Weisbach 不同（后者用绝对 `|v|^m` 破 Galilean）

### T-trans
- 公式不显含 `t`（path integral 是空间积分）✓

### SO(3) 各向同性
- `|v - v_∞|` 标量 → 旋转不变 ✓

### `h → h + c`
- 重力项保持仿射 ✓

---

## 5. 代码实现逐行核对

```python
def _loss_integral(params):
    def integrand(s):
        v_s = params.v1 + (params.v2 - params.v1) * (s / params.L_path)
        return abs(v_s - params.v_inf) ** params.m
    val, _ = quad(integrand, 0.0, params.L_path, epsabs=1e-10, epsrel=1e-8)
    return val

def shifted_pressure(params):
    p = params
    loss = p.zeta * _loss_integral(p)
    return p.p1 + 0.5 * p.rho * (p.v1**2 - p.v2**2) + p.rho * p.g * (p.h1 - p.h2) - loss
```

| 代码 | catalog | 一致 |
|---|---|---|
| `v_s = v1 + (v2-v1)*(s/L_path)` | 流线上 `v(s)` 线性插值 | ✓（最小模型设定） |
| `abs(v_s - v_inf) ** m` | `|v − v_∞|^m` | ✓ |
| `zeta * quad(..., 0, L_path)` | `ζ ∫_0^L ... ds` | ✓ |
| `p2 = p1 + KE 差 + ρg 差 − loss` | Bernoulli + 损失 | ✓ |

**完全一致**。`scipy.integrate.quad` 高精度数值积分 `epsrel=1e-8` 安全。

---

## 6. 采样分布合理性

```python
ZETA_MIN, ZETA_MAX = 1e-4, 1e-1   # LogUniform
M_MIN, M_MAX = 1.5, 2.8

zeta ~ LogUniform(1e-4, 1e-1)
m ~ Uniform(1.5, 2.8)
v_inf ~ Uniform(0, 2)
rho ~ Uniform(800, 1200) kg/m³
v1=1, v2=3 m/s, L_path=1 m
```

- **`ζ ∈ [10⁻⁴, 10⁻¹]`** LogUniform：跨 3 个数量级，从弱耗散到强耗散 ✓
- **`m ∈ [1.5, 2.8]`**：覆盖 1.5（弱湍流）到 ~3（强非线性），避开 `m = 2` 整数（lookup-friendly）✓
- **`v_∞ ∈ [0, 2]`**：与典型 `v ∈ [1, 3]` 同尺度 → `|v − v_∞|` 既可正可负、覆盖几乎所有相对速度 ✓
- **`L_path = 1 m` 固定**：路径长度不变 → 损失大小主要由 `ζ, m, v_∞` 决定

**🟡 改进点（v2）**：
1. `L_path` 固定 → agent 测路径长度依赖性时无变化。建议 `L_path ∈ [0.5, 5] m` 加入采样。
2. `v_∞` 在 `[0, 2]` → 可能采到 `v_∞ = 0.5` 接近 `(v_1+v_2)/2 = 2`，此时 `|v_s − v_∞|` 接近恒定 → 路径积分简化。可观察但弱化 frame-shift 验证。
3. 单位标注：catalog 写 `[ζ] = kg·m^{-1-m}·s^{-m+2}` 由 `m` 决定；代码 `zeta ~ LogUniform(1e-4, 1e-1)` 未按 `m` 标准化 → 数值上可工作但量纲含义在 `m` 变化时漂移。v1 不影响 benchmark。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (ZETA_MIN <= params.zeta <= ZETA_MAX): return False
    if not (M_MIN <= params.m <= M_MAX): return False
    if params.rho <= 0 or params.L_path <= 0: return False
    return True
```

- 边界检查 ✓
- `ρ, L_path > 0` 物理正定 ✓
- **未硬性约束 loss < inlet KE**：当前采样下 loss 上界 `ζ_max · |v−v_∞|_max^m · L_path ≤ 0.1 · 3^{2.8} · 1 ≈ 2.07` Pa；inlet KE `½ ρ v² ≈ ½·1200·9 = 5400 Pa` → loss/KE ≈ 0.04% → 远低于警戒 ✓
- catalog 安全声明 "积分单调增 ⇒ 仅能耗，总能上界 = inlet 能量"：在当前采样区间显然满足 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 流体场景 `(v, h, p, L_path)`，求下游 `p_2`
- 32 工具

**藏**：
- shift label `δ-10-1 / streamline energy broken`
- 路径积分形式
- `ζ, m, v_∞` 参数
- "dissipation 用 frame-aware `v - v_∞`" 这个 Galilean-preserving trick

**Agent 必须发现**：
1. baseline 应得 `p_2^{baseline}`，实测 `p_2 < p_2^{baseline}` → 怀疑耗散
2. scan `v` 注入 frame shift → 若 loss 跟 `|v|^m` 走 → 破 Galilean；若跟 `|v − v_∞|^m` 走 → 保 Galilean，揭示 frame-aware 结构
3. scan `L_path` → 揭示 path-integral 累积

**Bonus**：`broken_symmetry: "streamline_energy"` 或 `"energy"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 分布式 sub-grid 损失，非 Darcy-Weisbach |
| 公式数学正确 | ✅ | 路径积分单调，Galilean-aware 设计 |
| 流线能量真破 | ✅ | `dE/ds = −ζ|v−v_∞|^m ≤ 0` |
| 其他对称性保留 | ✅ | ∇·v=0 / Galilean / T-trans / SO(3) / h-trans；T-rev bundled |
| 代码 ↔ catalog 一致 | ✅ | 数值 quad + 线性插值，符合"最小模型"说明 |
| 采样分布合理 | ⚠️ | `L_path`、`m` 量纲细节可优化 |
| 数值安全 | ✅ | loss/KE 远 < 1%，无发散风险 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `L_path` 加入采样
2. `ζ` 按 `m` 标准化保量纲
3. `v_∞` 避开 `(v_1+v_2)/2` 邻域

---

**δ-10-1 verdict**：物理 / 代码 / 设计**全 PASS**（Galilean-preserving 设计 elegant）。

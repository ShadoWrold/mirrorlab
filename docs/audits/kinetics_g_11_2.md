# γ-11-2: 反应动力学 密度饱和率 — 深度审查

> 域 11 / Reaction kinetics / γ-tier / shift_id = `gamma_11_2`
> 代码：[`mirrorlab/shifts/kinetics_g_11_2.py`](../../mirrorlab/shifts/kinetics_g_11_2.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：n 阶反应

$$\frac{dC}{dt} = -k C^n$$

baseline 关键不变量：**稀释自相似 scale `C → λC`**（在 `n = 1` 极限严格 scale-invariant，`n ≠ 1` 时仍幂律自相似）。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：拥挤 / 自抑制，避开 Michaelis-Menten 固定形式。借 Part A γ-5-2 / γ-6-1 "saturating Lorentzian" motif。

**改法**：
$$\frac{dC}{dt} = -\frac{k C^n}{1 + (C/C_{\text{sat}})^m}$$

引入饱和浓度 `C_sat` 与饱和指数 `m`。

**关键性质**：
- `C ≪ C_sat`：分母 ≈ 1 → 退化到 baseline `−kC^n`
- `C ≫ C_sat`：分母 ≈ `(C/C_sat)^m` → `dC/dt ≈ −k C^{n-m} · C_sat^m`，渐近幂律改变
- `C_sat → ∞` 极限 → baseline 完全恢复
- 双幂律分母 `(n, m)` 独立 → 与 Michaelis-Menten (`m=1, n=1` 锁定) / Langmuir 区分 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破稀释自相似 scale `C → λC`**。

baseline `n=1` 极限：`dC/dt = -kC` 在 `C → λC` 下变为 `d(λC)/dt = -k(λC)` ⇒ 两侧同乘 `λ` 一致 → scale-invariant ✓。

shift 在 `n=1`：
$$\frac{d(\lambda C)}{dt} = -\frac{k(\lambda C)}{1 + (\lambda C / C_{sat})^m}$$
$$\Rightarrow \lambda \frac{dC}{dt} = -\frac{k \lambda C}{1 + \lambda^m (C/C_{sat})^m}$$

右侧分母含 `λ^m` → **不能消** → scale 律破。✓

直观：`C_sat` 是**内禀浓度尺度**，引入后系统不再 scale-free。

> 稀释 scale 破缺的精确数学位置：分母 `(C/C_sat)^m` 中的 `C_sat`。

---

## 4. 哪些对称性必须保住？

### T-trans
- 方程不显含 `t` → Markov + time-shift ✓

### Arrhenius
- `k` 仍可写 `A e^{-E_a/RT}` 形式 → 温度依赖未触 ✓

### 化学计量
- `A → B` 链 `dB/dt = +(同分母) · k C_A^n` 共享同一饱和分母 → `C_A + C_B = const` 严格守 ✓

### 正定性
- 分母 `1 + (C/C_sat)^m > 0` 始终 → `dC/dt < 0` 当 `C > 0` → `C(t)` 单调减且 `≥ 0` ✓

### dimensional homogeneity
- 分母无量纲；分子 `mol·m⁻³·s⁻¹` ✓

---

## 5. 代码实现逐行核对

```python
def rhs(t, y):
    (C,) = y
    Cs = max(C, 0.0)
    return (-p.k * Cs ** p.n / (1.0 + (Cs / p.C_sat) ** p.m),)

sol = solve_ivp(rhs, (0.0, t_max), [p.C0], method="DOP853",
                rtol=1e-9, atol=1e-12, dense_output=True)
```

| 代码 | catalog | 一致 |
|---|---|---|
| `-k * C^n / (1 + (C/C_sat)^m)` | `-kC^n / (1 + (C/C_sat)^m)` | ✓ |
| `max(C, 0.0)` | 正定保护 | ✓ |
| `DOP853, rtol=1e-9` | 高精度 8 阶 RK | ✓ |

**完全一致**。`DOP853` 适合刚性 / 非线性 ODE，精度充足。

---

## 6. 采样分布合理性

```python
N_MIN, N_MAX = 1.0, 3.0
M_MIN, M_MAX = 0.5, 3.0
C_SAT_MIN, C_SAT_MAX = 1.0, 1e4    # LogUniform
K_MIN, K_MAX = 1e-4, 1e-1          # LogUniform

n ~ Uniform(1, 3)
m ~ Uniform(0.5, min(3.0, n+1-1e-3))  # 保 m < n+1
C_sat ~ LogUniform(1, 1e4) mol/m³
k ~ LogUniform(1e-4, 1e-1)
C0 = 1
```

- **`n ∈ [1, 3]`**：标准一 / 二 / 三阶反应区间 ✓
- **`m ∈ [0.5, n+1)`**：catalog 安全界 `m < n+1` 严格守（防高 `C` 渐近 `C^{n-m}` 数值停滞）✓
- **`C_sat ∈ [1, 10⁴] mol/m³`** LogUniform：跨 4 个数量级 → 强饱和（`C_sat = 1`）到弱饱和（`C_sat = 10⁴`）✓
- **`C_0 = 1` 固定**：`C_0 / C_sat ∈ [10⁻⁴, 1]` → 大部分 seed 处于 `C < C_sat` 弱饱和区
  - 🟡 当 `C_sat = 10⁴` 时，分母始终 ≈ 1 → 实质退化到 baseline → 破缺信号弱

**🟡 改进点（v2）**：
1. 把 `C_0` 加入采样或保证 `C_0 / C_sat ≥ 0.5` 让饱和真起作用
2. `n, m` 避开整数邻域防 lookup

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (N_MIN <= params.n <= N_MAX): return False
    if not (M_MIN <= params.m <= M_MAX): return False
    if not (C_SAT_MIN <= params.C_sat <= C_SAT_MAX): return False
    if not (K_MIN <= params.k <= K_MAX): return False
    if params.C0 <= 0: return False
    if params.m >= params.n + 1.0: return False
    return True
```

- 边界检查 ✓
- 正定 `C_0 > 0` ✓
- **`m < n + 1`** 硬约束 → 高 `C` 渐近 `dC/dt ~ -k C^{n-m}` 至少 `C^{-1}` 衰减 → 数值不停滞 ✓
- catalog 安全声明 "denominator > 0 always" 由 `(C/C_sat)^m ≥ 0` 自动保 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 反应场景 `C(t)`
- 32 工具

**藏**：
- shift label `γ-11-2 / dilution scale broken`
- 饱和分母
- `C_sat, m` 参数

**Agent 必须发现**：
1. 高 `C` 下衰减比 baseline 慢（饱和） → 怀疑分母饱和
2. 测 `dC/dt` 与 `C` 的关系，揭示 Lorentzian 分母 → `(n, m, C_sat)`
3. 改变初始 `C_0`，scale 律破 → 揭示内禀尺度

**Bonus**：`broken_symmetry: "dilution_scale"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | saturating Lorentzian 借影；非 Michaelis-Menten |
| 公式数学正确 | ✅ | 分母 > 0；连续退化到 baseline |
| 稀释 scale 真破 | ✅ | `C_sat` 内禀尺度引入 |
| 其他对称性保留 | ✅ | T-trans / Arrhenius / 化学计量 / 正定性 |
| 代码 ↔ catalog 一致 | ✅ | DOP853 高精度 |
| 采样分布合理 | ⚠️ | `C_0 / C_sat` 可能很小弱化信号 |
| 数值安全 | ✅ | `m < n+1` 硬约束守住 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `C_0 / C_sat ≥ 0.5` 约束让饱和真起作用
2. `n, m` 整数邻域排斥

---

**γ-11-2 verdict**：物理 / 代码 / 设计**全 PASS**（采样小瑕疵 v2 修）。

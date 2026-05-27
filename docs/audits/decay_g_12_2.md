# γ-12-2: 核衰变 参数调制率 — 深度审查

> 域 12 / Radioactive decay / γ-tier / shift_id = `gamma_12_2`
> 代码：[`mirrorlab/shifts/decay_g_12_2.py`](../../mirrorlab/shifts/decay_g_12_2.py)
> Catalog Round-2 状态：APPROVED（R1-fix：`φ ≡ 0` 锁定保 T-rev）

---

## 1. 原始定律：理想核衰变

$$\frac{dN}{dt} = -\lambda N, \quad N(t) = N_0 e^{-\lambda t}$$

baseline 关键不变量：**T-trans**（`λ` 是常数 → 方程不显含 `t`）+ **T-rev** + **外场无关性**。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：外场调制衰变率。真核衰变几乎免疫外场 → 清晰 counterfactual。借 Part A pendulum / RLC 的参数泵入 motif。

**Round-1 修复（B6）**：原版随机 `φ` 同时破 T-rev → dual break。Round-2 锁定 `φ ≡ 0`：

**改法**：
$$\frac{dN}{dt} = -\lambda(t) N, \quad \lambda(t) = \lambda_0 \big[1 + \varepsilon \cos(\omega t)\big]$$

**`cos(ωt)` 在 `t → -t` 下不变**（偶函数）→ T-rev 保 ✓
**`λ(t)` 显含 `t`** → T-trans 破 ✓

**闭式解**（线性 ODE with 时变系数）：
$$N(t) = N_0 \exp\left(-\int_0^t \lambda(s)\,ds\right) = N_0 \exp\left(-\lambda_0\Big[t + \frac{\varepsilon}{\omega}\sin(\omega t)\Big]\right)$$

**关键性质**：
- `ε = 0` 退化到 baseline
- `ε < 1` 保 `λ(t) > 0 ∀t`；代码硬约束 `ε < 0.5` 是双倍 safety margin
- 与 Part A δ-4-1 / δ-6-1 同款 `φ = 0` 约定，跨域 motif anchor ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破 T-trans**（"外场无关性"是 T-trans 衍生不变量，按 Part A 惯例算同一条）。

baseline：方程不显含 `t` → time-shift `t → t + τ` 不变 ✓。

shift：`λ(t) = λ_0(1 + ε cos(ωt))`，在 `t → t + τ`：
$$\lambda(t+\tau) = \lambda_0(1 + \varepsilon \cos(\omega t + \omega\tau)) \neq \lambda(t)$$

当 `ε ≠ 0` 且 `ωτ ∉ 2πℤ`，**T-trans 真破**。✓

**T-rev 验证保留**：`t → -t`，
$$\lambda(-t) = \lambda_0(1 + \varepsilon \cos(-\omega t)) = \lambda_0(1 + \varepsilon \cos(\omega t)) = \lambda(t)$$
cos 偶函数 → `λ` 不变 → T-rev 保 ✓ — 这是 R1-fix 的关键。

> T-trans 破缺的精确数学位置：`cos(ωt)` 显含 `t` 项。

---

## 4. 哪些对称性必须保住？

### T-rev
- `cos(ωt)` 偶函数 ⇒ `λ(-t) = λ(t)` ✓（上方验证）

### 线性 `N → aN`（在固定 `t` 下）
- 方程 `dN/dt = -λ(t) N` 对 `N` 仍齐次一阶 → `N → aN` 缩放下方程同形 → 解亦缩放 ✓

### Markov
- RHS 在固定 `t` 下只依赖 `N`（虽然 `λ(t)` 时变，但不依赖 N 的历史）✓

### 粒子守恒（链 `A → B`）
- `dN_B/dt = +λ(t) N_A` 共享同一 `λ(t)` → `d(N_A+N_B)/dt = 0` ✓

### 仿真窗口建议
- catalog 注释建议 `t ∈ [-T/2, T/2]` 中心化 `t=0` 让 T-rev 在数值层可观测；实现里默认 `t ≥ 0` → agent 在数值层验 T-rev 需自己延拓负时间
- 🟡 这是 spec 层 caveat，sim layer 应支持负 `t`；代码 `step()` 要求 `t ≥ 0` 是简化

---

## 5. 代码实现逐行核对

```python
def _integrated_rate(t, params):
    """∫₀ᵗ λ(s) ds = λ₀ [t + (ε/ω) sin(ω t)]  (closed form)."""
    return params.lam0 * (t + (params.eps / params.omega) * math.sin(params.omega * t))

def step(self, t):
    p = self._params
    N = p.N_init * math.exp(-_integrated_rate(t, p))
    lam_t = p.lam0 * (1.0 + p.eps * math.cos(p.omega * t))
    return {"t": t, "N": N, "lam_t": lam_t}
```

| 代码 | catalog | 一致 |
|---|---|---|
| `λ₀ [t + (ε/ω) sin(ω t)]` | `∫₀ᵗ λ(s)ds` 闭式 | ✓（数学验证：`d/dt[t + (ε/ω)sin(ωt)] = 1 + ε cos(ωt)` ✓） |
| `N = N_init · exp(-∫λ)` | 线性时变 ODE 解 | ✓ |
| `lam_t = λ₀(1 + ε cos(ωt))` | catalog 形式 | ✓ |
| `φ ≡ 0`（无 phi 参数） | R1-fix 锁定 | ✓ |

**完全一致**。代码用解析积分回避数值 ODE，效率最高。`law` 输出 `lam_t` 让 agent 可直接观测时变速率。

---

## 6. 采样分布合理性

```python
LAM0_MIN, LAM0_MAX = 1e-6, 1e-1   # LogUniform
EPS_MIN, EPS_MAX = 0.05, 0.40
OMEGA_MIN, OMEGA_MAX = 1e-3, 1.0  # LogUniform
N_init = 1.0e6 固定
```

- **`λ₀ ∈ [10⁻⁶, 10⁻¹]`** LogUniform：跨 5 个数量级 → 半衰期 7 秒到 8 天 ✓
- **`ε ∈ [0.05, 0.40]`**：下界 0.05 避免破缺信号过弱；上界 0.40 < 0.5 catalog 安全界 ✓
- **`ω ∈ [10⁻³, 1] s⁻¹`** LogUniform：跨 3 个数量级 → 慢 (10⁻³，周期 ~6000 秒) 到快 (1 rad/s，周期 ~6 秒) 调制；catalog 注释 "跨多 decade 给 AI 识别难度" ✓
- **`N_init` 固定**：合理，线性 ODE 下解可缩放 → `N_init` 大小不改变 shape

**🟡 改进点（v2）**：
1. `ω` 范围 `[10⁻³, 1]` 与 `λ₀` 范围 `[10⁻⁶, 10⁻¹]` 可能不匹配：当 `ω/λ₀ ≫ 1`（快调制慢衰变）→ 振荡周期内 `N` 几乎不变 → 调制对 `N(t)` 影响仅是小波动；当 `ω/λ₀ ≪ 1`（慢调制快衰变）→ `N` 已衰完才看到调制。**关键 detectable 区间是 `ω ~ λ₀`** → 当前采样均匀 LogUniform 不保证落在此区间。建议条件采样 `ω / λ₀ ∈ [0.1, 10]`。
2. `ε` 下界 0.05 与 catalog 一致 ✓

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (LAM0_MIN <= params.lam0 <= LAM0_MAX): return False
    if not (EPS_MIN <= params.eps <= EPS_MAX): return False
    if not (OMEGA_MIN <= params.omega <= OMEGA_MAX): return False
    if params.eps >= 0.5: return False   # λ(t) > 0 ∀t
    if params.N_init <= 0: return False
    return True
```

- 边界检查 ✓
- **`ε < 0.5` 硬约束** → `λ(t) = λ₀(1 + ε cos(ωt)) ∈ [λ₀(1-0.5), λ₀(1+0.5)] = [0.5λ₀, 1.5λ₀] > 0` ∀t ✓
- 实际 sampler 已 `ε ≤ 0.40`，validator 再次冗余保护 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 衰变场景 `N(t), λ_eff(t)`（包括时变速率！）
- 32 工具

**藏**：
- shift label `γ-12-2 / T-trans broken`
- `λ(t) = λ₀(1 + ε cos(ωt))` 公式
- `ω, ε` 参数
- "外场参数泵入" 物理图像

**Agent 必须发现**：
1. `N(t)` 偏离 `e^{-λ₀t}`，残差有振荡 → 怀疑时变 `λ`
2. 测 `d ln N / dt` → 给出 `λ_eff(t)`
3. FFT 拟合振荡频率 → `ω`；幅度 → `ε`
4. 验 T-rev：`t → -t` 数据应对称 → 区别于 dual-break shifts

**Bonus**：`broken_symmetry: "T_translation"` 或 `"time_translation"` 加 0.10。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 参数共振 / Floquet motif；外场免疫 → counterfactual |
| 公式数学正确 | ✅ | `cos(ωt)` 偶 → T-rev 保；闭式积分 verified |
| T-trans 真破 | ✅ | `λ(t)` 显含 `t` |
| T-rev 保（R1-fix 核心） | ✅ | cos 偶函数 |
| 其他对称性保留 | ✅ | 线性 / Markov / 粒子守恒 |
| 代码 ↔ catalog 一致 | ✅ | 闭式积分；无 `φ` 参数 |
| 采样分布合理 | ⚠️ | `ω / λ₀` 比率未约束，detectable 区间不保证 |
| 数值安全 | ✅ | `λ(t) > 0` 双重守住 |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. 条件采样 `ω / λ₀ ∈ [0.1, 10]` 保证调制在 `N(t)` 上可见
2. spec / sim 层支持负 `t`，让 T-rev 可数值验证

---

**γ-12-2 verdict**：物理 / 代码 / 设计**全 PASS**（R1-fix `φ ≡ 0` 教科书级 — 单破缺约定的严格执行）。

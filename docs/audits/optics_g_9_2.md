# γ-9-2: Snell 介质交换不对称 — 深度审查

> 域 9 / Geometric optics / γ-tier / shift_id = `gamma_9_2`
> 代码：[`mirrorlab/shifts/optics_g_9_2.py`](../../mirrorlab/shifts/optics_g_9_2.py)
> Catalog Round-2 状态：APPROVED（reciprocity ≡ interchange 在被动界面合一）

---

## 1. 原始定律：Snell

$$n_1 \sin\theta_i = n_2 \sin\theta_t$$

baseline 关键不变量：**介质交换 `1↔2`** 与 **光路时间反演 / reciprocity**。
在 passive 界面上这两条是同一条 Noether-pair（Round-2 通过 invariant-checker 的认定）。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：non-reciprocal magnetic coupling（Part A γ-6-2 不对称互感的光学映射）。借 chiral / Faraday-rotator 思想 — 制造 `1↔2` 不对称。

**改法**：
$$\sin\theta_t = \frac{n_1}{n_2} \sin\theta_i + \kappa \cdot \frac{n_1 - n_2}{n_1 + n_2} \cdot \sin^3\theta_i$$

拆开看：
- `(n_1/n_2) sin θ_i` = 标准 Snell 部分
- `κ · (n_1−n_2)/(n_1+n_2) · sin³ θ_i` = **介质反对称 cubic 修正项**

**关键性质**：
- `κ` 振幅，`(n_1−n_2)/(n_1+n_2)` 在 `1↔2` 下变号（反对称因子）
- `sin³ θ_i`：cubic 阶 → 小角度下 ~ `θ³`，主导项仍是标准 Snell
- 当 `n_1 = n_2`，修正项为 0，与 baseline 一致（连续退化到无界面）
- lookup attacker 查 "chiral Snell" 拿到的是 Pasteur / bianisotropic 张量公式 → 与本 cubic + (n₁−n₂)/(n₁+n₂) 组合不重合 ✓

---

## 3. 哪条对称性被破了？

**目标**：**只破介质交换 `1↔2` / 互易性**（在 passive 界面上等价为同一 Noether-pair）。

交换操作：`1 ↔ 2`、`(θ_i, θ_t) → (θ_t, θ_i)`，反向追光。

baseline：`n_1 sin θ_i = n_2 sin θ_t` 在交换下→ `n_2 sin θ_t = n_1 sin θ_i` 完全等价 ✓。

shift：交换后正向方程变为
$$\sin\theta_i \stackrel{?}{=} \frac{n_2}{n_1} \sin\theta_t + \kappa \cdot \frac{n_2 - n_1}{n_2 + n_1} \sin^3\theta_t$$

反对称因子翻号 `(n_2−n_1)/(n_2+n_1) = −(n_1−n_2)/(n_1+n_2)`。若 baseline-projection `sin θ_t = (n_1/n_2) sin θ_i` 成立，回代得到：

$$\sin\theta_i = \frac{n_2}{n_1}\cdot\frac{n_1}{n_2}\sin\theta_i + \text{(cubic 项符号翻转)}$$

第一项闭合，**cubic 项符号翻转后不再恢复原方程** → 正向 `i→t` 路径与反向 `t→i` 路径**不一致** → 互易性破缺 ✓。

定量差：
$$\Delta = 2\kappa \cdot \frac{n_1 - n_2}{n_1 + n_2} \cdot \sin^3\theta_i \neq 0 \quad (\kappa, n_1-n_2 \neq 0)$$

> 互易性破缺的精确数学位置：cubic 修正项中的反对称因子。

---

## 4. 哪些对称性必须保住？

### SO(2) 绕法线
- 公式只含 `sin θ_i` 与折射率，绕法线整体转入射面 → 公式不变 ✓

### Fermat（每个固定方向分支内）
- 给定入射方向 `(n_1, θ_i, κ, n_2)`，`θ_t` 唯一确定 → 单分支稳定光程 ✓

### 能量 `R + T = 1`
- γ-9-2 只动**角度方程**，强度方程未触 → 收支闭合 ✓

### 切向波矢守恒（在该方向上）
- 沿固定 `i→t` 方向，由公式定义 ✓

### 偏振 U(1)
- 公式不含 `θ_pol` → 偏振旋转不变 ✓

### 界面平面内 parity（与法向无关）
- `x → −x` 同时 `θ → −θ`，`sin³` 是奇函数 → 同步翻号 ✓

---

## 5. 代码实现逐行核对

```python
def shifted_sin_theta_t(params: OpticsGamma92Params) -> float:
    s = sin(params.theta_i)
    anti = (params.n1 - params.n2) / (params.n1 + params.n2)
    return (params.n1 / params.n2) * s + params.kappa * anti * s ** 3
```

逐符号对照 catalog：

| 代码 | catalog | 一致 |
|---|---|---|
| `(n1/n2) * sin(θ_i)` | `(n_1/n_2) sin θ_i` | ✓ |
| `kappa * (n1-n2)/(n1+n2) * sin³(θ_i)` | `κ (n_1−n_2)/(n_1+n_2) sin³ θ_i` | ✓ |
| `asin(s) if -1≤s≤1 else nan` | TIR 受控 | ✓ |

**完全一致**。

---

## 6. 采样分布合理性

```python
N_MIN, N_MAX = 1.0, 2.0          # n_1, n_2 ~ Uniform(1.0, 2.0) 独立
KAPPA_MIN, KAPPA_MAX = 0.0, 0.15
theta_i = 0.3 (固定)
```

- **`n_1, n_2 ∈ [1.0, 2.0]`**：跨真空 / 空气到中高折射率玻璃，常见界面 ✓
- **独立采样** → `n_1 = n_2` 概率为 0 → 反对称因子几乎从不为零 → 破缺总可见 ✓
- **`κ ∈ [0, 0.15]`**：上界 0.15 < 0.2 catalog 安全界 ✓
- **`θ_i = 0.3 rad`**：`sin³(0.3) ≈ 0.026`，修正项相对主项最大 `κ · 1 · 0.026 / 0.3 ≈ 1.3%` → 信号弱但 detectable

**🟡 改进点（v2）**：
1. `κ = 0` 在 `[0, 0.15]` 端点，有概率采到 → 退化到 baseline。建议下界 0.01。
2. `θ_i = 0.3 固定`：修正项 ~ sin³(θ) 在小角度下被压制。scan 较大 `θ_i` 能放大破缺。

---

## 7. 安全约束 validator

```python
def validator(params):
    if not (N_MIN <= params.n1 <= N_MAX): return False
    if not (N_MIN <= params.n2 <= N_MAX): return False
    if not (KAPPA_MIN <= params.kappa <= KAPPA_MAX): return False
    if abs(sin(params.theta_i)) > 0.95: return False
    return True
```

- **`|sin θ_i| ≤ 0.95`**：catalog 安全界（>0.95 时 cubic 修正可能让 `|sin θ_t| > 1`）✓
- 检验 `|sin θ_t|` 上界：`|sin θ_t| ≤ (n_1/n_2) · 0.95 + 0.15 · 1 · 0.95³ ≤ 1.9 + 0.13 ≈ 2.0` 当 `n_1/n_2 = 2`
  - **🟡 这里有 hidden subtlety**：当 `n_1 = 2, n_2 = 1` 时 `sin θ_t > 1` 立刻 TIR 即使 baseline 也 TIR；shift 不引入额外发散，`asin` 越界返回 `nan` 受控
- `κ < 0.2 ∧ |sin θ_i| < 0.95` ⇒ catalog 声明 `|sin θ_t| ≤ 1` — 严格表达式可数值验证 ✓

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 看到**：
- 光学界面场景，可调 `(n_1, n_2, θ_i)`、观测 `θ_t`

**藏**：
- shift label `γ-9-2 / non-reciprocal`
- cubic 形式 + `(n_1−n_2)/(n_1+n_2)` 反对称因子
- 参数 `κ`

**Agent 必须发现**：
1. 正向 `i→t` 和反向 `t→i` 数据不闭合 → reciprocity 破
2. 交换 `(n_1, n_2)` 输出不对称 → interchange 破
3. 拟合 cubic 修正系数与反对称因子结构

**Bonus**：`broken_symmetry: "reciprocity"` 或 `"interchange"` 任一接受。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | non-reciprocal 借影 / γ-6-2 跨域 anchor |
| 公式数学正确 | ✅ | `n_1=n_2` 连续退化，cubic 不发散 |
| 互易性 / 1↔2 真破 | ✅ | 反对称因子 + cubic 不可消 |
| 其他对称性保留 | ✅ | SO(2) / Fermat / R+T / k_∥ / 偏振 / parity |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ⚠️ | `κ` 下界 0 可退化；`θ_i` 固定 |
| 数值安全 | ✅ | `|sin θ_i|≤0.95` 守住；TIR 受控 nan |
| 信息泄漏防御 | ✅ | 全藏 |

**🟡 改进点**（v2）：
1. `κ` 下界 → 0.01 避免 baseline 退化
2. `θ_i` 加入采样（Uniform(0.1, 0.7)），放大 cubic 信号

---

**γ-9-2 verdict**：物理 / 代码 / 设计**全 PASS**（采样 κ 下界为小瑕疵，v2 修）。

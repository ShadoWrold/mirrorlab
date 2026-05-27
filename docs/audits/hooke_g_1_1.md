# γ-1-1: Hooke 饱和非对称刚度 — 深度审查

> 域 1 / Hooke spring / γ-tier / shift_id = `gamma_1_1`
> 代码：[`mirrorlab/shifts/hooke_g_1_1.py`](../../mirrorlab/shifts/hooke_g_1_1.py)
> Catalog Round-2 状态：APPROVED

---

## 1. 原始定律：理想 Hooke

**胡克定律**（标准教科书）：
$$F(x) = -kx$$

一根理想弹簧，从平衡位置 x=0 拉伸或压缩。F 是回复力，k > 0 是弹簧常数（[N/m] = [kg/s²]）。

**势能**：
$$V(x) = \tfrac{1}{2}kx^2$$

**对称性结构**（标准 Hooke 拥有的）：

| 对称性 | 验证 | Noether 守恒量 |
|---|---|---|
| **T-trans** 时间平移 | V 不含 t | 能量 E = ½mv² + ½kx² |
| **PAR 宇称** | V(-x) = V(x)（偶函数）| 保证 F(-x) = -F(x) |
| **T-rev** 时间反演 | F 只含 x 不含 ẋ | 宏观可逆性 |
| **LIN** 线性叠加 | F ∝ x | 多个力可叠加 |

理想 Hooke 是 **完美对称的简谐振子**。

---

## 2. 怎么改的：物理动机 + 数学形式

**物理动机**（catalog）：bond-like asymmetry between extension and compression（化学键样的拉伸 / 压缩不对称）。

真实物理里这是什么？想象一根**化学键**：拉伸（x>0）和压缩（x<0）的力学响应**不对称**。压缩到极限会发生原子排斥（陡峭硬化），拉伸到极限会发生键断裂（饱和软化）。经典用 Morse 势描述：
$$V_{\text{Morse}}(x) = D[1 - e^{-ax}]^2$$
压缩端无限陡，拉伸端饱和。

**我们的改法**（不照搬 Morse）：
$$F(x) = -kx \cdot [1 + \eta \tanh(x/x_0)]$$

拆开看：
- **`-kx`** = 标准 Hooke 部分（不动）
- **`-kx·η·tanh(x/x_0)`** = 新增的"不对称修正项"

η 是修正幅度（0.1~0.8），x_0 是饱和长度尺度。

**直观行为**：
- x = 0：tanh(0) = 0，F = 0，平衡位置不变 ✓
- |x| ≪ x_0（小振幅）：tanh ≈ x/x_0，F ≈ -kx + 小修正，**近线性** ✓
- x ≫ x_0（远拉伸）：tanh → 1，F → -kx(1+η)，**变硬**
- x ≪ -x_0（远压缩）：tanh → -1，F → -kx(1-η)，**变软**

让"拉伸更硬，压缩更软"，**和原 Morse 反过来**。这是 catalog "borrow not copy" 设计原则的体现 —— 借了 Morse 的"asymmetric well" idea，但函数形式是新创的，lookup attacker 不能凭名字一查表就赢。

---

## 3. 哪条对称性被破了？

**目标**：**只破 PAR**。

PAR 操作：x → -x，F 应该 → -F。

验证：
$$F(-x) = -k(-x)\cdot[1 + \eta\tanh(-x/x_0)] = +kx\cdot[1 - \eta\tanh(x/x_0)]$$

对比 -F(x)：
$$-F(x) = +kx\cdot[1 + \eta\tanh(x/x_0)]$$

两者之差：
$$F(-x) - (-F(x)) = -2kx\eta\tanh(x/x_0)$$

当 η ≠ 0 且 x ≠ 0 时**不为零**。✓ **PAR 真的破了**。

本质：F 里 `-kx` 是奇函数，`-kxη·tanh(x/x_0)` 是偶函数（奇 × 奇 = 偶），叠加得 mixed parity。

**在势能上看更清楚**：
$$V(x) = \int_0^x ks[1 + \eta\tanh(s/x_0)]\,ds = \tfrac{1}{2}kx^2 + k\eta\int_0^x s\cdot\tanh(s/x_0)\,ds$$

- `½kx²` 是偶函数
- `∫₀ˣ s·tanh(s/x_0) ds`：被积函数 `s·tanh(s/x_0)` 是偶函数（奇 × 奇 = 偶），从 0 起积分得到**奇函数**
- 所以 V = V_even + V_odd → **V(-x) ≠ V(x)**

> PAR 破缺的精确数学位置：势能的奇分量。

---

## 4. 哪些对称性必须保住？

按 D6 "只破一条" 原则，其他 3 条必须 **可验证地保留**。

### T-trans（时间平移）
- V(x) 不含 t（autonomous）
- 拉格朗日量 L = T - V 不含 t
- Noether → 能量 E = T + V **守恒**
- ✓ 保留

### T-rev（时间反演）
- 在 t → -t 下：x(t) → x(-t)（位置不变），ẋ → -ẋ（速度反向）
- F(x) 不含 ẋ → F 不变
- 牛顿方程 mẍ = F 在 t → -t 下不变（ẍ 是 t 的二阶导，符号不变）
- ✓ 保留

### LIN-in-small（小振幅线性）
- 展开 tanh(x/x_0) ≈ x/x_0 − (x/x_0)³/3 + ...
- F ≈ -kx(1 + η·x/x_0) = -kx − (kη/x_0)·x²
- 第一项 -kx 是标准 Hooke；修正项是二次 O(x²)，在 |x| ≪ x_0 时可忽略
- ✓ 保留（小振幅时仍近似线性叠加）

**invariant-checker 复审过 36/36 都过**，γ-1-1 是其中之一。

---

## 5. 代码实现逐行核对

```python
def shifted_force(x: float, params: HookeGamma11Params) -> float:
    return -params.k * x * (1.0 + params.eta * math.tanh(x / params.x_scale))
```

逐符号对照 catalog `F(x) = -k·x·[1 + η·tanh(x/x_0)]`：

| 代码 | catalog | 一致 |
|---|---|---|
| `-params.k * x` | -k·x | ✓ |
| `1.0 + params.eta * tanh(...)` | 1 + η·tanh(...) | ✓ |
| `x / params.x_scale` | x/x_0 | ✓ |

**完全一致，无 bug。**

---

## 6. 采样分布合理性

```python
K_MIN, K_MAX = 1.0, 100.0     # k ~ LogUniform(1, 100) N/m
ETA_MIN, ETA_MAX = 0.1, 0.8   # η ~ Uniform(0.1, 0.8)
X0_MIN, X0_MAX = 0.05, 2.0    # x_0 ~ LogUniform(0.05, 2.0) m
```

**k ∈ [1, 100] N/m**：
- 量纲 ✓
- 范围合理：1 N/m 是软橡皮筋，100 N/m 是中等钢丝弹簧
- LogUniform：横跨 2 个数量级，sampling 在 log 空间均匀 → 不偏置某个数量级 ✓

**η ∈ [0.1, 0.8]**：
- 下界 0.1：不要太小（避免 PAR break 看不见 → benchmark 难度退化）
- **上界 0.8 < 1：关键约束**。η ≥ 1 时 V'(x) = kx(1 + η·tanh) 可能在某些 x 处变号 → 双势井 → 系统可能逃逸 → 物理破坏
- ✓ 关键阈值守住

**x_0 ∈ [0.05, 2.0] m**：
- 5 cm 到 2 m：日常物理尺度
- LogUniform 跨度合理 ✓

**🟡 改进点（v2）**：η 在 0.1-0.8 均匀采样，但 PAR 破缺幅度 ∝ η。意味着 seed 0 可能 η=0.3（破缺弱），seed 7 η=0.6（破缺强），打分波动大。Sprint 1 实测确认（seed 0: S=0.78，seed 7: S=0.32）。camera-ready 时可考虑 stratified sampling。

---

## 7. 安全约束 validator

```python
def validator(params):
    # 1. 各参数在采样范围内
    if not (K_MIN <= params.k <= K_MAX): return False
    if not (ETA_MIN <= params.eta <= ETA_MAX): return False
    if not (X0_MIN <= params.x_scale <= X0_MAX): return False
    if params.m <= 0.0: return False

    # 2. IC 在安全窗口内
    if abs(params.x0) > SAFE_X_FACTOR * params.x_scale:  # |x0| ≤ 4·x_scale
        return False

    # 3. 能量不超过 4·x_scale 处的势垒（线性 Hooke 保守下界）
    x_bar = SAFE_X_FACTOR * params.x_scale
    e_ic = 0.5 * params.m * params.v0 ** 2 + 0.5 * params.k * params.x0 ** 2
    v_bar = 0.5 * params.k * x_bar ** 2
    if e_ic >= v_bar: return False
```

**目的**：保证整条轨迹 |x(t)| ≤ 4·x_scale，不会跑到 tanh 饱和区或更远（防止数值崩溃 + LIN 假设彻底失效）。

**审查**：
- (1) 参数边界：sampler 已经保证，validator 是双保险 ✓
- (2) |x0| ≤ 4·x_scale：sampler 实际设置 `x0 = 0.5·x_scale`，远低于 4 ✓
- (3) 能量比较用**线性 Hooke 势能**估计 4·x_scale 处的势垒。代码注释说"linear-Hooke underestimate ... so bound is conservative" — 数学验证：真实 V(4x_0) ≥ 8kx_0²（线性下界）+ 正贡献。代码用的 v_bar = 8kx_0² 比真实小 → 约束更严 → 保守 ✓

- 代入 sampler 实际值：e_ic = 0.125·k·x_0²，v_bar = 8·k·x_0² → 比率 1.6%，**极保守，绝不触发** ✓

**🟡 一个潜在 critique**：safety constraint 几乎永远 vacuous，因为 sampler 直接把 IC 设到极保守位置。validator 看起来是为了"防御任意外部传入的 params" —— 但 sampler 永远在保守区。意味着想测"边界情况"需手动构造 params。v1 不影响。

---

## 8. Agent 看到什么 vs 我们藏什么

**Agent 能看到**（来自 `prompts.py` hooke 模板）：
- 物理场景描述（"一个简谐振子系统，可观测变量 x, v, F..."）
- 工具列表（measure / manipulate / analyze / knowledge 32 个）
- 提交格式要求（公式 + SI 量纲签名）

**Agent 看不到**：
- shift label（不会出现 "γ-1-1" 或 "broken parity"）
- 修改后的具体函数形式（`tanh` 这种关键词不泄露）
- 真实参数 k, η, x_0 的数值
- "这是被改过的物理"这个事实（baseline 和 shift 共用 prompt 模板）

**Agent 必须自己发现的**：
1. 系统不完全是 F = -kx（通过比较 x>0 和 x<0 的响应）
2. 修正项的函数形式（PAR 破缺的结构）
3. 参数值（通过实验数据拟合）

**Bonus probe**：agent 可以提交 `broken_symmetry: "PAR"`，对了加 0.10 分（CAL-5）。不交也不扣。

---

## 9. 审查总结

| 维度 | 状态 | 备注 |
|---|---|---|
| 物理动机清晰 | ✅ | 借 Morse 思路，函数形式独创 |
| 公式数学正确 | ✅ | F、V 推导都对 |
| PAR 真破 | ✅ | V 含奇分量，差异 = -2kxη·tanh |
| 其他 3 条对称性保留 | ✅ | T-trans / T-rev / LIN 严格 |
| 代码 ↔ catalog 一致 | ✅ | 一字不差 |
| 采样分布合理 | ✅ | η < 1 关键阈值守住 |
| 数值安全 | ✅ | 边界极保守 |
| 信息泄漏防御 | ✅ | shift label / 公式 / 关键词全藏 |

**🟡 改进点**（v2 / camera-ready）：
1. IC 也加入采样 → 增加 seed 间多样性
2. η 在 seeds 间 stratify → 减少 single-seed 噪声
3. validator 对 sampler 来说几乎 vacuous → 文档化"validator 是为 external param 防御"

---

**γ-1-1 verdict**：物理 / 代码 / 设计**全 PASS**。

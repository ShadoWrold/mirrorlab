# R1 物理一致性调研报告：NewtonBench 12 域的对称性结构与安全 γ/δ shift

> 任务 #1 输出。作者：physics-researcher。日期：2026-05-22。
>
> 目的：为 D6（"一次只破一个对称性"偏移原则）提供物理学层面的安全 shift 清单 + 风险评估。

---

## 0. 方法论与免责声明

### 0.1 工作原则

- 每个 shift 候选必须**明确标注它破坏哪条对称性 / 守恒律**，并验证其他对称性（因果性、确定性、数值稳定性）仍保持。
- 所有候选必须有**真实物理先例**（modified gravity / MOND / Lorentz violation / anisotropic cosmology / 非牛顿流变 / 非线性光学 / hyperbolic heat 等）。
- 排除"看起来可行但物理上有死结"的偏移（详见第 14 节风险列表）。

### 0.2 NewtonBench 12 域的不确定性

简报与设计笔记给出 "12 个 sim"，明确点名的只有 gravity / coulomb / hooke / snell / fourier / damped harmonic 等。**本报告基于物理教科书的"经典 12 定律"列表重建**，并在第 13 节标注每个域是否需要回到 NewtonBench 源码（arxiv 2510.07172, HKUST-KnowComp/NewtonBench）核对。**v1 起步范围（Hooke / Gravity / Damped / Coulomb / Heat transfer / Fourier）有 5/6 与简报直接对齐**，这部分结论高置信度。

### 0.3 对称性记号

为表格紧凑性，下文使用：

```
T-trans     时间平移不变 → 能量守恒
S-trans     空间平移不变 → 动量守恒
ROT         空间旋转不变（各向同性）→ 角动量守恒
T-rev       时间反演对称
PAR         空间反演（宇称）
GAL         伽利略不变性（低速）
SCALE       尺度（重整化群 / 量纲）不变性
LIN         线性叠加原理
DET         确定性（ODE Lipschitz、无 blow-up）
CAU         因果性（信息速度有上界）
```

---

## 1. Newton 万有引力 (Gravity)

**标准律**：F = G m₁ m₂ / r² 沿径向，对称结构：T-trans / S-trans / ROT / T-rev / PAR / GAL / 逆平方→ Gauss/Bertrand。守恒：E, p, L；额外性质：闭合椭圆轨道（Bertrand 定理）、等效原理。

| Shift ID | 形式 | 破坏的对称性 | 其他守恒 | 数值稳定性 | 真实先例 |
|---|---|---|---|---|---|
| G-γ1 | F = G m₁m₂ / r^(2+ε), ε 小（≤0.1） | Bertrand 闭合轨道；GR 对应 Schwarzschild 进动 | E, p, L 仍守恒（中心力 + 各向同性）| 稳定，仅近心点进动 | Adelberger 2003 inverse-square test；MOG/MOND 弱场展开 |
| G-γ2 | F = G m₁m₂/r² + α e^(−r/λ)/r² (Yukawa 附加项) | 关闭逆平方的 Birkhoff 推广；尺度不变性破缺 | E, p, L 守恒；中心力 | 稳定（λ 选适当） | Adelberger 2003；fifth-force search |
| G-γ3 | F = G m₁m₂/r² 但 G 方向各向异性：G(θ̂) = G₀(1 + ξ n̂·r̂) | ROT（破各向同性）；保留 T-trans/S-trans | E, p 守恒；L **不守恒** | 稳定 | Bianchi 各向异性宇宙学；Kostelecký SME 引力扇区 |
| G-δ1 | F = G m₁m₂/r² + 显式耗散项 −η v | T-rev（不可逆）；能量不守恒 | p, L 不守恒（看作系统）| 稳定 | Chameleon screening；Dirac LNH 时变 G（弱版本） |
| G-δ2 | G → G(t) = G₀(1 + αt), α 极小 | T-trans → E 不守恒 | p, L 守恒 | 稳定（线性漂移）| Dirac large numbers；BBN 约束 |

**推荐 v1**：G-γ1（指数偏移）+ G-γ3（各向异性）+ G-δ2（时变 G）。三者破坏的对称性正交：Bertrand / ROT / T-trans。

---

## 2. Coulomb 静电 (Coulomb)

**标准律**：F = k q₁q₂/r²。对称结构与引力同构 (T/S/ROT/T-rev/PAR/Gauss)；额外：**电荷守恒**、规范不变性 U(1)。

| Shift ID | 形式 | 破坏 | 其他守恒 | 稳定性 | 真实先例 |
|---|---|---|---|---|---|
| C-γ1 | F = kq₁q₂ e^(−μr)/r² · (1 + μr) (Yukawa-Proca 静电势) | 长程 Gauss 定律（光子获质量 μ） | E,p,L,Q 守恒；U(1) 弱破缺 | 稳定 | Proca theory；Goldhaber-Nieto Rev. Mod. Phys. 2010 |
| C-γ2 | F = kq₁q₂/r^(2+ε) | 各向同性下的 Gauss 定律；PAR 保持 | E,p,L,Q 守恒 | 稳定 | 历史 Cavendish/Plimpton 实验 |
| C-γ3 | F = kq₁q₂/r² + 弱 P-奇耦合（手性偏置）| PAR | E,p,L 守恒；Q 守恒；T-rev 弱破缺 | 稳定 | 弱相互作用宇称破缺；axion-photon coupling |
| C-δ1 | 电荷耗散：q(t) = q₀ e^(−γt) | Q 守恒 + U(1) | E 不守恒 | 稳定 | millicharge / massive photon → 电荷蒸发；Okun "On the possible non-conservation of charge" |
| C-δ2 | F̃ = kq₁q₂/r² + δ·(v×B 类内禀偏置) (无外场)| GAL；T-rev | Q 守恒 | 稳定 | Lorentz 破缺（SME）|

**推荐 v1**：C-γ1（Yukawa-Proca）+ C-δ1（电荷蒸发）。
**注意**：C-γ3 与 G-γ3 在 ground-truth label 上须区分（一个破 PAR、一个破 ROT），避免 agent 用相同 ansatz 蒙混。

---

## 3. Hooke 弹性 (Hooke)

**标准律**：F = −kx，1D 线性。对称：T-trans / S-trans（沿运动方向变化）/ T-rev / LIN / SCALE（无内禀长度）/ x→−x（PAR）。守恒：E。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| H-γ1 | F = −kx − αx³ (Duffing) | LIN；SCALE | E 守恒；T-rev | 稳定（α>0 hardening；α<0 慎选避免 escape）| Duffing 1918；非线性振子标准教材 |
| H-γ2 | F = −kx − βx² (二次非线性) | LIN；x→−x (PAR) | E 守恒 | β 必须小，否则势能无下界（半边 unbounded）| 非对称弹簧；分子键 Morse 展开 |
| H-γ3 | F = −k(x) x，k(x) = k₀(1 + η|x|/L), 各向异性硬度 | LIN；x→−x（部分） | E 守恒 | 稳定 | strain-hardening 材料；橡胶弹性 |
| H-δ1 | F = −kx − cv (粘弹) | T-rev；E 守恒 | p 守恒（外力视角） | 稳定 | Kelvin-Voigt model |
| H-δ2 | F = −kx, 但 k = k(t) 缓变（参数振荡） | T-trans → E 不守恒 | 其他守恒 | 稳定（避免共振发散选合理 k(t)）| Mathieu 方程；参数共振 |

**推荐 v1**：H-γ1（Duffing，非线性叠加破缺）+ H-δ1（粘弹）。
**警告**：H-γ2（二次项）单独使用时势能 V = ½kx² + ⅓βx³ 在 x→−∞ 发散到 −∞，agent 在大振幅下会观测到 escape——可作为"故意 ill-posed"的 hidden anomaly，但需限制初始 |x| 小。

---

## 4. Snell 折射 (Snell)

**标准律**：n₁ sin θ₁ = n₂ sin θ₂；对称：界面内 ROT / T-rev（光路可逆）/ PAR / 频率独立（在非色散假设下）。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| S-γ1 | n₂(λ) = n₂₀(1 + α/λ²) (Cauchy 色散) | 频率独立性 | T-rev；ROT | 稳定 | Cauchy 公式；普通玻璃 |
| S-γ2 | 双折射：n_o ≠ n_e，n(θ_pol) = n_o cos²+ n_e sin² | 界面内 ROT（各向同性破缺） | T-rev | 稳定 | 单轴晶体（方解石）；Born & Wolf 教材 |
| S-γ3 | n₁ sin θ₁ = n₂ sin θ₂ + κ sin(2θ₁) (P-奇修正) | T-rev（小修正）+ PAR | 频率独立 | 稳定 | chiral media；optical activity |
| S-δ1 | n_eff = n + iβ (吸收) → 复 Snell 定律 | 能量守恒（光强衰减） | T-rev 弱破缺 | 稳定 | absorbing media；Fresnel with absorption |

**推荐 v1**：S-γ2（双折射，破 ROT）。这是最 "教科书" 且 agent 必须设计正确的偏振实验才能区分——非常好的 tool-use 测试。

---

## 5. Fourier 热传导 (Fourier law)

**标准律**：q = −κ ∇T；扩散方程 ∂T/∂t = α∇²T。对称：T-trans / S-trans / ROT / 扩散（**T-rev 已破**，不可逆）/ 线性。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| F-γ1 | q = −κ(T) ∇T, κ(T) = κ₀(T/T₀)^n | LIN（→非线性扩散）| T-trans/S-trans/ROT 保持 | 稳定（n>0）| 高温陶瓷；辐射主导 κ∝T³ |
| F-γ2 | **Cattaneo-Vernotte**：τ ∂q/∂t + q = −κ∇T → 双曲热方程 | "热瞬时传播"（违反 CAU）→ 修复后 CAU 成立 | LIN；其他全保 | 稳定 | Cattaneo 1958；Vernotte 1958 |
| F-γ3 | 各向异性：q_i = −κ_ij ∂_j T，κ_ij 非对角 | ROT | LIN；T-trans/S-trans | 稳定 | 单晶导热；石墨层状结构 |
| F-γ4 | 低维异常扩散：⟨x²⟩ ∝ t^α, α≠1 | Fick/Fourier 普通扩散律 | T-trans | 稳定 | Lepri-Livi-Politi 异常导热 Phys. Rep. 2003 |
| F-δ1 | 加入源/汇项：∂T/∂t = α∇²T + S(x) | 总热量守恒 | 其他 | 稳定 | 化学反应、辐射 |

**推荐 v1**：F-γ2（双曲化，破"无穷传播速度"——非常微妙、需要测瞬态信号传播）+ F-γ3（各向异性）。

---

## 6. Damped Harmonic Oscillator (Damped)

**标准律**：ẍ + 2γẋ + ω₀²x = 0。对称已经较少（T-rev 破、E 不守恒）。可加 shift 破其余对称。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| D-γ1 | 阻尼 ∝ |v|^p，p≠1（如 Coulomb 干摩擦 p=0、湍流 p=2）| 阻尼项的线性 | ω₀ 部分 | 稳定 | 干摩擦；Stokes vs Newton drag |
| D-γ2 | ẍ + 2γẋ + ω₀² x + αx³ = 0 (Duffing-damped) | LIN | T-trans → 自治系统 | 混沌（受迫时）；自治稳定 | Duffing oscillator 经典文献 |
| D-γ3 | 受迫 + 非自治频率：ω₀²(t) = ω₀²(1+ε cos Ωt) | T-trans → 参数共振 | LIN | 须避开 Mathieu 不稳定带 | Mathieu 方程 |
| D-δ1 | 负阻尼自激（van der Pol）：ẍ − μ(1−x²)ẋ + x = 0 | T-rev；能量耗散方向反转 | LIN | 极限环吸引子 | van der Pol 1920；松弛振荡 |

**推荐 v1**：D-γ1（非线性阻尼）+ D-δ1（van der Pol，破单调耗散）。

---

## 7. Pendulum (单摆，假设 NewtonBench 含)

**标准律**：θ̈ = −(g/L) sin θ；小角时退化为 SHO；周期 T = 2π√(L/g)（小角）。对称：T-trans / θ→−θ 对称 / T-rev / E 守恒。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| P-γ1 | 大角全 sin θ → 周期含椭圆积分 K(sin(θ₀/2)) | 简谐近似的等周期性（保持物理） | E, T-rev | 稳定 | 物理教材；Galileo 摆 |
| P-γ2 | 球摆（2D 球面） + Foucault 进动（地球自转） | 摆动平面的旋转不变性 | E | 稳定 | Foucault 1851 |
| P-γ3 | 双摆 / 弹簧摆（耦合） | 单一振荡周期 | E | 混沌 | 经典混沌系统 |
| P-δ1 | 阻尼摆 + 周期受迫 | E；T-rev | LIN | 混沌阈值；Strange attractor | Drazin 教材 |

**v1 不建议优先选 Pendulum**（与 SHO 重叠且摆角小时退化），如选可用 P-γ2（Foucault 进动，干净的 ROT 破缺）。

---

## 8. Ohm 电导 (Ohm)

**标准律**：V = IR；J = σE。对称：T-trans / LIN / 局域响应。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| O-γ1 | J = σE + βE³（高场非线性）| LIN | T-trans | 稳定 | Gunn 效应；半导体高场 |
| O-γ2 | Shockley 二极管：I = I_s(e^(V/V_T)−1) | LIN；V→−V (PAR) | T-trans | 稳定 | Shockley 1949 |
| O-γ3 | Hall 效应类：J_i = σ_ij E_j (反对称分量) | 时间反演 + 各向同性 | T-trans | 稳定 | Hall 1879 |
| O-δ1 | 超导 / RTS 跳变：σ → ∞ 当 T<T_c | 线性响应 | 守恒 | 数值奇异（须 regularize） | BCS 1957 |

**推荐 v1（若选 Ohm）**：O-γ2（非线性 I-V）。

---

## 9. Stefan-Boltzmann 辐射 (Stefan)

**标准律**：P = εσA T⁴。对称：T-trans / ROT。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| SB-γ1 | P = εσA T^(4+δ) (违反 Wien/Planck) | Planck 分布的 SCALE | T-trans | 稳定 | 反事实，无直接先例 → 慎用 |
| SB-γ2 | ε = ε(λ) 选择性辐射（灰体→彩色体） | 普适黑体谱 | T-trans | 稳定 | 实际材料发射率 |
| SB-γ3 | P = εσA T⁴ (1 + α cos θ) (各向异性发射) | ROT | T-trans | 稳定 | 定向辐射；天线方向图 |

**v1 不优先**（与简报 6 域重叠少）。

---

## 10. 理想气体 / Boyle (Ideal Gas)

**标准律**：PV = nRT。对称：T-trans / 状态变量对称（无微观结构）。

| Shift ID | 形式 | 破坏 | 其他 | 稳定性 | 先例 |
|---|---|---|---|---|---|
| IG-γ1 | (P + a/V²)(V − b) = nRT (van der Waals) | 点粒子近似 | T-trans | 稳定（避免 V<b）| van der Waals 1873 |
| IG-γ2 | PV = nRT(1 + B(T)/V) (维里展开) | 理想性 | T-trans | 稳定 | Mayer cluster expansion |
| IG-γ3 | PV^γ_eff = const, γ_eff(T) (变绝热指数) | 经典 5/3 普适性 | T-trans | 稳定 | 多原子分子振动自由度激活 |

**v1 不优先**。

---

## 11. Newton 冷却定律 (Cooling)

**标准律**：dT/dt = −k(T − T_env)。对称：T-trans / 线性。

| Shift ID | 形式 | 破坏 | 先例 |
|---|---|---|---|
| NC-γ1 | dT/dt = −k(T⁴ − T_env⁴) (Stefan 主导) | LIN | 高温冷却 |
| NC-γ2 | k = k(T) 非常数 | LIN | 实际对流 |
| NC-δ1 | dT/dt = −k(T−T_env) + γ(T−T_env)² (反馈) | LIN；可能跑飞 → 须限定 γ 小 | 反常对流 |

**v1 不优先**（与 Fourier 域重叠）。

---

## 12. 透镜方程 / 抛体 / 多普勒（候选填补 12 域）

NewtonBench 列表的剩余 1-2 域可能包含**薄透镜方程** (1/u + 1/v = 1/f)、**抛体运动**或**多普勒效应**。本报告暂不展开，待 R4（工程可行性）从源码确认后补全。

---

## 13. 与 NewtonBench 源码对齐的 TODO

| 域 | 简报/笔记直接提及 | 高置信？ | 备注 |
|---|---|---|---|
| Gravity | ✓ | ✓ | |
| Coulomb | ✓ | ✓ | |
| Hooke | ✓ | ✓ | |
| Snell | ✓ | ✓ | |
| Fourier | ✓ | ✓ | |
| Damped harmonic | ✓（v1 列表中）| ✓ | |
| Pendulum | ✗ | 推测 | 需对源码 |
| Ohm | ✗ | 推测 | 需对源码 |
| Stefan-Boltzmann | ✗ | 推测 | 需对源码 |
| Ideal Gas | ✗ | 推测 | 需对源码 |
| Newton Cooling | ✗ | 推测 | 需对源码 |
| Lens / Projectile / Doppler | ✗ | 推测 | 需对源码 |

**Action**：把这张表交给 R4 (工程可行性) 调研员去 fork repo 后逐域核对。

---

## 14. 风险列表（看似可行但有隐藏问题的 shift）

| 风险 ID | shift | 隐藏问题 |
|---|---|---|
| RISK-1 | H-γ2 (二次弹性) | 势能 V = ½kx²+⅓βx³ 在 x<0 大幅时无下界，agent 大幅初值 → escape；须限制采样窗口 |
| RISK-2 | G-γ1 / C-γ2 (r^(2+ε)) | ε 取负、|ε| 大时近距离吸引强度发散，碰撞前数值爆炸；须设最小距离 cutoff |
| RISK-3 | SB-γ1 (T^(4+δ)) | 违反 Wien 定律意味着同时违反量子统计 → 无 self-consistent 物理对应；建议舍弃，改用 SB-γ2 |
| RISK-4 | D-γ3 (Mathieu 参数共振) | 参数 (ε, Ω/ω₀) 落入不稳定舌时指数发散；标定时必须避开 |
| RISK-5 | F-γ2 (双曲热) | τ 太大时 wave-like 信号反弹，叠加效应使曲线拟合误判；agent 必须用瞬态测量才能识别 |
| RISK-6 | C-δ1 (电荷蒸发) | 同时破坏 U(1) 规范不变性 → 真要 self-consistent 需引入光子质量；保持 standalone 当唯象使用即可，不要让 agent 试图同时拟合电磁场结构 |
| RISK-7 | G-δ1 (耗散引力) | 同时破 T-rev 和 E 守恒，**违反"一次只破一个"** → 必须改写为"环境耗散项"，把破坏归到系统-环境耦合而非引力本身 |
| RISK-8 | 任何"加噪声型"shift | NewtonBench 已报告噪声敏感问题；如果 shift 与噪声同尺度，agent 无法区分 anomaly 与 noise → 我们的标注须保证 shift 信号 ≫ noise floor（>5σ）|
| RISK-9 | "对称性多破" | 多个 shift 叠加同一域时，agent ground truth 标签变成 multi-label 问题；v1 严格保持每个 scenario 单 shift |
| RISK-10 | G-δ2 / 任何 t-依赖参数 | 与 D6 "确定性必须保持" 冲突？答：t-依赖是确定性的（只要 G(t) 闭式给出）；但要禁止随机 G(t)；标定时显式给出函数形式 |

---

## 15. v1 推荐 shift 子集（结合简报偏好的 6 域）

| 域 | β-tier (NewtonBench 兼容) | γ-tier (我们新增) | δ-tier (守恒律) | 建议难度梯度 |
|---|---|---|---|---|
| Gravity | 改 G、改指数 (NewtonBench) | **G-γ3 各向异性**（破 ROT） | **G-δ2 时变 G**（破 T-trans）| 易 / 中 / 难 |
| Coulomb | 改 k、改指数 | **C-γ1 Yukawa**（破长程 Gauss）| **C-δ1 电荷蒸发**（破 Q）| 易 / 中 / 难 |
| Hooke | 改 k、改指数 | **H-γ1 Duffing**（破 LIN）| **H-δ1 粘弹**（破 T-rev）| 易 / 中 / 难 |
| Damped HO | 改 γ, ω | **D-γ1 非线性阻尼**（破阻尼线性）| **D-δ1 van der Pol**（耗散方向反转）| 易 / 中 / 难 |
| Heat transfer (Cooling) | 改 k | **NC-γ1 T⁴ 主导**（破 LIN）| — | 易 / 中 |
| Fourier law | 改 κ | **F-γ3 各向异性**（破 ROT），**F-γ2 双曲化**（破"瞬时传播"假设）| F-δ1 源项 | 易 / 中 / 难 |

**对称性覆盖**：v1 子集横跨 ROT / LIN / T-trans / T-rev / Q-conservation / Gauss long-range / 因果性，共 7 类对称性破缺 → 这是 paper "第一个系统基于对称性破缺设计偏移" 卖点的核心证据集。

---

## 16. 关键物理文献清单

> 全部为可在 arXiv 或 journal 获取的真实文献。未列出未核实的来源。

1. **Will, C. M. (2014).** "The Confrontation between General Relativity and Experiment." *Living Reviews in Relativity*, 17:4. arXiv:[1403.7377](https://arxiv.org/abs/1403.7377).
   *Gist*：PPN 形式系统综述，给出 modified gravity 各种偏移的实验约束（Cassini γ_PPN、月地测距、双脉冲星）。是 G-γ shift 标定上界的权威来源。

2. **Kostelecký, V. A. & Russell, N. (2011).** "Data tables for Lorentz and CPT violation." *Rev. Mod. Phys.* 83, 11. arXiv:[0801.0287](https://arxiv.org/abs/0801.0287)（持续更新版）。
   *Gist*：Standard-Model Extension (SME) 系数实验上限表，覆盖光、引力、强子各扇区——为 ROT 破缺、PAR 破缺型 shift 提供数量级参考。

3. **Goldhaber, A. S. & Nieto, M. M. (2010).** "Photon and graviton mass limits." *Rev. Mod. Phys.* 82, 939. arXiv:[0809.1003](https://arxiv.org/abs/0809.1003).
   *Gist*：光子 / 引力子质量实验上限综述，Yukawa-Proca 偏移（C-γ1, G-γ2）的物理动机。

4. **Milgrom, M. (1983).** "A modification of the Newtonian dynamics as a possible alternative to the hidden mass hypothesis." *ApJ* 270, 365. （Open access via NASA ADS。）
   *Gist*：MOND 原论文：低加速度下 F=m a μ(a/a₀)。提供"加速度阈值型"非线性引力偏移先例。

5. **Bekenstein, J. D. (2004).** "Relativistic gravitation theory for the MOND paradigm." *Phys. Rev. D* 70, 083509. arXiv:[astro-ph/0403694](https://arxiv.org/abs/astro-ph/0403694).
   *Gist*：TeVeS——MOND 的相对论化。证明 modified gravity 可以做到 self-consistent。

6. **Lepri, S., Livi, R., Politi, A. (2003).** "Thermal conduction in classical low-dimensional lattices." *Phys. Rep.* 377, 1. arXiv:[cond-mat/0112193](https://arxiv.org/abs/cond-mat/0112193).
   *Gist*：1D/2D 晶格中 Fourier 定律失效，导热率发散——F-γ4 异常扩散的标准引用。

7. **Cattaneo, C. (1958)** "Sur une forme de l'équation de la chaleur éliminant le paradoxe d'une propagation instantanée." *Comptes Rendus* 247, 431. （以及 Vernotte 同年同源。）
   *Gist*：双曲热方程的原始动机——修复 Fourier 定律"无穷信号速度"的因果性问题。F-γ2 的来源。

8. **Adelberger, E. G., Heckel, B. R., Nelson, A. E. (2003).** "Tests of the gravitational inverse-square law." *Annu. Rev. Nucl. Part. Sci.* 53, 77.
   *Gist*：Eöt-Wash 组 sub-mm 引力实验综述，给出 G-γ1（r^(2+ε)）和 G-γ2（Yukawa）的实验约束区。

9. **Mattingly, D. (2005).** "Modern tests of Lorentz invariance." *Living Rev. Relativity* 8, 5. arXiv:[gr-qc/0502097](https://arxiv.org/abs/gr-qc/0502097).
   *Gist*：Lorentz 破缺各种唯象模型（双特殊相对论、Horava 引力、SME 等）+ 实验约束。

10. **Bertotti, B., Iess, L., Tortora, P. (2003).** "A test of general relativity using radio links with the Cassini spacecraft." *Nature* 425, 374.
    *Gist*：PPN γ - 1 = (2.1 ± 2.3)×10⁻⁵——为 Gravity 域 shift 强度的"标定级"上界提供参考。

11. **Will & Nordtvedt (1972).** "Conservation Laws and Preferred Frames in Relativistic Gravity." *ApJ* 177, 757.
    *Gist*：PPN 框架下守恒律破缺与"优先参考系"shift 的系统分类——直接对应 D6 的对称性分类哲学。

12. **Duffing, G. (1918).** *Erzwungene Schwingungen bei veränderlicher Eigenfrequenz und ihre technische Bedeutung.* Vieweg.（教科书级，无 arXiv。可引用 Strogatz "Nonlinear Dynamics and Chaos" Ch. 12 替代）。
    *Gist*：非线性振子 ẍ + δẋ + αx + βx³ = γ cos ωt 的鼻祖论文。H-γ1 / D-γ2 来源。

---

## 17. 结论与给 team-lead 的建议

1. **v1 推荐 18 个 shift（6 域 × 3 tier）**，对称性破缺类型横跨 7 类，足以作为 paper 卖点 #4 ("第一个系统基于对称性破缺设计偏移") 的实证集。
2. **关键风险**：RISK-7 (G-δ1 多对称性同时破) **必须在 v1 spec 中显式禁止**；RISK-3 (SB-γ1 违反量子统计) 建议从候选池中移除。
3. **与 R4 对接**：第 13 节 TODO 表已列明需源码核对的域，建议 R4 调研员优先确认。
4. **与 E2（评测协议）对接**：每个 shift 必须配 ground-truth "对称性 label"（multi-class 或 multi-hot），用以分开测 anomaly identification（"知道哪条对称性被破"）与 characterization（"准确写出偏移定律形式"）。这呼应卖点 #3。
5. **物理保险丝**：建议在 v1 sim 装一个 invariant checker——每个 shift 启用时自动校验"该破的破了、不该破的没破"，否则报错。这能防止标定阶段意外引入 multi-symmetry shift。

---

*报告结束。*

# MirrorLab 架构设计:参考优秀项目 + 逐结构讲解

> 目的:在动手重构前,先把目标架构讲清楚——参考成熟项目怎么解决"同一东西散落多处",每个结构为什么这么设,你我共同确认后再实施。

---

## 一、我们的核心病症(一句话)

**一个 cell 的定义散落在 7 个地方,破缺公式重复 3 遍,7 张并行查找表。**
加/改一个 cell 要同步改 5-7 个文件——这叫 **shotgun surgery(霰弹式修改)**,是公认的代码坏味道。

成熟项目都用同一个药方治它:**单一数据源(Single Source of Truth)+ 注册表(Registry)+ 从声明派生(Derive, don't repeat)。**

---

## 二、三个参考项目(都和我们处境高度相似)

### 参考1:Gymnasium(OpenAI Gym 后继)— Registry 模式
**它的处境**:成百上千个强化学习环境,每个要被"创建、列举、包装、向量化"等多种系统消费。如果每个系统各存一份环境列表,就是我们的 7 张并行表。

**它的解法**:
```python
gym.register(id="GridWorld-v0", entry_point=GridWorldEnv, max_episode_steps=300)
env = gym.make("GridWorld-v0")   # 所有人通过 id 创建,不直接 import 类
```
- 一个 `EnvSpec` dataclass 装下环境的全部元信息(id、怎么构造、配置上限)。
- **注册表把"定义"和"使用"解耦**:加新环境只 `register` 一次,所有工具自动支持。

**映射到我们**:`CellSpec` ≈ `EnvSpec`;`register_cell(CELL)` ≈ `gym.register`;`load(domain, shift)` ≈ `gym.make`。
**好消息**:我们**已经有这个模式的雏形**——`loader_shifts/__init__.py` 的 `register()/get()` 就是 mini-registry,只是只管 grid builder 一种东西。CellSpec 把它升级成管全部。

### 参考2:Pydantic / Python dataclass — 字段元数据派生
**它的处境**:一个数据模型的每个字段,要同时驱动"校验、序列化、JSON schema、数据库列名"。如果每处各写一遍,就是我们的"破缺公式重复 3 遍 + cf 两张表"。

**它的解法**:把每个字段的属性**声明在字段本身上**,所有系统从字段读:
```python
# Pydantic
name: str = Field(alias='username', description='...')   # 校验/序列化/schema 全从这里派生
# 标准库 dataclass(我们能直接用,无新依赖)
G: float = field(metadata={"mirrorlab": {"role": "law", "canonical": "G"}})
```
- dataclass 的 `field(metadata=...)` 是 Python 官方留的"第三方扩展点"——存一个只读 mapping,库自己读。
- **关键原则**:字段声明是唯一真相,校验/序列化/schema 都是它的**投影**,不可能 drift。

**映射到我们**:我已证实 `_LAW_PARAM_FIELDS`(哪些字段是 law)和 `_PREDICTOR_NAME_MAP`(canonical 名)的 **key 集合 48 个 cell 全部完全一致**——它们就是字段的两个属性(role + canonical),本该长在字段上。

### 参考3:我们自己的 ShiftImpl — 已有的内部先例
```python
@dataclass(frozen=True)
class ShiftImpl:
    law: Callable      # 破缺公式(已经是可复用 callable!)
    sampler: Callable
    validator: Callable
```
**每个 shift 已经导出 ShiftImpl**。它已经把 law/sampler/validator 收成一个对象——CellSpec 只是**继续往上收**(把 grid 范围、output 通道、broken_symmetry、字段 role 也收进来),让它成为真正的全量单一数据源。

---

## 三、目标架构:逐结构讲解(每个为什么这么设)

### 结构1:字段 role 元数据(单一数据源的最小单元)
```python
from mirrorlab.spec import P   # P = 元数据 helper

@dataclass(frozen=True)
class GravityGamma22Params:
    G: float       = field(metadata=P.law("G"))        # role=law, canonical="G"
    M: float       = field(metadata=P.law("M"))
    m: float       = field(metadata=P.mass())          # role=mass → cf 不扰动
    alpha: float   = field(metadata=P.law("alpha"))
    omega: float   = field(metadata=P.law("omega"))
    r_scale: float = field(metadata=P.law("r_scale"))
    r0: float      = field(metadata=P.ic())            # role=ic(初始条件)→ cf 不扰动
    v0: float      = field(metadata=P.ic())
```
**为什么这样设**:
- 每个字段的"身份"(是 law 系数?初始条件?观测轴?)和它的 canonical 名,**就写在它旁边**——读代码的人一眼看懂这个字段的角色,不用去翻 counterfactual.py 的两张表对照。
- `role` 有 4 种:`law`(被 cf 扰动 + 有 canonical 名)、`mass`/`ic`/`axis`(cf 排除)。**这正是把你们之前修对的 bug 固化成数据**:wave γ-8-1 的 k 标 `role=axis` → 永远不会被 cf 误扰动(否则 (c) oracle 被 cap,就是当初的 bug)。
- `P.law("G")` 里的 "G" 是 canonical 名——**显式存储,不靠算法推导**。因为我看过实际数据:canonical 命名是不规则的(`k0→k` 但 `L1→L_1`、`q_src→q_1`),没有简洁规则,本质就是人工标注。硬编码反而清晰可审。

### 结构2:CellSpec(全量单一数据源)
```python
@dataclass(frozen=True)
class CellSpec:
    domain: str                       # "gravity"
    shift: str                        # "gamma_2_2"
    params_type: type                 # GravityGamma22Params(字段带 role 元数据)
    law: Callable[[Mapping, Any], float]   # 统一签名:law(inputs, params) → 标量
    sampler: Callable[[int], Any]
    validator: Callable[[Any], bool]
    output: str                       # "F"(评分通道名,per-cell 不是 per-domain)
    broken_symmetry: str              # "SCALE"
    grid: GridSpec                    # 采样范围 + OOD 策略(per-cell)
```
**为什么这样设**:
- **law 是核心**:`law(inputs, params)` 一个纯函数。grid GT 和 oracle **都调它**——公式 3→1,永不 drift(这是最大收益)。
  - grid GT:`law(inputs, sim.params)`(in-domain)/ `law(inputs, cf_params)`(counterfactual)
  - oracle:同一个 law,(c) 上 cf 扰动的参数通过 canonical 名自动并入
- **output 在 cell 级不在 domain 级**:我发现一个潜伏的不一致——optics 同域里 baseline/γ-9-2 评角度、γ-9-1/δ-9-1 评透射率 T,现在靠 domain 级 `_DOMAIN_OBSERVABLES` 糊着。CellSpec.output 顺手修正。
- **grid 保持 per-cell**:采样不是机械重复(μ-schedule 避开各向同性奇点、geomspace 居中 bump、掠射悬崖范围)——这些是真·物理设计,**不统一**。只统一 GT 的 law 求值。

### 结构3:CELL_REGISTRY(注册表,替 7 张并行表)
```python
CELL_REGISTRY: dict[tuple[str,str], CellSpec] = {}
def register_cell(spec): CELL_REGISTRY[(spec.domain, spec.shift)] = spec

# 每个系统从 registry 派生,不再各存一张表:
#   load(domain,shift)            → CELL_REGISTRY[key].sampler/law/grid
#   make_oracle(key)              → 通用 adapter 读 spec.law
#   _LAW_PARAM_FIELDS[T]          → {f.name for f if role==law}      (派生,不再硬编码)
#   _PREDICTOR_NAME_MAP[T]        → {f.name: canonical}              (派生)
#   declared_params(key)          → law 字段 → canonical 名          (删 48 个函数)
```
**为什么这样设**:Gymnasium 的核心教训——**一份注册,处处派生**。加一个 cell = 写一个 CellSpec + register 一次,7 处自动跟上。再不用改 7 个文件。

### 结构4:大世界的预留接口(Scene = CellSpec 组合)
```python
def composed_law(inputs, bundle):                       # 多定律 = 多个 law 求和
    return sum(c.law(inputs, bundle[c.id]) for c in components) \
         + sum(k.law(inputs, bundle) for k in couplings)
```
**为什么现在就留**:因为 `law(inputs, params)` 是纯函数,组合是免费的(求和)。共因世界(候选C)的 SharedLatent→各域 params,正好喂进这个组合点。**单 law = 1 个 component 的特例**——不为大世界改任何单 cell 逻辑,只是允许 ScenarioInstance 持有多个 component。

---

## 四、什么绝对不动(冻结区)

- **eval/numeric.py 评分核心**:entry 形状、(a)(b) 2-tuple/(c) 3-tuple、canonical_inputs、(c) 合并序、`_rel_floor`、`_alias_inputs` 桥接——全冻结。CellSpec 只负责**产出**这些精确形状,不改评分逻辑。
- **你们刚修对的 5 个 bug**:全部变成 metadata 编码的属性(role=axis、leak#2、cf-override-wins…),迁移时当数据保住,golden-parity 测试守门。

---

## 五、为什么这个架构"极大方便理解和扩展"

| 你想做的事 | 现在 | 重构后 |
|-----------|------|--------|
| 看懂一个 cell | 翻 7 个文件拼起来 | 读它的 CellSpec 一处 |
| 改一个破缺公式 | 改 3 处保持同步 | 改 law 一处 |
| 加一个新 cell | 改 5-7 个文件 | 写 1 个 CellSpec + register |
| 加一个新 domain | 同步 7 张表 | 注册即可 |
| 搭大世界 | 无从下手 | 组合现成 CellSpec |
| 改错 canonical 名 | 静默 bug,(c) 掉分 | golden-parity 测试拦截 |

---

## 六、待你确认的设计决策

1. **元数据放字段上(Pydantic 式)还是集中清单(轻量但数据与类分离)?** 我倾向字段上(真单一数据源,且和已有 ShiftImpl 惯例一致),但要动 48 个 shift 文件。
2. **role 的命名和粒度**:law / mass / ic / axis 四类够不够?(我核实过现有数据,这四类覆盖所有字段)
3. **迁移节奏**:先做 1 个垂直切片(gravity/γ-2-2 完整走通 CellSpec)给你看效果,再逐 domain 铺开?

确认后我们逐结构敲定,再开始 P0。

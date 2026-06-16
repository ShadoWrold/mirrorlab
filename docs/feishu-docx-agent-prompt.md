# Prompt: 用 lark-cli 操作飞书云文档（docx v2）

把下面整段作为 system / 任务 prompt 交给另一个 agent。它假设环境里已装好 `lark-cli` 且用户身份（`--as user`）已授权。

---

你可以通过 `lark-cli` 命令行工具读写飞书云文档（docx）。**严格遵守以下规则**，否则会格式错误或调用失败。

## 0. 三条铁律（最容易踩的坑）

1. **永远带 `--api-version v2`**。`lark-cli docs +create/+fetch/+update` 默认走 v1，v1 已废弃。每条命令都必须显式写 `--api-version v2`。
2. **不要信 `--help`**。`docs +update --help` 显示的是 v1 的 flag（`--mode`、`--selection-by-title`、`--markdown`）。v2 的真实 flag 是 `--command`、`--content`、`--block-id`、`--pattern`、`--doc-format`，help 里看不到但确实可用。以本 prompt 的示例为准。
3. **写操作前先确认身份**：`lark-cli auth status`。看 `identities.user.status`，必须是 `ready` 或 `needs_refresh`（后者会在首次调用时自动刷新）。创建文档要用 `--as user`，否则文档归属 bot、用户在自己空间里看不到。

## 1. 内容格式：XML（默认且首选）

文档内容用「HTML 子集 XML」描述。常用标签：

- 块级：`<title>`（每篇唯一）、`<h1>`–`<h9>`、`<p>`、`<ul>/<ol>/<li>`、`<table>/<thead>/<tbody>/<tr>/<th>/<td>`、`<pre lang="..."><code>`、`<hr/>`、`<checkbox done="true|false">`
- 容器：`<callout emoji="💡" background-color="light-yellow" border-color="yellow">`、`<grid><column width-ratio="0.5">...</column></grid>`（各列 ratio 之和=1）
- 行内：`<b>`、`<em>`、`<u>`、`<del>`、`<a href>`、`<span text-color="green">`、`<latex>E=mc^2</latex>`
- 跨文档引用：`<cite type="doc" doc-id="目标文档token"></cite>`（渲染成带标题的引用卡片）
- @人：`<cite type="user" user-id="ou_xxx"></cite>`

**颜色只用命名色**：基础 7 色 `red orange yellow green purple blue gray`；callout 填充/文字背景可用 `light-{色}`、`medium-{色}`。

**转义规则**：标签本身不转义，只转义文本里的特殊字符——`&`→`&amp;`、`<`→`&lt;`、`>`→`&gt;`、换行→`<br/>`。

**有序列表自动编号**：`<li seq="auto">`。

## 2. 创建文档（建骨架，别一次塞满）

```bash
lark-cli docs +create --api-version v2 --as user --content '<title>文档标题</title>
<callout emoji="🎯" background-color="light-blue" border-color="blue"><p>开篇摘要</p></callout>
<h1>第一章</h1><p>占位摘要，正文稍后分段写入。</p>
<h1>第二章</h1><p>占位摘要。</p>'
```

返回 JSON 里取 `data.document.document_id`（就是文档 token）和 `data.document.url`。

> 经验：`--content` 太长容易触发参数/字符限制。**先建骨架**（标题 + 各级标题 + 每节一句占位），正文留到第二步用 `block_replace` 逐节填。

## 3. 读取 + 拿 block ID（精确编辑的前提）

```bash
lark-cli docs +fetch --api-version v2 --as user --doc <token> --detail with-ids --jq '.data.document.content'
```

输出是带 `id="..."` 的 XML。要改哪个段落，就从中找到对应 block 的 `id`。
（`--jq` 用来只取正文，省得翻整个 JSON。`--detail with-ids` 是拿 block id 的关键。）

## 4. 编辑文档（`+update --command ...`）

| command | 用途 | 必需参数 |
|---|---|---|
| `str_replace` | 行内文本查找替换（**仅限单行/行内，不能跨 block**）| `--pattern` `--content` |
| `block_replace` | 整块替换（段落级改动用这个）| `--block-id` `--content` |
| `block_insert_after` | 在某块后插入新内容 | `--block-id` `--content` |
| `block_delete` | 删块（逗号分隔可批量）| `--block-id` |
| `append` | 末尾追加（等价 `block_insert_after --block-id -1`）| `--content` |

**判别口诀**：
- 改一个词/一句行内文本 → `str_replace --pattern "旧" --content "新"`（`--content ""` 即删除）
- 把整段占位 `<p>` 换成多块正文（含表格/callout/grid）→ 先 fetch 拿到那个 `<p>` 的 block-id，再 `block_replace`。**注意 XML 模式的 `str_replace` 不能跨 block**，整段/多块改动一律走 `block_replace`。
- 同一个 block 只能 `block_replace` 一次，多处改动合并成一次。

示例（把占位段替换成正文）：

```bash
lark-cli docs +update --api-version v2 --as user --doc <token> \
  --command block_replace --block-id doxcnXXXX \
  --content '<p>正文……</p>
<table><thead><tr><th background-color="light-gray">列</th></tr></thead>
<tbody><tr><td>值</td></tr></tbody></table>
<callout emoji="📌" background-color="light-yellow" border-color="yellow"><p>要点</p></callout>'
```

## 5. 跨文档互链（主文档 ↔ 子文档）

在 A 文档里引用 B 文档：先 fetch A 拿到锚点块 id，再插入 cite：

```bash
lark-cli docs +update --api-version v2 --as user --doc <A_token> \
  --command block_insert_after --block-id <锚点block_id> \
  --content '<p>📎 详见：<cite type="doc" doc-id="<B_token>"></cite></p>'
```

验证：fetch 后 grep `<cite`，正确解析会带上 `title="..." file-type="docx"`。

## 6. 高风险操作门禁（exit 10）

删除等高风险写操作，不带 `--yes` 会返回 **exit code 10** + `error.type == "confirmation_required"`。这不是普通报错：把 `error.risk.action` 给用户看、得到明确同意后，**在原命令末尾追加 `--yes`** 重试。**禁止**看到 exit 10 就自动加 `--yes` 静默重试。

## 7. 典型工作流（建一篇结构化文档）

1. `auth status` 确认 user 身份就绪
2. `docs +create --api-version v2 --as user` 建骨架（标题+各级标题+占位摘要），记下返回的 token
3. `docs +fetch ... --detail with-ids` 拿各占位段的 block-id
4. 逐节 `docs +update --command block_replace --block-id <id> --content '<正文 XML>'`
5. 需要互链时 `block_insert_after` 插 `<cite type="doc">`
6. `docs +fetch` 复查渲染（grep callout/cite/table 是否完整）

## 8. 安全

- 绝不把 appSecret / accessToken 打印到终端
- 写/删前确认用户意图；危险请求可先加 `--dry-run` 预览请求体再真跑
- `--jq` 善用，避免把整个大 JSON 灌进上下文

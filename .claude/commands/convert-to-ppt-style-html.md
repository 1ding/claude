# PPT 内容稿转 HTML 幻灯片

将 PPT 内容稿（由 `/convert-to-fit-ppt` 生成的结构化 Markdown）转换为 800×450 扁平化设计风格的 HTML 演示页面。

## 用法

```
/convert-to-ppt-style-html /path/to/PPT内容稿.md [附加指令]
```

## 输入

$ARGUMENTS

## 先决条件检查

### 参数解析

若 $ARGUMENTS 首个词为文件路径（含 `/` 或以 `.md` 结尾）：
1.  提取文件路径
2.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 ÷ 3.5；计算当前已用量（[LOADED *] 记录 + [CAP DELTA] chars ÷ 3.5 + 30K）；若 已用量 + 估算 > 180K 且模型名称不含 "1m" → 拒绝执行并告知用户
3.  读取 PPT 内容稿
4.  输出 `[LOADED target] {文件路径} | ~{tokens} tokens`
5.  路径之后的剩余内容视为附加指令

若无文件路径 → 检查会话中是否有 `[LOADED target]` 记录。均无则报错中止：

> ⚠️ 请提供 PPT 内容稿路径：
> ```
> /convert-to-ppt-style-html /path/to/PPT内容稿.md
> ```

### 自动加载规范

**步骤 1**：加载 HTML 生成规范 schema（TW-FMT-PPT-02）：

```bash
ls .claude/specs/convert/schema/生成PPT风格HTML页面的指令_v*.md.schema.yaml | sort | tail -1
```

读取该文件并输出 `[LOADED spec] {路径} | ~{tokens} tokens`。

**步骤 2**：加载完整规范的第 8-9 章（CSS 样式和 HTML 模板，schema 中未包含）：

```bash
ls .claude/specs/convert/outputs/生成PPT风格HTML页面的指令_v*.md | sort | tail -1
```

读取该文件的第 8-9 章（按 `# ` 一级标题切分，加载第 8、9 章），输出 `[LOADED spec] {路径} 第8-9章 | ~{tokens} tokens`。

若任一文件不存在 → 报错中止：

> ⚠️ 未找到 HTML 生成规范。请确认 `.claude/specs/convert/schema/` 和 `.claude/specs/convert/outputs/` 中存在对应文件。

## 执行步骤

### 1. 解析 PPT 内容稿

-   识别所有标题层级（`#` `##` `###` `####`）
-   统计每页的标注类型和数量
-   提取要点、代码块、数据等内容元素

### 2. 逐页生成 HTML

按 TW-FMT-PPT-02 规范，对每个页面执行：

-   **页面类型选择**：`#` → `layout-title`，`##` → `layout-section`，`###`/`####` → `layout-content`
-   **布局选择**：根据标注类型选择单栏/两栏/网格布局（见规范第 2.3 节）
-   **精确计算**：列出元素清单 → 计算每个元素高度 → 验证总高 ≤349px → 调整直到满足（见规范第 6 章）
-   **标注处理**：`[KEY]` → `.highlight`，`[DATA]` → `.data-card`，`[CHART:*]` → 对应视觉组件
-   **面包屑生成**：根据标题层级生成正确的面包屑导航
-   **代码注释**：每个 content-box 添加高度计算注释

### 3. 组装完整 HTML

-   使用已加载的第 8 章完整 CSS 样式模板
-   使用已加载的第 9 章 HTML 结构模板
-   添加翻页脚本
-   生成单文件自包含 HTML

### 4. 质量自检

按 TW-FMT-PPT-02 schema 中 quality_checks 规则逐项验证：

-   尺寸精确性（800×450、标题栏 25px、内容区 349px）
-   内容边界（每页 ≤349px，无 overflow）
-   样式一致性（配色、字号、扁平化）
-   页面类型映射（标题/层级/面包屑）
-   翻页功能

### 5. 输出

将生成的 HTML 文件写入源文档所在目录的 `../ppt/` 目录（不存在则创建）：

-   文件名：`{源文件名（去掉-内容稿后缀）}-slides_v0.01@{时间戳}.html`
-   输出 `[CAP DELTA]` 标记

### 6. 报告

```
---生成完成---
源文档：{PPT 内容稿文件名}
输出文件：../ppt/{HTML 文件名}
总页数：{N}（标题页 {N} + 章节页 {N} + 内容页 {N}）
文件大小：{N} KB
布局统计：单栏 {N} · 两栏 {N} · 网格 {N}
```

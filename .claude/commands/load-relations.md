# 加载关联文档（AI 判断关系类型）

读取关联文档，由 AI 根据文件内容判断其与目标文档的关系类型并打上对应标记。适合关系类型不明确、或需要批量加载混合类型文档的情况。

## 用法

```
/load-relations /path/to/related-file.md       # 单文件，AI 判断关系类型
/load-relations /path/to/related-file.md 4     # 只加载第4章
/load-relations /path/to/related-file.md 1-2   # 只加载第1、2章
/load-relations /path/to/project/              # 项目目录，从 CLAUDE.md 批量解析
```

## 执行步骤

### 文件模式（参数为文件路径）

1.   读取指定文件
     - 单文件加载限制：100K tokens
     - 超过限制时：显示 ⚠️ 告警但继续完整加载
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算和超量检查仅针对保留内容
2.   结合会话中已有的 `[LOADED target]`（若存在），判断该文件与目标文档的关系类型：
-   **upstream**：目标文档的依据、来源或上级文档
-   **downstream**：目标文档的衍生、实现或下游文档
-   **parallel**：与目标文档同层级、相互参照的文档
-   **context**：背景信息、约束条件、领域知识
3.   输出加载确认（带判断说明）：
   ```
   [LOADED {判断类型}] {文件路径} | ~{字节数÷3.5取整} tokens  ← /load-relations 判断为 {类型}
   [LOADED {判断类型}] {文件路径} [章节 N] | ~{tokens数量} tokens  ← /load-relations 判断为 {类型}
   ```
   - 如果超过 100K tokens：
   ```
   ⚠️ [LOADED {判断类型}] {文件路径} | ~{tokens数量} tokens (超过100K限制，已完整加载) ← /load-relations 判断为 {类型}
   ```

### 目录模式（参数为目录路径）

1.   检查该目录下是否有 `CLAUDE.md`：
     -   **有 CLAUDE.md**：读取关联关系表，按 upstream / downstream / parallel / context 分类加载；文件定位优先 outputs/，其次 drafts/
     -   **无 CLAUDE.md**：列出该目录下所有 `.md` 文件（同名前缀取最新版本），对每个文件执行文件模式中的 AI 判断步骤
2.   每加载一个文件输出对应 `[LOADED {类型}]` 确认

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及当前已用量汇总。

> 提示：关联文档体积通常较大，加载前建议先执行 /cap-status 确认剩余容量。

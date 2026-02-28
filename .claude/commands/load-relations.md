# 加载关联文档（AI 判断关系类型）

读取关联文档，由 AI 根据文件内容判断其与目标文档的关系类型并打上对应标记。适合关系类型不明确、或需要批量加载混合类型文档的情况。

## 用法

```
/load-relations /path/to/related-file.md       # 单文件，AI 判断关系类型
/load-relations /path/to/project/              # 项目目录，从 CLAUDE.md 批量解析
```

## 执行步骤

### 文件模式（参数为文件路径）

1.   读取指定文件
2.   结合会话中已有的 `[LOADED target]`（若存在），判断该文件与目标文档的关系类型：
-   **upstream**：目标文档的依据、来源或上级文档
-   **downstream**：目标文档的衍生、实现或下游文档
-   **parallel**：与目标文档同层级、相互参照的文档
-   **context**：背景信息、约束条件、领域知识
3.   输出加载确认（带判断说明）：
   ```
   [LOADED {判断类型}] {文件路径} | ~{字节数÷3.5取整} tokens  ← /load-relations 判断为 {类型}
   ```

### 目录模式（参数为目录路径）

1.   从会话历史找到最近一条 `[LOADED target]` 记录，获取目标文档
2.   推断项目路径（从文件路径向上找到含 `CLAUDE.md` 的目录）
3.   读取该项目的 `CLAUDE.md`，找到目标文档的全部关联列表
4.   按以下顺序加载，文件定位优先从 `outputs/`，其次 `drafts/`：
   ```
   [LOADED upstream]    {文件路径} | ~{tokens}
   [LOADED downstream]  {文件路径} | ~{tokens}
   [LOADED parallel]    {文件路径} | ~{tokens}
   [LOADED context]     {文件路径} | ~{tokens}
   ```

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载

> 提示：关联文档体积通常较大，加载前建议先执行 /cap-status 确认剩余容量。

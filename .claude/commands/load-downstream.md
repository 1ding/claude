# 加载下游关联文档

将下游文档读取到当前会话上下文。

## 用法

```
/load-downstream /path/to/downstream-file.md        # 直接指定文件
/load-downstream /path/to/downstream-file.md 4      # 只加载第4章
/load-downstream /path/to/downstream-file.md 1-2    # 只加载第1、2章
/load-downstream /path/to/project/                  # 批量加载（需先 /load-target）
```

## 执行步骤

### 文件模式（参数以 .md 结尾）

1.   读取指定文件
     - 单文件加载限制：100K tokens
     - 超过限制时：显示 ⚠️ 告警但继续完整加载
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算和超量检查仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED downstream] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED downstream] {文件路径} [章节 N] | ~{tokens数量} tokens    ← 有章节参数时
   ```
   - 如果超过 100K tokens：
   ```
   ⚠️ [LOADED downstream] {文件路径} | ~{tokens数量} tokens (超过100K限制，已完整加载)
   ```

### 目录模式（参数为目录路径）

1.   从会话历史找到最近一条 `[LOADED target]` 记录，获取目标文档文件名
2.   读取该目录下的 `CLAUDE.md`，在关联关系表中找到目标文档的下游文档列表
3.   按优先级（outputs/ 优先，其次 drafts/）逐一定位并读取各下游文档
4.   每加载一个文件输出一条 `[LOADED downstream]` 确认

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载

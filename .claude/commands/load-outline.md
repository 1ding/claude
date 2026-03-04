# 加载大纲文件

将指定大纲文件读取到当前会话上下文。

## 用法

```
/load-outline /path/to/outline-file.md
/load-outline /path/to/outline-file.md 4       # 只加载第4章
/load-outline /path/to/outline-file.md 1-2     # 只加载第1、2章
```

参数为具体文件路径（必填，不支持目录）。章节参数可选，置于路径之后。

## 执行步骤

1.   读取 $ARGUMENTS 指定的文件
     - 单文件加载限制：100K tokens
     - 超过限制时：显示 ⚠️ 告警但继续完整加载
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算和超量检查仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED outline] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED outline] {文件路径} [章节 N] | ~{tokens数量} tokens    ← 有章节参数时
   ```
   - 如果超过 100K tokens：
   ```
   ⚠️ [LOADED outline] {文件路径} | ~{tokens数量} tokens (超过100K限制，已完整加载)
   ```
3.   扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计
4.   容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载；可输入 `/model <sonnet-1m>` 切换大上下文模型（无需重开会话）

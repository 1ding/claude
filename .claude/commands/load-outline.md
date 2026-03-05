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
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED outline] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED outline] {文件路径} [章节 N] | ~{tokens数量} tokens    ← 有章节参数时
   ```
3.   扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及当前已用量汇总。

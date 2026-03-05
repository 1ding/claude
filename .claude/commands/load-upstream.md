# 加载上游关联文档

将上游文档读取到当前会话上下文。

## 用法

```
/load-upstream /path/to/upstream-file.md       # 单文件
/load-upstream /path/to/upstream-file.md 4     # 只加载第4章
/load-upstream /path/to/upstream-file.md 1-2   # 只加载第1、2章
/load-upstream /path/a.md /path/b.md           # 多文件
/load-upstream /path/to/dir/                   # 目录（加载所有 .md）
```

## 执行步骤

### 单文件模式

1.   读取指定文件
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED upstream] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED upstream] {文件路径} [章节 N] | ~{tokens数量} tokens      ← 有章节参数时
   ```

### 多文件模式（`路径1 路径2 ...`）

1.   依次识别参数中的多个路径（不支持章节参数）
2.   对每个文件逐一执行单文件模式步骤

### 目录模式（参数为目录路径）

1.   列出该目录下所有 `.md` 文件（按文件名排序，同名前缀取最新版本）
2.   逐一读取，每个文件输出一条 `[LOADED upstream]` 确认

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及当前已用量汇总。

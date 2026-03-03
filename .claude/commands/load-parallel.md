# 加载并行关联文档

将并行文档读取到当前会话上下文。

## 用法

```
/load-parallel /path/to/file.md                          # 单文件
/load-parallel /path/to/file.md 4                        # 只加载第4章
/load-parallel /path/to/file.md 1-2                      # 只加载第1、2章
/load-parallel /path/a.md /path/b.md /path/c.md          # 多文件（对等模式，无需 load-target）
/load-parallel /path/to/project/                         # 目录批量加载（需先 /load-target）
```

## 执行步骤

### 单文件模式（参数为单个 .md 路径，可含章节参数）

1.   读取指定文件
     - 单文件加载限制：100K tokens
     - 超过限制时：显示 ⚠️ 告警但继续完整加载
     - **章节过滤**（有章节参数时）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算和超量检查仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED parallel] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED parallel] {文件路径} [章节 N] | ~{tokens数量} tokens      ← 有章节参数时
   ```
   - 如果超过 100K tokens：
   ```
   ⚠️ [LOADED parallel] {文件路径} | ~{tokens数量} tokens (超过100K限制，已完整加载)
   ```

### 多文件模式（参数为多个 .md 路径）

1.   按参数顺序逐一读取各文件
2.   每加载一个文件输出一条 `[LOADED parallel]` 确认
3.   与 `load-target` 无关，不检查也不依赖会话历史中的 target 记录

### 目录模式（参数为目录路径）

1.   列出该目录下所有 `.md` 文件
2.   逐一读取全部文件
3.   每加载一个文件输出一条 `[LOADED parallel]` 确认
4.   与 `load-target` 无关，不检查也不依赖会话历史中的 target 记录

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载

# 加载背景约束文档

将领域背景约束文件读取到当前会话上下文。

## 用法

```
/load-context /path/to/context-file.md         # 直接指定文件
/load-context /path/to/context-file.md 4       # 只加载第4章
/load-context /path/to/context-file.md 1-2     # 只加载第1、2章
/load-context /path/to/context-dir/            # 加载目录下全部文件
```

## 执行步骤

### 文件模式（参数以 .md 或 .yaml 结尾）

1.   读取指定文件
     - 单文件加载限制：100K tokens
     - 超过限制时：显示 ⚠️ 告警但继续完整加载
     - **章节过滤**（有章节参数时，仅 .md 文件支持）：按 `# ` 一级标题切分，序号从1开始，只保留指定章节；若无一级标题或序号越界，加载全文并告警。token 估算和超量检查仅针对保留内容
2.   输出加载确认：
   ```
   [LOADED context] {文件路径} | ~{字节数÷3.5取整} tokens
   [LOADED context] {文件路径} [章节 N] | ~{tokens数量} tokens    ← 有章节参数时
   ```
   - 如果超过 100K tokens：
   ```
   ⚠️ [LOADED context] {文件路径} | ~{tokens数量} tokens (超过100K限制，已完整加载)
   ```

### 目录模式（参数为目录路径）

1.   扫描目录，加载全部 `.md` 文件（按文件名排序，同前缀取最新版本）
2.   逐一读取，每个文件输出一条 `[LOADED context]` 确认

### 加载后

扫描本次会话全部 `[LOADED *]` 记录，列出已加载文件清单及估算合计。

容量检查（以 200K 为基准）：
-   合计 > 120K tokens → ⚠️ 已超过 60%，谨慎继续加载
-   合计 > 160K tokens → 🔴 已超过 80%，强烈建议停止加载

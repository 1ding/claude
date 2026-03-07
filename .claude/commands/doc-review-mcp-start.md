# 单模型交互评审 — 发起

调用 MCP multi-reviewer 的 `start_review_session` 工具，使用单个 AI 模型对文档发起评审。

## 输入

$ARGUMENTS

格式示例：
```
/doc-review-mcp gemini-2.5-pro /path/to/文档.md
/doc-review-mcp gpt-5.4-pro /path/to/文档.md
/doc-review-mcp qwen3.5-plus-02-15 /path/to/文档.md
```

## 先决条件检查

1.  提取模型名称（第一个参数）和文件路径（第二个参数）
2.  **模型检查**：当前模型名称不含 "1m" → 停止执行，提示：
    > 请先切换模型：`/model sonnet-1m` 或 `/model opus[1m]`，切换后重新运行。
3.  **容量预检**：用 `ls -l` 获取文件大小，估算 tokens = 字节数 ÷ 3.5；已用量 + 估算 > 900K → 应用四分支决策树，停止
4.  **可用模型校验**：模型名称必须是 `gpt-5.4-pro`、`gemini-2.5-pro`、`qwen3.5-plus-02-15` 之一

若参数不足，输出提示并中止：

> 用法：`/doc-review-mcp <模型> /path/to/文档.md`
>
> 可用模型：`gpt-5.4-pro`、`gemini-2.5-pro`、`qwen3.5-plus-02-15`

## 执行步骤

### 1. 发起评审

调用 MCP Server `multi-reviewer` 的 `start_review_session` 工具：

```json
{
  "file_path": "<绝对路径>",
  "model": "<模型名称>",
  "review_language": "zh"
}
```

### 2. 记录会话 ID

从返回结果中提取 `session_id`。

### 3. 将初始评审意见写入文件

**输出路径**：被评审文档所在目录的 `../review/` 下（目录不存在时自动创建），文件名格式：
```
{原文件名（不含扩展名）}_review@{YYYYMMDDHHmm}.md
```

**文件结构**：

```
# 评审报告：{原文档标题}

+ 评审时间：{时间}
+ 评审模型：{模型名称}
+ 被评审文件：{文件路径}
+ 会话 ID：{session_id}
+ 评审状态：进行中

# 1 初始评审意见

{模型返回的完整评审内容，保留原文}
```

### 4. 输出结果

```
评审报告已生成：{报告文件路径}
会话 ID：{session_id}

后续操作：
- /doc-review-mcp-discuss {session_id} <你的反馈>  — 与评审模型讨论
- /doc-review-mcp-end {session_id}                  — 结束评审并输出最终报告
```

## 不执行

-   **不修改**被评审文档（仅评审，不修订）
-   **不加载**规范文档（评审由外部模型基于通用标准进行）

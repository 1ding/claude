# 单模型交互评审 — 讨论

调用 MCP multi-reviewer 的 `discuss_review` 工具，向评审模型发送反馈，模型根据反馈修订评审意见。

## 输入

$ARGUMENTS

格式示例：
```
/doc-review-mcp-discuss a1b2c3d4 第3点关于逻辑一致性的意见不准确，文档第2章已解释了设计决策
/doc-review-mcp-discuss a1b2c3d4 改进建议中的第3条不适用于我们的场景，请撤回
/doc-review-mcp-discuss a1b2c3d4 请深入分析第4章的结构问题
```

## 参数解析

1.  提取会话 ID（第一个参数，8位字符串）
2.  提取反馈内容（剩余所有文字）

若参数不足，输出提示并中止：

> 用法：`/doc-review-mcp-discuss <session_id> <反馈内容>`

## 执行步骤

### 1. 发送反馈

调用 MCP Server `multi-reviewer` 的 `discuss_review` 工具：

```json
{
  "session_id": "<会话ID>",
  "message": "<用户反馈内容>"
}
```

### 2. 查找评审报告文件

在对话历史中查找该 session_id 对应的评审报告文件路径（由 `/doc-review-mcp-start` 创建）。
若找不到，用 Grep 在项目的 `review/` 目录中搜索包含该 session_id 的 `_review@*.md` 文件。

### 3. 追加讨论内容到报告文件

将讨论内容**追加**到评审报告文件末尾：

```
# {N} 第 {轮次} 轮讨论

## {N}.1 用户反馈

{用户反馈内容}

## {N}.2 模型修订意见

{模型修订后的评审内容，保留原文}
```

轮次编号从 1 开始，依据文件中已有的讨论章节数递增。
章节编号 N 接续文件中已有的顶级章节号。

### 4. 输出结果

在对话中展示模型的修订意见，并提示：

```
讨论记录已追加到：{报告文件路径}

继续操作：
- /doc-review-mcp-discuss {session_id} <继续反馈>  — 继续讨论
- /doc-review-mcp-end {session_id}                  — 结束评审
```

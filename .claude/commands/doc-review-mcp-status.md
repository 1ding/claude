# 单模型交互评审 — 状态查询

查看当前交互评审的状态信息。

## 输入

$ARGUMENTS

格式示例：
```
/doc-review-mcp-status
```

## 执行步骤

### 1. 查询可用模型

调用 MCP Server `multi-reviewer` 的 `list_models` 工具，获取可用模型清单。

### 2. 查找活跃会话

在对话历史中查找所有由 `/doc-review-mcp-start` 创建的会话，提取：
-   会话 ID
-   使用的模型
-   被评审文件路径
-   评审状态（进行中 / 已完成）
-   已进行的讨论轮次

若对话中无活跃会话，显示"无活跃会话"。

### 3. 输出状态

```
# MCP 交互评审状态

## 可用模型

{list_models 返回的模型清单}

## 活跃会话

| 会话 ID    | 模型         | 被评审文件     | 状态   | 讨论轮次 |
| ---------- | ------------ | -------------- | ------ | -------- |
| {id}       | {model}      | {file}         | {状态} | {N}      |

## 可用操作

- /doc-review-mcp-start <模型> <文件路径>        — 发起新评审
- /doc-review-mcp-discuss <session_id> <反馈>     — 继续讨论
- /doc-review-mcp-end <session_id>                — 结束评审
```

# 多模型文档评审系统 - 完整手册

通过 OpenRouter 统一接入 GPT-4o、Grok、Gemini 等模型，对文档进行并行评审，输出聚合对比报告。

---

# 1 系统概述

## 1.1 架构图

```graph
┌─────────────────────────────────────────────────────────┐
│                  Claude Code (MCP Client)               │
│                                                         │
│  /doc-review-multi 文档路径  →  调用 MCP Tool           │
└────────────────────────┬────────────────────────────────┘
                         │ stdio JSON-RPC
┌────────────────────────▼────────────────────────────────┐
│          MCP Server: multi-reviewer (server.py)         │
│                                                         │
│   tool: review_document(file_path, focus, models)       │
│                         │                               │
│              并行 asyncio.gather                        │
│         ┌───────┬───────┴───────┐                       │
│         ▼       ▼               ▼                       │
│     GPT-4o   Grok-3        Gemini-2.0                   │
│         └───────┴───────┬───────┘                       │
│                         ▼                               │
│                   聚合评审报告                          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼ 统一 HTTPS API
┌─────────────────────────────────────────────────────────┐
│              OpenRouter (openrouter.ai)                 │
│          单一 API Key，OpenAI 兼容接口                  │
│   openai/gpt-4o  │  x-ai/grok-3  │  google/gemini-2.0   │
└─────────────────────────────────────────────────────────┘
```

## 1.2 核心优势

-   **单一 Key**：只需一个 OpenRouter API Key，无需分别申请 OpenAI / xAI / Google Key
-   **并行评审**：三个模型同时调用，总耗时约等于最慢单个模型的时间
-   **可扩展**：新增模型只需在 `server.py` 的 `AVAILABLE_MODELS` 中加一行
-   **与现有工作流无缝衔接**：作为 `/doc-review` 的多模型增强版，结果可直接送入 `/doc-revise`

---

# 2 前置条件

## 2.1 注册 OpenRouter 账号

1.   访问 `https://openrouter.ai`，注册账号
2.   进入 `Keys` 页面，创建新的 API Key
3.   充值（支持信用卡、加密货币），建议先充 5-10 美元用于测试
4.   记录 API Key，格式为 `sk-or-v1-xxxxxxxx`

## 2.2 确认 Python 环境

```bash
python3 --version   # 需要 3.10 及以上
pip3 --version
```

---

# 3 安装步骤

## 3.1 安装 Python 依赖

```bash
cd /home/1ding/claude/.claude/mcp-servers/multi-reviewer
pip3 install -r requirements.txt
```

+   `mcp>=1.0.0`：Anthropic 官方 MCP Python SDK
+   `openai>=1.30.0`：OpenAI 兼容客户端（OpenRouter 使用相同接口）

## 3.2 配置 API Key

使用 `claude mcp add` 命令注册（Key 写入 `~/.claude.json`，用户级，对所有项目生效）：

```bash
claude mcp add multi-reviewer \
  -e OPENROUTER_API_KEY=sk-or-v1-你的真实Key \
  --scope user \
  -- python3 /home/1ding/claude/.claude/mcp-servers/multi-reviewer/server.py
```

**重要**：注册后**重启 Claude Code**使配置生效。

+   Key 存储在 `~/.claude.json`，不会出现在项目文件中，不会被 git 追踪
+   `settings.local.json` 不支持 `mcpServers` 字段，不要在那里配置

## 3.3 验证安装

重启 Claude Code 后，在对话中输入：

```
列出 multi-reviewer 可用的评审模型
```

Claude Code 会调用 MCP tool `list_models`，返回模型列表即表示安装成功。

---

# 4 使用方法

## 4.1 基本用法

```
/doc-review-multi /home/1ding/claude/projects/开行科技风险/drafts/银行信息科技风险监管评级提升协同作战计划_v0.01_R03@202603061100.md
```

+   使用默认模型：GPT-4o、Grok-3、Gemini-2.0
+   全文评审，无特定重点

## 4.2 指定评审重点

```
/doc-review-multi /path/to/文档.md --focus 重点检查监管要求覆盖度和举措可落地性
```

## 4.3 指定模型组合

```
/doc-review-multi /path/to/文档.md --models gpt-4o deepseek-v3
```

## 4.4 完整参数示例

```
/doc-review-multi /path/to/文档.md --focus 检查数据一致性 --models gpt-4o grok-3 gemini-2.0
```

---

# 5 可用模型参考

| 模型 Key        | OpenRouter 模型 ID                  | 特点                     |
| --------------- | ----------------------------------- | ------------------------ |
| `gpt-4o`        | `openai/gpt-4o`                     | 综合能力强，推理准确     |
| `gpt-4o-mini`   | `openai/gpt-4o-mini`                | 速度快，成本低           |
| `grok-3`        | `x-ai/grok-3`                       | 实时信息，批判性强       |
| `grok-3-mini`   | `x-ai/grok-3-mini`                  | Grok 轻量版              |
| `gemini-2.0`    | `google/gemini-2.0-flash-001`       | 长上下文，多模态         |
| `gemini-1.5-pro`| `google/gemini-1.5-pro`             | 超长上下文（100万 token）|
| `claude-sonnet` | `anthropic/claude-sonnet-4-5`       | 中文理解优秀             |
| `deepseek-v3`   | `deepseek/deepseek-chat-v3-0324`    | 中文能力强，成本极低     |

+   新增模型：在 `server.py` 的 `AVAILABLE_MODELS` 字典中添加一行即可

---

# 6 与现有工作流的衔接

```graph
                    文档评审工作流
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
   /doc-review                  /doc-review-multi
  （Claude 单模型）              （多模型并行）
  深度内部质量检查              多角度交叉验证
  结合规范文档评审              适合重要文档终审
          │                             │
          └──────────────┬──────────────┘
                         ▼
                    /doc-revise
                  （整合意见修订）
```

**推荐使用场景**：

-   常规修订后 → `/doc-review`（快速，基于规范）
-   重要文档定稿前 → `/doc-review-multi`（多角度，交叉验证）
-   发现系统性问题 → `/doc-revise` 修订后再次评审

---

# 7 故障排除

## 7.1 MCP Server 连接失败

**现象**：Claude Code 提示找不到 `multi-reviewer` 工具

**排查步骤**：
1.   确认已重启 Claude Code
2.   手动测试 server 能否启动：
    ```bash
    OPENROUTER_API_KEY=sk-or-v1-你的Key python3 /home/1ding/claude/.claude/mcp-servers/multi-reviewer/server.py
    ```
    正常启动后无输出，按 Ctrl+C 退出
3.   检查 `settings.local.json` 的 JSON 格式是否合法（可用 `python3 -m json.tool settings.local.json` 验证）

## 7.2 API Key 无效

**现象**：评审报告中出现 `[ERROR] API Key 无效或无权限访问该模型`

**解决**：
-   确认 `settings.local.json` 中 Key 拼写正确
-   在 OpenRouter 控制台确认账户有余额
-   确认该 Key 有权限访问目标模型

## 7.3 依赖缺失

**现象**：`ModuleNotFoundError: No module named 'mcp'`

**解决**：
```bash
pip3 install -r /home/1ding/claude/.claude/mcp-servers/multi-reviewer/requirements.txt
```

## 7.4 文档过长导致超时

**现象**：评审耗时过长或部分模型返回错误

**解决**：
-   先评审关键章节：`/doc-review-multi /path/to/文档.md --focus 只评审第3章内容`
-   使用速度更快的模型：`--models gpt-4o-mini grok-3-mini`

---

# 8 扩展与定制

## 8.1 新增模型

在 `server.py` 的 `AVAILABLE_MODELS` 中添加：

```python
AVAILABLE_MODELS = {
    # 现有模型...
    "llama-4":  "meta-llama/llama-4-maverick",   # 新增示例
}
```

## 8.2 定制评审 Prompt

修改 `server.py` 中的 `build_review_prompt()` 函数，可针对特定领域（如银行信息科技风险）定制评审维度：

```python
def build_review_prompt(content, focus, language):
    # 在此添加领域专业要求，例如：
    domain_context = "本文档涉及银行信息科技风险监管，请重点关注合规性和可操作性。"
    ...
```

## 8.3 调整并发数

默认三个模型并发，如需限制并发（避免 Rate Limit），可在 `handle_review_document()` 中改为顺序调用：

```python
# 顺序调用（替换 asyncio.gather）
model_results = {}
for key in model_keys:
    model_results[key] = await call_openrouter(key, prompt)
```

---

# 9 文件清单

```
.claude/mcp-servers/multi-reviewer/
├── server.py          ← MCP Server 主体（核心文件）
├── requirements.txt   ← Python 依赖
├── .env.example       ← API Key 配置模板
└── README.md          ← 本手册

.claude/commands/
└── doc-review-multi.md  ← /doc-review-multi slash 命令定义

.claude/settings.local.json
└── mcpServers.multi-reviewer  ← MCP Server 注册配置（需手动添加）
```

"""
多模型文档评审 MCP Server
通过 OpenRouter 统一调用 GPT-4o、Grok、Gemini 等模型对文档进行并行评审，
或以单模型交互对话方式进行评审。
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import openai
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# 并发控制：最多同时发 2 个请求，避免触发 Rate Limit
_SEMAPHORE = asyncio.Semaphore(2)
_RETRY_DELAYS = [2, 5, 15]  # 指数退避等待秒数（最多重试 3 次）

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# 可用模型映射表（OpenRouter 模型 ID）
AVAILABLE_MODELS = {
    "gpt-5.4-pro":          "openai/gpt-5.4-pro",
#   "grok-4":               "x-ai/grok-4",
    "gemini-2.5-pro":       "google/gemini-2.5-pro",
    "qwen3.5-plus-02-15":   "qwen/qwen3.5-plus-02-15",
#   "minimax-m2.5":         "minimax/minimax-m2.5",
#   "deepseek-v3.2":        "deepseek/deepseek-v3.2"
}

DEFAULT_MODELS = ["qwen3.5-plus-02-15", "gpt-5.4-pro", "gemini-2.5-pro"]

# ---------------------------------------------------------------------------
# 单模型交互评审会话存储（内存，进程级）
# ---------------------------------------------------------------------------

# session_id -> {"model": str, "messages": list[dict], "file_path": str}
_REVIEW_SESSIONS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("multi-reviewer")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="review_document",
            description=(
                "使用多个 AI 模型并行评审文档，聚合输出对比报告。"
                "支持全文评审或指定评审重点。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文档绝对路径（.md 文件）",
                    },
                    "review_focus": {
                        "type": "string",
                        "description": (
                            "评审重点说明（可选）。"
                            "例如：'重点检查逻辑一致性和数据准确性'"
                        ),
                    },
                    "models": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(AVAILABLE_MODELS.keys())},
                        "description": (
                            f"参与评审的模型列表（可选，默认：{DEFAULT_MODELS}）。"
                            f"可选值：{list(AVAILABLE_MODELS.keys())}"
                        ),
                    },
                    "review_language": {
                        "type": "string",
                        "enum": ["zh", "en"],
                        "description": "评审报告语言（可选，默认：zh 中文）",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_models",
            description="列出所有可用的评审模型及其 OpenRouter ID",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="start_review_session",
            description=(
                "使用单个 AI 模型对文档发起评审，返回会话 ID 和初始评审意见。"
                "后续可通过 discuss_review 工具就评审意见进行讨论，模型会根据反馈修订意见。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文档绝对路径（.md 文件）",
                    },
                    "model": {
                        "type": "string",
                        "enum": list(AVAILABLE_MODELS.keys()),
                        "description": f"参与评审的模型（可选值：{list(AVAILABLE_MODELS.keys())}）",
                    },
                    "review_focus": {
                        "type": "string",
                        "description": "评审重点说明（可选）",
                    },
                    "review_language": {
                        "type": "string",
                        "enum": ["zh", "en"],
                        "description": "评审报告语言（可选，默认：zh 中文）",
                    },
                },
                "required": ["file_path", "model"],
            },
        ),
        Tool(
            name="discuss_review",
            description=(
                "在已有评审会话中发送反馈，模型将基于对话历史修订其评审意见。"
                "需先通过 start_review_session 获取会话 ID。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "由 start_review_session 返回的会话 ID",
                    },
                    "message": {
                        "type": "string",
                        "description": "向评审模型发送的反馈或问题",
                    },
                },
                "required": ["session_id", "message"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "list_models":
        lines = ["# 可用评审模型\n"]
        for key, model_id in AVAILABLE_MODELS.items():
            lines.append(f"- `{key}` → `{model_id}`")
        return [TextContent(type="text", text="\n".join(lines))]

    if name == "review_document":
        return await handle_review_document(arguments)

    if name == "start_review_session":
        return await handle_start_review_session(arguments)

    if name == "discuss_review":
        return await handle_discuss_review(arguments)

    return [TextContent(type="text", text=f"未知工具：{name}")]


# ---------------------------------------------------------------------------
# 评审核心逻辑
# ---------------------------------------------------------------------------

async def handle_review_document(arguments: dict) -> list[TextContent]:
    file_path = arguments["file_path"]
    review_focus = arguments.get("review_focus", "")
    model_keys = arguments.get("models", DEFAULT_MODELS)
    language = arguments.get("review_language", "zh")

    # 读取文档
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return [TextContent(type="text", text=f"[ERROR] 文件不存在：{file_path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"[ERROR] 读取文件失败：{e}")]

    # 构建评审 prompt
    prompt = build_review_prompt(content, review_focus, language)

    # 并行调用各模型
    tasks = {key: call_openrouter(key, prompt) for key in model_keys}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    model_results = dict(zip(tasks.keys(), results))

    # 生成聚合报告
    report = build_report(file_path, review_focus, model_keys, model_results, language)
    return [TextContent(type="text", text=report)]


def build_review_prompt(content: str, focus: str, language: str) -> str:
    focus_line = f"\n评审重点：{focus}" if focus else ""
    lang_instruction = "请用中文输出评审意见。" if language == "zh" else "Please respond in English."

    return f"""{lang_instruction}

你是一位专业文档评审专家，请对以下文档进行全面、客观的评审。{focus_line}

## 评审维度

请逐项评审并给出具体意见：

1. **内容完整性** - 内容是否完整，是否有遗漏的关键信息
2. **逻辑一致性** - 内部逻辑是否自洽，是否存在矛盾
3. **专业准确性** - 专业表述是否准确，数据/引用是否可信
4. **结构清晰度** - 文档结构是否合理，层次是否清晰
5. **表述质量**   - 语言是否清晰、简洁、无歧义
6. **改进建议**   - 列出具体、可操作的改进建议（按优先级排序）

## 输出格式

按上述6个维度分别输出，每个维度包含：评分（1-5分）、主要发现、具体建议。
最后给出综合评价（1-3句话）。

---
## 待评审文档

{content}
"""


async def call_openrouter(model_key: str, prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "[ERROR] 未配置 OPENROUTER_API_KEY"

    model_id = AVAILABLE_MODELS.get(model_key)
    if not model_id:
        return f"[ERROR] 未知模型：{model_key}"

    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/claude-code",
            "X-Title": "Claude Code Multi-Reviewer",
        },
    )

    async with _SEMAPHORE:
        for attempt, delay in enumerate([0] + _RETRY_DELAYS):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                return response.choices[0].message.content or "[ERROR] 模型返回内容为空"
            except openai.AuthenticationError:
                return "[ERROR] API Key 无效或无权限访问该模型"
            except openai.RateLimitError:
                if attempt < len(_RETRY_DELAYS):
                    continue  # 等待后重试
                return f"[ERROR] 请求频率超限，已重试 {len(_RETRY_DELAYS)} 次，仍失败"
            except openai.APIError as e:
                return f"[ERROR] API 调用失败：{e}"
            except Exception as e:
                return f"[ERROR] 未知错误：{e}"

    return "[ERROR] 未知状态"  # 不可达，仅作保护


def build_report(
    file_path: str,
    focus: str,
    model_keys: list[str],
    model_results: dict,
    language: str,
) -> str:
    file_name = Path(file_path).name
    focus_line = f"评审重点：{focus}\n" if focus else ""
    model_list = "、".join(model_keys)

    sections = [
        f"# 多模型评审报告",
        f"",
        f"文档：`{file_name}`",
        f"{focus_line}参与模型：{model_list}",
        f"",
        "---",
    ]

    for key in model_keys:
        result = model_results.get(key, "[ERROR] 未获得评审结果")
        if isinstance(result, Exception):
            result = f"[ERROR] {result}"
        sections.append(f"\n## {key} 评审意见\n")
        sections.append(result)
        sections.append("\n---")

    sections.append("\n> 以上为各模型独立评审意见，请结合实际情况综合判断。")
    sections.append("> 后续可使用 `/doc-revise` 整合评审意见执行修订。")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# 单模型交互评审
# ---------------------------------------------------------------------------

async def handle_start_review_session(arguments: dict) -> list[TextContent]:
    file_path = arguments["file_path"]
    model_key = arguments["model"]
    review_focus = arguments.get("review_focus", "")
    language = arguments.get("review_language", "zh")

    # 读取文档
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return [TextContent(type="text", text=f"[ERROR] 文件不存在：{file_path}")]
    except Exception as e:
        return [TextContent(type="text", text=f"[ERROR] 读取文件失败：{e}")]

    # 构建初始 prompt（system + user）
    system_prompt = _build_session_system_prompt(language)
    user_prompt = _build_session_user_prompt(content, review_focus, language)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # 调用模型
    reply = await call_openrouter_messages(model_key, messages)
    if reply.startswith("[ERROR]"):
        return [TextContent(type="text", text=reply)]

    # 将助手回复追加到历史
    messages.append({"role": "assistant", "content": reply})

    # 存储会话
    session_id = str(uuid.uuid4())[:8]
    _REVIEW_SESSIONS[session_id] = {
        "model": model_key,
        "messages": messages,
        "file_path": file_path,
    }

    output = (
        f"# {model_key} 评审意见\n\n"
        f"文档：`{Path(file_path).name}`\n"
        f"会话 ID：`{session_id}`\n\n"
        f"---\n\n"
        f"{reply}\n\n"
        f"---\n\n"
        f"> 如需讨论或要求修订评审意见，请使用 discuss_review 工具，携带会话 ID `{session_id}`。"
    )
    return [TextContent(type="text", text=output)]


async def handle_discuss_review(arguments: dict) -> list[TextContent]:
    session_id = arguments["session_id"]
    user_message = arguments["message"]

    session = _REVIEW_SESSIONS.get(session_id)
    if not session:
        return [TextContent(
            type="text",
            text=f"[ERROR] 会话不存在或已过期：{session_id}。请通过 start_review_session 重新发起评审。"
        )]

    model_key = session["model"]
    messages = session["messages"]

    # 追加用户反馈
    messages.append({"role": "user", "content": user_message})

    # 调用模型
    reply = await call_openrouter_messages(model_key, messages)
    if reply.startswith("[ERROR]"):
        # 回滚用户消息，保持历史干净
        messages.pop()
        return [TextContent(type="text", text=reply)]

    # 追加助手回复
    messages.append({"role": "assistant", "content": reply})

    turns = (len(messages) - 2) // 2  # 排除 system + 初始user，每轮=user+assistant
    output = (
        f"# {model_key} 修订意见（第 {turns} 轮讨论）\n\n"
        f"会话 ID：`{session_id}`\n\n"
        f"---\n\n"
        f"{reply}\n\n"
        f"---\n\n"
        f"> 可继续使用 discuss_review 工具发送反馈。"
    )
    return [TextContent(type="text", text=output)]


def _build_session_system_prompt(language: str) -> str:
    if language == "zh":
        return (
            "你是一位专业文档评审专家。你将对用户提供的文档进行评审，"
            "并在后续对话中根据用户的反馈修订你的评审意见。"
            "每次修订时，请明确说明哪些意见被修改或撤回，并给出修改理由。"
            "请用中文输出。"
        )
    return (
        "You are a professional document reviewer. You will review the document provided by the user "
        "and revise your review based on user feedback in subsequent turns. "
        "When revising, clearly state which points were changed or withdrawn and why. "
        "Please respond in English."
    )


def _build_session_user_prompt(content: str, focus: str, language: str) -> str:
    focus_line = f"\n评审重点：{focus}" if focus else ""
    if language == "zh":
        return (
            f"请对以下文档进行全面评审。{focus_line}\n\n"
            "## 评审维度\n\n"
            "请逐项评审并给出具体意见：\n\n"
            "1. **内容完整性** - 内容是否完整，是否有遗漏的关键信息\n"
            "2. **逻辑一致性** - 内部逻辑是否自洽，是否存在矛盾\n"
            "3. **专业准确性** - 专业表述是否准确，数据/引用是否可信\n"
            "4. **结构清晰度** - 文档结构是否合理，层次是否清晰\n"
            "5. **表述质量**   - 语言是否清晰、简洁、无歧义\n"
            "6. **改进建议**   - 列出具体、可操作的改进建议（按优先级排序）\n\n"
            "按上述6个维度分别输出，每个维度包含：评分（1-5分）、主要发现、具体建议。"
            "最后给出综合评价（1-3句话）。\n\n"
            "---\n## 待评审文档\n\n"
            f"{content}"
        )
    return (
        f"Please review the following document comprehensively.{focus_line}\n\n"
        "## Review Dimensions\n\n"
        "1. **Completeness** - Is the content complete? Any missing key information?\n"
        "2. **Logical Consistency** - Is the internal logic coherent? Any contradictions?\n"
        "3. **Professional Accuracy** - Are professional terms accurate? Are data/references credible?\n"
        "4. **Structural Clarity** - Is the document structure reasonable and well-organized?\n"
        "5. **Expression Quality** - Is the language clear, concise, and unambiguous?\n"
        "6. **Improvement Suggestions** - List specific, actionable suggestions (by priority).\n\n"
        "For each dimension, provide: score (1-5), key findings, specific suggestions. "
        "End with an overall assessment (1-3 sentences).\n\n"
        "---\n## Document to Review\n\n"
        f"{content}"
    )


async def call_openrouter_messages(model_key: str, messages: list[dict]) -> str:
    """支持多轮对话历史的 OpenRouter 调用。"""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "[ERROR] 未配置 OPENROUTER_API_KEY"

    model_id = AVAILABLE_MODELS.get(model_key)
    if not model_id:
        return f"[ERROR] 未知模型：{model_key}"

    client = openai.AsyncOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/claude-code",
            "X-Title": "Claude Code Multi-Reviewer",
        },
    )

    async with _SEMAPHORE:
        for attempt, delay in enumerate([0] + _RETRY_DELAYS):
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.chat.completions.create(
                    model=model_id,
                    messages=messages,
                    temperature=0.3,
                )
                return response.choices[0].message.content or "[ERROR] 模型返回内容为空"
            except openai.AuthenticationError:
                return "[ERROR] API Key 无效或无权限访问该模型"
            except openai.RateLimitError:
                if attempt < len(_RETRY_DELAYS):
                    continue
                return f"[ERROR] 请求频率超限，已重试 {len(_RETRY_DELAYS)} 次，仍失败"
            except openai.APIError as e:
                return f"[ERROR] API 调用失败：{e}"
            except Exception as e:
                return f"[ERROR] 未知错误：{e}"

    return "[ERROR] 未知状态"


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())

"""LLM Orchestrator: uses OpenRouter API with tool-use loop."""

import json
from openai import OpenAI
from hr_matching.config import OPENROUTER_API_BASE, OPENROUTER_API_KEY, DEFAULT_MODEL, MAX_TOOL_ITERATIONS
from hr_matching.llm.tool_registry import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """你是一个专业的HR花名册分析助手。你的任务是帮助用户从Excel花名册中查找和匹配合适的人选。

你有以下工具可以使用：
1. parse_excel - 解析Excel文件，获取结构化数据
2. analyze_schema - 分析列名含义，建立语义映射
3. search_roster - 根据条件筛选候选人
4. score_matches - 对候选人评分排名

## 工作流程
当用户选择花名册文件并提出查询时，你应该：
1. 先调用 parse_excel 解析文件
2. 再调用 analyze_schema 理解列名含义
3. 根据用户需求，调用 search_roster 进行筛选
4. 如需排名，调用 score_matches 进行评分
5. 最后整理结果，以清晰的表格形式呈现给用户

## 注意事项
- 花名册格式可能千差万别，始终先解析再分析
- 如果筛选结果为空，尝试放宽条件
- 向用户解释你的筛选逻辑和结果
- 用中文回复用户
"""


def create_client(api_key: str = None, model: str = None):
    """Create an OpenAI-compatible client for OpenRouter."""
    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise ValueError("请设置 OPENROUTER_API_KEY 环境变量或在侧边栏输入API Key")
    return OpenAI(base_url=OPENROUTER_API_BASE, api_key=key)


def run_query(
    user_message: str,
    file_path: str = None,
    api_key: str = None,
    model: str = None,
    on_tool_start=None,
    on_tool_call=None,
) -> str:
    """Run a user query through the LLM with tool-use loop.

    Args:
        user_message: The user's natural language query.
        file_path: Path to the selected spreadsheet file (injected into context).
        api_key: OpenRouter API key.
        model: Model identifier (e.g. 'anthropic/claude-sonnet-4').
        on_tool_start: Optional callback(tool_name, iteration) before tool execution.
        on_tool_call: Optional callback(tool_name, args, result, iteration) after tool execution.

    Returns:
        The LLM's final text response.
    """
    client = create_client(api_key=api_key)
    model_id = model or DEFAULT_MODEL

    # Build initial messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if file_path:
        context = f"用户已选择花名册文件，路径为: {file_path}\n\n用户的问题: {user_message}"
    else:
        context = user_message
    messages.append({"role": "user", "content": context})

    tool_counter = 0

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        message = choice.message

        # Append assistant message
        messages.append(message)

        # If no tool calls, we're done
        if not message.tool_calls:
            return message.content or ""

        # Process each tool call
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            tool_counter += 1

            # Callback before execution
            if on_tool_start:
                on_tool_start(tool_name, tool_counter)

            # Execute tool
            result = execute_tool(tool_name, arguments)

            # Callback after execution
            if on_tool_call:
                on_tool_call(tool_name, arguments, result, tool_counter)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "已达到最大工具调用次数。请尝试更简单的查询。"

"""LLM Orchestrator: uses OpenRouter API with tool-use loop."""

import json
from openai import OpenAI
from hr_matching.config import OPENROUTER_API_BASE, OPENROUTER_API_KEY, DEFAULT_MODEL, MAX_TOOL_ITERATIONS
from hr_matching.llm.tool_registry import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """你是一个专业的HR花名册分析助手。你的任务是帮助用户从Excel花名册中查找和匹配合适的人选。

你有以下工具可以使用：
1. parse_excel - 解析Excel文件，获取列名、样本数据和全部数据
2. analyze_schema - 分析列名含义，建立语义映射
3. execute_pandas - 【核心工具】执行 pandas 代码，可实现任意筛选、统计、排名
4. search_roster - 简单条件筛选（快速通道，仅支持预定义条件）
5. score_matches - 简单评分排名（快速通道）
6. manage_files - 文件管理（创建文件夹、列目录、移动/复制/删除）
7. create_archive - 为员工创建档案目录（专业技术 + 教育培训）
8. read_reference - 读取档案参考材料（PDF文本提取、图片base64视觉理解、Excel/CSV解析）
9. save_profile - 保存生成的档案文件（.md + .json）并更新处理记录
10. load_knowledge - 加载领域知识（职称评审条件、学历认定规则等 .md 文件）
11. read_policy - 读取制度文件（.pdf/.docx/.txt），提取全文供分析
12. save_knowledge - 将生成的知识保存为 .md 文件到知识库

## 工作流程
当用户选择花名册文件并提出查询时，你应该：
1. 判断查询是否涉及专业判断标准（职称评审、资格认定、岗位匹配等）
   - 如果涉及，先调用 load_knowledge 加载相关领域知识
   - 根据知识中的规则来构建筛选条件，而不是自行推断
2. 调用 parse_excel 解析文件，获取列名和样本数据
3. 观察列名和样本数据，理解表格结构
4. 编写 pandas 代码，调用 execute_pandas 实现筛选/统计/排名
5. 整理结果，以清晰的表格形式呈现给用户
6. **必须提醒 HR**：建议从结果中随机抽取 3-5 人进行核查，确认筛选准确性

## execute_pandas 使用规范
- df 已自动加载为 DataFrame，直接使用即可
- 同时可用：pd (pandas)、re (正则)、datetime
- **必须**将最终结果赋值给 `result` 变量
- 结果行数建议不超过 20 行（用 .head(20)）
- 示例：
  ```python
  # 筛选技术部本科以上
  result = df[df['部门'].str.contains('技术') & df['学历'].isin(['本科', '硕士', '博士'])].head(20)
  ```
  ```python
  # 统计各部门人数
  result = df.groupby('部门').size().reset_index(name='人数')
  ```

## 何时用哪个工具
- **优先使用 execute_pandas**：适用于任意查询，不受预定义条件限制
- search_roster：仅当条件恰好匹配预定义字段（部门、职位、学历等）时可用
- score_matches：需要对候选人评分时可用

## 注意事项
- 花名册格式千差万别，始终先 parse_excel 观察实际列名
- 根据实际列名编写代码，不要假设列名
- 如果筛选结果为空，尝试放宽条件或用模糊匹配（str.contains）
- 向用户解释你的筛选逻辑和结果
- 用中文回复用户

## 代码质量标准：双重自动校验（Pre + Post Validation）
execute_pandas 内置了完全自动化的双重校验机制，无需人工干预：

### 事前检查（Pre-validation）—— 拦截错误代码
- 代码中引用的列名（df['xxx']、.groupby('xxx')、.sort_values('xxx') 等）会在执行前自动与实际列名比对
- 覆盖范围：直接索引、groupby、sort_values、drop、rename、merge、pivot_table、agg 等所有常见 pandas 操作
- 如果引用了不存在的列，代码不会执行，立即返回 available_columns + sample_data
- 你应根据返回信息修正代码后重试

### 事后检查（Post-validation）—— 发现异常结果
- 代码执行成功后，系统自动检测结果异常并在 warnings 字段中提示：
  - 结果为空（0行）但源数据有数据 → 筛选条件可能过严或值不匹配
  - 结果行数等于源数据总行数 → 过滤条件可能未生效
  - 某些列全部为 NaN → 数据类型可能不匹配
- 当你看到 warnings 时，应该主动分析原因并考虑调整代码
- 每次结果都附带 dataframe_meta（列名、类型、行列数）供参考

## 员工档案功能
当用户要求为员工建立档案时：
1. 调用 create_archive 创建目录结构（professional + education 两个子档案）
2. 提示用户将证明材料放入对应的 reference/ 目录
3. 用户确认后调用 read_reference 读取新材料（自动跳过已处理文件）
4. 分析材料内容（包括用视觉能力理解图片中的证书、学历等），分别生成专业技术和教育培训档案
5. 调用 save_profile 保存 .md 和 .json 文件

档案生成规范：
- profile.md：叙述性描述，包含时间线、关键成就、能力评估
- profile.json：高维嵌套 JSON 结构（经历→子项目→技能→关联教育），支持累计效应和经历间微小差异的表达
- 每次只处理新增材料，已处理的通过 memory.md 跳过

## 知识库维护
当用户提供制度文件（.pdf/.docx/.txt）并要求生成或更新知识时：
1. 调用 read_policy 读取制度文件，获取全文内容
2. 分析内容，按知识库规范提取关键规则（标题、适用场景、具体规则、注意事项）
3. 向用户展示生成内容的摘要，让用户确认
4. 用户确认后调用 save_knowledge 保存到 knowledge/ 目录
5. 告知用户：后续涉及该主题的查询将自动加载此知识文件

知识库文件格式规范（.md）：
- 标题：涵盖的知识主题
- 适用场景：LLM 在什么查询下应使用这份知识
- 具体规则：用"条件 → 结论"格式列出判定标准
- 注意事项：容易混淆或需特殊处理的情况
- 结尾提醒 HR 抽样核查结果
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

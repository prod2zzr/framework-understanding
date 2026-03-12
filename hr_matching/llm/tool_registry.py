"""Central tool registry: maps tool names to callables and JSON schemas."""

import json
from hr_matching.tools import parse_excel, analyze_schema, search_roster, score_matches

# --- JSON Schema definitions for OpenAI-compatible function calling ---

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "parse_excel",
            "description": (
                "解析花名册文件，支持.xlsx、.xls、.et（WPS）、.csv格式。"
                "自动检测表头行，返回列名、行数、样本数据和全部数据。"
                "这是第一步：在分析或搜索之前必须先解析文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Excel文件的完整路径",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "可选的工作表名称，不指定则使用第一个工作表",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_schema",
            "description": (
                "分析Excel列名的语义含义，将原始列名映射到标准字段名。"
                "例如将'工号'映射到'employee_id'，'姓名'映射到'name'。"
                "这使后续工具能理解任意格式的花名册。需要传入列名列表和样本数据。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Excel文件的列名列表（来自parse_excel的结果）",
                    },
                    "sample_rows": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "前几行样本数据（来自parse_excel的结果）",
                    },
                },
                "required": ["columns", "sample_rows"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_roster",
            "description": (
                "根据结构化条件筛选候选人。支持的筛选条件包括："
                "department(部门), position(职位), education(最低学历), "
                "min_experience/max_experience(经验年限范围), "
                "min_age/max_age(年龄范围), min_salary/max_salary(薪资范围), "
                "gender(性别), skills(技能,逗号分隔), keyword(关键词全文搜索), "
                "status(在职状态)。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "全部员工数据（来自parse_excel的all_data）",
                    },
                    "column_mapping": {
                        "type": "object",
                        "description": "列名映射（来自analyze_schema的column_mapping）",
                    },
                    "filters": {
                        "type": "object",
                        "description": "筛选条件字典，键为条件名，值为条件值",
                        "properties": {
                            "department": {"type": "string"},
                            "position": {"type": "string"},
                            "education": {"type": "string"},
                            "min_experience": {"type": "number"},
                            "max_experience": {"type": "number"},
                            "min_age": {"type": "number"},
                            "max_age": {"type": "number"},
                            "min_salary": {"type": "number"},
                            "max_salary": {"type": "number"},
                            "gender": {"type": "string"},
                            "skills": {"type": "string"},
                            "keyword": {"type": "string"},
                            "status": {"type": "string"},
                        },
                    },
                },
                "required": ["data", "column_mapping", "filters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_matches",
            "description": (
                "对筛选出的候选人进行评分和排名。根据需求描述中的关键词、"
                "学历、经验等维度给每个候选人打分(0-100)，返回排序后的结果。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "candidates": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "候选人列表（来自search_roster的matched_candidates）",
                    },
                    "requirements": {
                        "type": "string",
                        "description": "自然语言描述的需求，用于评分匹配",
                    },
                    "column_mapping": {
                        "type": "object",
                        "description": "列名映射（来自analyze_schema的column_mapping）",
                    },
                },
                "required": ["candidates", "requirements", "column_mapping"],
            },
        },
    },
]

# --- Callable dispatch map ---

TOOL_CALLABLES = {
    "parse_excel": parse_excel,
    "analyze_schema": analyze_schema,
    "search_roster": search_roster,
    "score_matches": score_matches,
}


def execute_tool(tool_name: str, arguments: dict) -> str:
    """Execute a tool by name with given arguments, return JSON string result."""
    if tool_name not in TOOL_CALLABLES:
        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
    try:
        result = TOOL_CALLABLES[tool_name](**arguments)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {e}"}, ensure_ascii=False)

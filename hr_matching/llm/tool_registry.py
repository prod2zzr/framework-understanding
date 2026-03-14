"""Central tool registry: maps tool names to callables and JSON schemas."""

import json
from hr_matching.tools import (
    parse_excel, analyze_schema, search_roster, score_matches,
    execute_pandas, manage_files,
    create_archive, read_reference, save_profile,
    load_knowledge,
)

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
    {
        "type": "function",
        "function": {
            "name": "execute_pandas",
            "description": (
                "执行 pandas 代码对花名册数据进行任意查询、筛选、统计、排名。"
                "代码中 df 已预加载为 DataFrame（同时可用 pd、re、datetime）。"
                "必须将最终结果赋值给 result 变量。"
                "适用于任意表格结构，不受预定义筛选条件限制。"
                "【内置双重校验】事前：自动校验代码中的列名（索引+方法参数），"
                "不存在则拦截并返回实际列名。事后：自动检测空结果、全量返回、"
                "NaN异常等问题并在warnings字段中提示，全程无需人工干预。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "花名册文件的完整路径",
                    },
                    "code": {
                        "type": "string",
                        "description": (
                            "要执行的 pandas Python 代码。df 已加载，"
                            "将结果赋值给 result 变量。示例：\n"
                            "result = df[df['部门'] == '技术部'].head(20)"
                        ),
                    },
                },
                "required": ["file_path", "code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_files",
            "description": (
                "文件管理工具，支持创建文件夹、列出目录、移动/复制/删除文件等操作。"
                "所有操作限制在项目目录内，受保护的系统文件不允许删除或覆盖。"
                "path 参数使用相对于项目根目录的路径，如 'output/reports'。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create_folder",
                            "list_dir",
                            "move",
                            "copy",
                            "delete",
                            "file_info",
                        ],
                        "description": "要执行的文件操作类型",
                    },
                    "path": {
                        "type": "string",
                        "description": "目标路径（相对于项目根目录）",
                    },
                    "destination": {
                        "type": "string",
                        "description": "目标路径，仅 move 和 copy 操作需要（相对于项目根目录）",
                    },
                },
                "required": ["action", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_archive",
            "description": (
                "为员工创建档案目录结构，包含专业技术档案和教育培训档案两个子目录，"
                "每个子目录下有 reference/ 文件夹供 HR 放入证明材料。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "员工工号（如 EMP001）",
                    },
                    "name": {
                        "type": "string",
                        "description": "员工姓名",
                    },
                },
                "required": ["employee_id", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_reference",
            "description": (
                "读取员工档案中的参考材料。PDF 提取文本，图片返回 base64 供视觉理解，"
                "Excel/CSV 解析为表格，txt/md 直接读取。自动跳过 memory.md 中已标记的已处理文件。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {
                        "type": "string",
                        "description": "员工档案相对路径（如 archives/EMP001_张三）",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["professional", "education"],
                        "description": "档案类别：professional（专业技术）或 education（教育培训）。不指定则两个都读取。",
                    },
                },
                "required": ["archive_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_profile",
            "description": (
                "保存 LLM 生成的员工档案文件（profile.md 叙述档案 + profile.json 结构化数据），"
                "并更新 memory.md 处理记录。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "archive_path": {
                        "type": "string",
                        "description": "员工档案相对路径（如 archives/EMP001_张三）",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["professional", "education"],
                        "description": "档案类别",
                    },
                    "profile_md": {
                        "type": "string",
                        "description": "Markdown 格式的叙述性档案内容（时间线、成就、评估）",
                    },
                    "profile_json": {
                        "type": "string",
                        "description": "JSON 格式的结构化档案数据（高维嵌套，支持经历→子项目→技能→关联关系）",
                    },
                    "processed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "本次处理的参考材料文件名列表",
                    },
                },
                "required": ["archive_path", "category", "profile_md", "profile_json", "processed_files"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_knowledge",
            "description": (
                "加载领域知识文件（.md格式），如职称评审条件、学历认定规则等。"
                "知识文件存放在 knowledge/ 目录中，由 HR 维护，与代码解耦。"
                "不指定 topic 时返回所有可用主题列表；指定 topic 时返回匹配的知识内容。"
                "当用户查询涉及专业判断标准（如职称评审、岗位匹配、资格认定）时应主动加载相关知识。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "知识主题关键词（如'职称'、'学历'、'岗位'）。不指定则列出所有可用主题。",
                    },
                },
                "required": [],
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
    "execute_pandas": execute_pandas,
    "manage_files": manage_files,
    "create_archive": create_archive,
    "read_reference": read_reference,
    "save_profile": save_profile,
    "load_knowledge": load_knowledge,
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

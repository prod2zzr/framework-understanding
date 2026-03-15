"""Tool: Read policy documents and save generated knowledge files.

Enables LLM-assisted knowledge base creation:
  1. read_policy()   — reads .pdf/.docx/.txt policy files, returns text for LLM analysis
  2. save_knowledge() — saves LLM-generated .md to knowledge/ directory
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

from hr_matching.tools.employee_archive import _read_pdf, _read_docx

_KNOWLEDGE_DIR = Path(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge",
    )
)

# Template hint for LLM to follow when generating knowledge files
_FORMAT_HINT = """请根据以上制度文件内容，生成结构化的知识文件（.md格式），包含：
1. **标题**：说明涵盖的知识主题
2. **适用场景**：说明在什么查询场景下应使用这份知识
3. **具体规则**：用"条件 → 结论"格式列出所有判定规则（学历、年限、前置条件等）
4. **注意事项**：容易混淆或需特殊处理的情况
5. 最后一行加上：**提醒 HR**：筛选结果仅为初步匹配，请抽样核查 3-5 人确认准确性

生成完成后调用 save_knowledge 工具保存。"""


def read_policy(file_path: str) -> dict:
    """Read a policy/regulation document and return its text content.

    Supports: .pdf, .docx, .doc, .txt, .md

    Args:
        file_path: Absolute or relative path to the policy document.

    Returns:
        dict with ``success`` flag, ``content`` (extracted text),
        and ``format_hint`` (instructions for generating knowledge).
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"文件不存在: {file_path}"}

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            content = _read_pdf(path)
        elif suffix in (".docx", ".doc"):
            content = _read_docx(path)
        elif suffix in (".txt", ".md"):
            content = path.read_text(encoding="utf-8")
        else:
            return {
                "success": False,
                "error": f"不支持的文件格式: {suffix}。支持 .pdf、.docx、.txt、.md",
            }
    except Exception as e:
        return {"success": False, "error": f"文件读取失败: {e}"}

    if not content or content.startswith("("):
        return {
            "success": False,
            "error": f"文件内容为空或无法提取文本: {content}",
        }

    return {
        "success": True,
        "file_name": path.name,
        "content": content,
        "format_hint": _FORMAT_HINT,
    }


def save_knowledge(topic: str, content: str) -> dict:
    """Save LLM-generated knowledge content as a .md file.

    If a file with the same topic already exists, it is backed up
    as ``{topic}.backup.md`` before being overwritten.

    Args:
        topic: Knowledge topic name (used as filename, e.g. "职称评审条件").
        content: Markdown content to save.

    Returns:
        dict with ``success`` flag and ``file_path``.
    """
    if not topic or not topic.strip():
        return {"success": False, "error": "topic 不能为空"}
    if not content or not content.strip():
        return {"success": False, "error": "content 不能为空"}

    # Ensure knowledge directory exists
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    target = _KNOWLEDGE_DIR / f"{topic.strip()}.md"

    # Backup existing file
    if target.exists():
        backup = _KNOWLEDGE_DIR / f"{topic.strip()}.backup.md"
        shutil.copy2(str(target), str(backup))
        backup_msg = f"已备份旧版本到 {backup.name}"
    else:
        backup_msg = None

    try:
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        return {"success": False, "error": f"文件写入失败: {e}"}

    result = {
        "success": True,
        "file_path": str(target),
        "topic": topic.strip(),
        "message": f"知识文件已保存: {target.name}。后续查询将通过 load_knowledge 自动加载。",
    }
    if backup_msg:
        result["backup"] = backup_msg

    return result

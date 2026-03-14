"""Tool: Load domain knowledge from .md files in the knowledge directory."""

import os
import glob

# Knowledge directory relative to this file's package root
_KNOWLEDGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge",
)


def load_knowledge(topic: str = None) -> dict:
    """Load domain knowledge files.

    Args:
        topic: Optional topic keyword to search for.  If provided, returns
            files whose name contains the keyword.  If omitted, returns a
            list of all available knowledge files.

    Returns:
        dict with ``success`` flag and either ``files`` (list of available
        topics) or ``knowledge`` (list of {filename, content} dicts).
    """
    if not os.path.isdir(_KNOWLEDGE_DIR):
        return {"success": False, "error": "知识库目录不存在。请创建 hr_matching/knowledge/ 并添加 .md 文件。"}

    md_files = sorted(glob.glob(os.path.join(_KNOWLEDGE_DIR, "*.md")))
    # Exclude README.md from knowledge files
    md_files = [f for f in md_files if os.path.basename(f).upper() != "README.MD"]

    if not md_files:
        return {"success": False, "error": "知识库中没有 .md 文件。请在 hr_matching/knowledge/ 中添加知识文件。"}

    # If no topic specified, return list of available files
    if not topic:
        available = [os.path.splitext(os.path.basename(f))[0] for f in md_files]
        return {
            "success": True,
            "available_topics": available,
            "hint": "请指定 topic 参数加载具体知识。例如 topic='职称' 会匹配所有文件名含"职称"的知识文件。",
        }

    # Filter files matching the topic keyword
    matched = [f for f in md_files if topic in os.path.basename(f)]

    if not matched:
        available = [os.path.splitext(os.path.basename(f))[0] for f in md_files]
        return {
            "success": False,
            "error": f"未找到与 '{topic}' 相关的知识文件。",
            "available_topics": available,
        }

    # Read matched files
    knowledge = []
    for fpath in matched:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            knowledge.append({
                "filename": os.path.basename(fpath),
                "content": content,
            })
        except Exception as e:
            knowledge.append({
                "filename": os.path.basename(fpath),
                "error": f"读取失败: {e}",
            })

    return {
        "success": True,
        "knowledge": knowledge,
        "sample_check_reminder": "⚠ 请在向 HR 展示结果时提醒：建议从结果中随机抽取 3-5 人进行人工核查，确认筛选准确性。",
    }

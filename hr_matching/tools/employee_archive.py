"""Employee archive tools – create, read reference materials, save profiles."""

import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ARCHIVES_DIR = _PROJECT_ROOT / "archives"

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
_TEXT_EXTENSIONS = {".txt", ".md", ".json"}
_PDF_EXTENSIONS = {".pdf"}
_EXCEL_EXTENSIONS = {".xlsx", ".xls", ".et", ".csv"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_memory(memory_path: Path) -> set[str]:
    """Parse memory.md and return set of already-processed file names."""
    if not memory_path.exists():
        return set()
    processed = set()
    in_table = False
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| 文件名"):
            in_table = True
            continue
        if line.startswith("|--"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 2 and cols[1]:
                processed.add(cols[1])
        elif in_table and not line.startswith("|"):
            in_table = False
    return processed


def _update_memory(memory_path: Path, employee_id: str, name: str,
                   processed_files: list[dict], category_status: dict):
    """Write / update memory.md with processed file records."""
    existing = set()
    lines_before_table = []
    table_lines = []
    lines_after_status = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if memory_path.exists():
        existing = _parse_memory(memory_path)
        # Preserve existing table rows
        in_table = False
        for line in memory_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| 文件名"):
                in_table = True
                continue
            if line.startswith("|--") and in_table:
                continue
            if in_table and line.startswith("|"):
                table_lines.append(line)
            elif in_table:
                in_table = False

    # Add new entries
    for f in processed_files:
        if f["name"] not in existing:
            table_lines.append(
                f"| {f['name']} | {f.get('type', '未知')} | {now} | {f.get('category', '-')} |"
            )

    # Build full content
    content = f"# 档案处理记录 - {name} ({employee_id})\n"
    content += f"最后更新: {now}\n\n"
    content += "## 已处理文件\n"
    content += "| 文件名 | 类型 | 处理时间 | 档案类别 |\n"
    content += "|--------|------|---------|--------|\n"
    for row in table_lines:
        content += row + "\n"
    content += "\n## 状态\n"
    for cat, status in category_status.items():
        content += f"- {cat}: {status}\n"

    memory_path.write_text(content, encoding="utf-8")


def _read_pdf(file_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file_path))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- 第{i+1}页 ---\n{text}")
        return "\n\n".join(pages_text) if pages_text else "(PDF无可提取文本，可能为扫描件)"
    except Exception as e:
        return f"(PDF读取失败: {e})"


def _read_docx(file_path: Path) -> str:
    """Extract text from a .docx file."""
    try:
        from docx import Document
        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs) if paragraphs else "(Word文档无可提取文本)"
    except Exception as e:
        return f"(Word文档读取失败: {e})"


def _read_image_base64(file_path: Path) -> str:
    """Read image file and return base64 encoded string."""
    data = file_path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def _image_mime(suffix: str) -> str:
    """Return MIME type for image suffix."""
    mapping = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".bmp": "image/bmp",
        ".webp": "image/webp", ".gif": "image/gif",
    }
    return mapping.get(suffix.lower(), "image/png")


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def create_archive(employee_id: str, name: str) -> dict:
    """Create the archive directory structure for an employee.

    Args:
        employee_id: Employee ID (e.g. "EMP001").
        name: Employee name (e.g. "张三").

    Returns:
        dict with success flag, archive_path, and directory structure.
    """
    folder_name = f"{employee_id}_{name}"
    archive_path = _ARCHIVES_DIR / folder_name

    dirs_to_create = [
        archive_path / "professional" / "reference",
        archive_path / "education" / "reference",
    ]

    already_existed = archive_path.exists()

    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    # List structure
    structure = []
    for root, dirs, files in os.walk(str(archive_path)):
        rel = os.path.relpath(root, str(_PROJECT_ROOT))
        for f in files:
            structure.append(os.path.join(rel, f))
        if not files and not dirs:
            structure.append(rel + "/")

    rel_path = str(archive_path.relative_to(_PROJECT_ROOT))

    return {
        "success": True,
        "archive_path": rel_path,
        "already_existed": already_existed,
        "structure": structure,
        "message": (
            f"档案目录{'已存在' if already_existed else '已创建'}: {rel_path}\n"
            f"请将专业技术材料放入 {rel_path}/professional/reference/\n"
            f"请将教育培训材料放入 {rel_path}/education/reference/"
        ),
    }


def read_reference(archive_path: str, category: str = None) -> dict:
    """Read reference materials from an employee's archive.

    Scans the reference/ directories, skips already-processed files
    (tracked in memory.md), and returns file contents for new files.

    Args:
        archive_path: Relative path to the employee archive (e.g. "archives/EMP001_张三").
        category: "professional", "education", or None (both).

    Returns:
        dict with files list, new_files, and processed_files.
    """
    resolved = (_PROJECT_ROOT / archive_path).resolve()
    if not str(resolved).startswith(str(_PROJECT_ROOT)):
        return {"success": False, "error": "路径越界"}
    if not resolved.is_dir():
        return {"success": False, "error": f"档案目录不存在: {archive_path}"}

    memory_path = resolved / "memory.md"
    already_processed = _parse_memory(memory_path)

    categories = []
    if category in ("professional", "education"):
        categories = [category]
    else:
        categories = ["professional", "education"]

    all_files = []
    new_files = []
    processed_files = []

    for cat in categories:
        ref_dir = resolved / cat / "reference"
        if not ref_dir.is_dir():
            continue

        for f in sorted(ref_dir.iterdir()):
            if not f.is_file():
                continue
            suffix = f.suffix.lower()
            file_info = {
                "name": f.name,
                "category": cat,
                "size_bytes": f.stat().st_size,
            }

            if f.name in already_processed:
                file_info["status"] = "already_processed"
                processed_files.append(file_info)
                continue

            # Read content based on type
            if suffix in _PDF_EXTENSIONS:
                file_info["type"] = "pdf"
                file_info["content"] = _read_pdf(f)
            elif suffix in _IMAGE_EXTENSIONS:
                file_info["type"] = "image"
                file_info["mime"] = _image_mime(suffix)
                file_info["image_base64"] = _read_image_base64(f)
                file_info["content"] = f"[图片文件: {f.name}, 已编码为base64，请用视觉能力分析]"
            elif suffix in _TEXT_EXTENSIONS:
                file_info["type"] = "text"
                file_info["content"] = f.read_text(encoding="utf-8", errors="replace")
            elif suffix in _EXCEL_EXTENSIONS:
                file_info["type"] = "spreadsheet"
                try:
                    import pandas as pd
                    if suffix == ".csv":
                        df = pd.read_csv(str(f))
                    else:
                        df = pd.read_excel(str(f))
                    file_info["content"] = df.head(50).to_string(index=False)
                    file_info["row_count"] = len(df)
                except Exception as e:
                    file_info["content"] = f"(读取失败: {e})"
            else:
                file_info["type"] = "unknown"
                file_info["content"] = f"(不支持的文件格式: {suffix})"

            file_info["status"] = "new"
            new_files.append(file_info)

        all_files.extend(new_files)
        all_files.extend(processed_files)

    return {
        "success": True,
        "archive_path": archive_path,
        "total_files": len(all_files),
        "new_count": len(new_files),
        "processed_count": len(processed_files),
        "new_files": new_files,
        "processed_files": [{"name": f["name"], "category": f["category"]} for f in processed_files],
    }


def save_profile(archive_path: str, category: str,
                 profile_md: str, profile_json: str,
                 processed_files: list) -> dict:
    """Save LLM-generated profile files and update memory.md.

    Args:
        archive_path: Relative path to the employee archive.
        category: "professional" or "education".
        profile_md: Markdown content for the narrative profile.
        profile_json: JSON string for the structured profile data.
        processed_files: List of file names that were processed to generate this profile.

    Returns:
        dict with success flag and written file paths.
    """
    resolved = (_PROJECT_ROOT / archive_path).resolve()
    if not str(resolved).startswith(str(_PROJECT_ROOT)):
        return {"success": False, "error": "路径越界"}

    if category not in ("professional", "education"):
        return {"success": False, "error": f"category 必须是 'professional' 或 'education'，收到: {category}"}

    cat_dir = resolved / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    # Write profile.md
    md_path = cat_dir / "profile.md"
    md_path.write_text(profile_md, encoding="utf-8")

    # Write profile.json
    json_path = cat_dir / "profile.json"
    # Validate JSON if it's a string
    if isinstance(profile_json, str):
        try:
            parsed = json.loads(profile_json)
            json_path.write_text(
                json.dumps(parsed, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except json.JSONDecodeError:
            json_path.write_text(profile_json, encoding="utf-8")
    else:
        json_path.write_text(
            json.dumps(profile_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Update memory.md
    # Extract employee_id and name from archive_path
    folder_name = Path(archive_path).name
    parts = folder_name.split("_", 1)
    emp_id = parts[0] if parts else folder_name
    emp_name = parts[1] if len(parts) > 1 else ""

    # Build processed file records
    file_records = [
        {"name": f, "type": "参考材料", "category": category}
        for f in processed_files
    ]

    # Determine category status
    memory_path = resolved / "memory.md"
    status = {}
    other_cat = "education" if category == "professional" else "professional"
    status[category] = f"已生成 ({len(processed_files)} 份材料)"
    # Check if other category has profile
    other_profile = resolved / other_cat / "profile.md"
    if other_profile.exists():
        status[other_cat] = "已生成"
    else:
        status[other_cat] = "待处理"

    _update_memory(memory_path, emp_id, emp_name, file_records, status)

    files_written = [
        str(md_path.relative_to(_PROJECT_ROOT)),
        str(json_path.relative_to(_PROJECT_ROOT)),
        str(memory_path.relative_to(_PROJECT_ROOT)),
    ]

    return {
        "success": True,
        "files_written": files_written,
        "message": f"{category} 档案已保存，共处理 {len(processed_files)} 份材料",
    }

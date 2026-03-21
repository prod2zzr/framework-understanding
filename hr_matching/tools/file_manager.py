"""File management tool – sandboxed to the project directory."""

import os
import shutil
from datetime import datetime
from pathlib import Path

# Project root – all operations are confined within this directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Paths that cannot be deleted or overwritten (relative to project root)
_PROTECTED_PATHS = {
    ".git",
    ".env",
    ".env.example",
    ".gitignore",
    "hr_matching",
    "setup.bat",
    "start.bat",
    "requirements.txt",
    "README.md",
}


def _resolve_and_validate(path: str) -> tuple[Path, str | None]:
    """Resolve a relative path and validate it stays inside the project root.

    Returns (resolved_path, error_message). error_message is None if valid.
    """
    # Treat as relative to project root
    resolved = (_PROJECT_ROOT / path).resolve()
    if not str(resolved).startswith(str(_PROJECT_ROOT)):
        return resolved, f"路径越界：不允许操作项目目录之外的路径 ({path})"
    return resolved, None


def _is_protected(resolved: Path) -> bool:
    """Check whether *resolved* falls under a protected path."""
    rel = resolved.relative_to(_PROJECT_ROOT)
    # Check each component of the relative path against protected set
    for protected in _PROTECTED_PATHS:
        protected_path = _PROJECT_ROOT / protected
        if resolved == protected_path or str(resolved).startswith(str(protected_path) + os.sep):
            return True
    return False


def manage_files(action: str, path: str, destination: str = None) -> dict:
    """Perform a file-system operation confined to the project directory.

    Args:
        action: One of create_folder, list_dir, move, copy, delete, file_info.
        path: Target path (relative to project root).
        destination: Destination path for move/copy (relative to project root).

    Returns:
        dict with ``success`` flag and ``result`` or ``error``.
    """
    resolved, err = _resolve_and_validate(path)
    if err:
        return {"success": False, "error": err}

    try:
        if action == "create_folder":
            resolved.mkdir(parents=True, exist_ok=True)
            return {"success": True, "result": f"文件夹已创建: {resolved.relative_to(_PROJECT_ROOT)}"}

        elif action == "list_dir":
            if not resolved.is_dir():
                return {"success": False, "error": f"不是目录: {path}"}
            entries = []
            for item in sorted(resolved.iterdir()):
                entries.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return {"success": True, "result": entries, "count": len(entries)}

        elif action == "move":
            if not destination:
                return {"success": False, "error": "move 操作需要提供 destination 参数"}
            dest_resolved, dest_err = _resolve_and_validate(destination)
            if dest_err:
                return {"success": False, "error": dest_err}
            if _is_protected(resolved):
                return {"success": False, "error": f"受保护路径，不允许移动: {path}"}
            # Ensure destination parent exists
            dest_resolved.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(resolved), str(dest_resolved))
            return {"success": True, "result": f"已移动: {path} → {destination}"}

        elif action == "copy":
            if not destination:
                return {"success": False, "error": "copy 操作需要提供 destination 参数"}
            dest_resolved, dest_err = _resolve_and_validate(destination)
            if dest_err:
                return {"success": False, "error": dest_err}
            dest_resolved.parent.mkdir(parents=True, exist_ok=True)
            if resolved.is_dir():
                shutil.copytree(str(resolved), str(dest_resolved))
            else:
                shutil.copy2(str(resolved), str(dest_resolved))
            return {"success": True, "result": f"已复制: {path} → {destination}"}

        elif action == "delete":
            if _is_protected(resolved):
                return {"success": False, "error": f"受保护路径，不允许删除: {path}"}
            if not resolved.exists():
                return {"success": False, "error": f"路径不存在: {path}"}
            if resolved.is_dir():
                if any(resolved.iterdir()):
                    return {"success": False, "error": f"文件夹非空，不允许删除: {path}（请先清空内容）"}
                resolved.rmdir()
            else:
                resolved.unlink()
            return {"success": True, "result": f"已删除: {path}"}

        elif action == "file_info":
            if not resolved.exists():
                return {"success": False, "error": f"路径不存在: {path}"}
            stat = resolved.stat()
            return {
                "success": True,
                "result": {
                    "path": str(resolved.relative_to(_PROJECT_ROOT)),
                    "type": "dir" if resolved.is_dir() else "file",
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                },
            }

        else:
            return {"success": False, "error": f"未知操作: {action}。支持: create_folder, list_dir, move, copy, delete, file_info"}

    except Exception as e:
        return {"success": False, "error": f"操作失败: {type(e).__name__}: {e}"}

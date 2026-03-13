"""Execute LLM-generated pandas code against a loaded DataFrame."""

import re
import signal
import pandas as pd

# Patterns that indicate dangerous code
_FORBIDDEN_PATTERNS = [
    r'\bimport\s+os\b',
    r'\bimport\s+sys\b',
    r'\bimport\s+subprocess\b',
    r'\bimport\s+shutil\b',
    r'\bfrom\s+os\b',
    r'\bfrom\s+subprocess\b',
    r'\bopen\s*\(',
    r'\bexec\s*\(',
    r'\beval\s*\(',
    r'\bcompile\s*\(',
    r'\b__\w+__\b',       # dunder attributes
    r'\bglobals\s*\(',
    r'\blocals\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
    r'\bdelattr\s*\(',
    r'\bbreakpoint\s*\(',
]

_MAX_RESULT_ROWS = 50
_TIMEOUT_SECONDS = 10


def _check_code_safety(code: str) -> str | None:
    """Return an error message if code contains forbidden patterns, else None."""
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return f"代码安全检查未通过：检测到禁止的模式 '{pattern}'"
    return None


def _timeout_handler(signum, frame):
    raise TimeoutError("代码执行超时")


def _load_dataframe(file_path: str) -> pd.DataFrame:
    """Load a spreadsheet file into a DataFrame."""
    lower = file_path.lower()
    if lower.endswith('.csv'):
        return pd.read_csv(file_path)
    else:
        return pd.read_excel(file_path)


def execute_pandas(file_path: str, code: str) -> dict:
    """Execute pandas code against a spreadsheet file.

    The code runs in a restricted namespace with ``df`` (the loaded DataFrame),
    ``pd``, ``re``, and ``datetime`` available.  The code **must** assign its
    final output to a variable called ``result``.

    Args:
        file_path: Path to the spreadsheet file.
        code: Python/pandas code to execute.

    Returns:
        dict with ``success`` flag, ``result`` (data), and ``row_count``.
    """
    # Safety check
    error = _check_code_safety(code)
    if error:
        return {"success": False, "error": error}

    # Load data
    try:
        df = _load_dataframe(file_path)
    except Exception as e:
        return {"success": False, "error": f"文件加载失败: {e}"}

    # Build restricted namespace
    import datetime as _dt
    namespace = {
        "df": df,
        "pd": pd,
        "re": re,
        "datetime": _dt,
    }

    # Execute with timeout
    old_handler = None
    try:
        # Set timeout (only works on Unix; skip on Windows)
        try:
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(_TIMEOUT_SECONDS)
        except (AttributeError, ValueError):
            pass  # Windows or non-main thread

        _SAFE_BUILTINS = {
            "len": len, "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "tuple": tuple, "set": set,
            "range": range, "enumerate": enumerate, "zip": zip,
            "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
            "sorted": sorted, "reversed": reversed, "filter": filter, "map": map,
            "any": any, "all": all, "isinstance": isinstance, "type": type,
            "print": print, "True": True, "False": False, "None": None,
        }
        exec(code, {"__builtins__": _SAFE_BUILTINS}, namespace)

        # Cancel alarm
        try:
            signal.alarm(0)
        except (AttributeError, ValueError):
            pass

    except TimeoutError:
        return {"success": False, "error": f"代码执行超时（限制 {_TIMEOUT_SECONDS} 秒）"}
    except Exception as e:
        return {"success": False, "error": f"代码执行出错: {type(e).__name__}: {e}"}
    finally:
        if old_handler is not None:
            try:
                signal.signal(signal.SIGALRM, old_handler)
                signal.alarm(0)
            except (AttributeError, ValueError):
                pass

    # Extract result
    if "result" not in namespace:
        return {"success": False, "error": "代码中未定义 result 变量。请将最终结果赋值给 result。"}

    result = namespace["result"]

    # Convert result to JSON-friendly format
    try:
        if isinstance(result, pd.DataFrame):
            truncated = len(result) > _MAX_RESULT_ROWS
            data = result.head(_MAX_RESULT_ROWS).to_dict(orient="records")
            return {
                "success": True,
                "result": data,
                "row_count": len(result),
                "truncated": truncated,
                "columns": list(result.columns),
            }
        elif isinstance(result, pd.Series):
            truncated = len(result) > _MAX_RESULT_ROWS
            data = result.head(_MAX_RESULT_ROWS).to_dict()
            return {
                "success": True,
                "result": data,
                "row_count": len(result),
                "truncated": truncated,
            }
        else:
            return {
                "success": True,
                "result": result,
            }
    except Exception as e:
        return {"success": False, "error": f"结果序列化失败: {e}"}

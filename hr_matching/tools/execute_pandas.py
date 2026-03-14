"""Execute LLM-generated pandas code against a loaded DataFrame.

Safety layers (executed in order):
1. Forbidden-pattern scan  – blocks dangerous code before execution
2. Column pre-validation   – catches wrong column names before execution
3. Sandboxed exec          – restricted builtins + timeout
4. Result serialisation    – truncation + metadata attachment
"""

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

# Patterns to extract column name references from pandas code
# Matches: df['col'], df["col"], df.loc[:, 'col'], df[["col1", "col2"]]
_COLUMN_REF_PATTERNS = [
    r"""df\s*\[\s*['\"](.+?)['\"]\s*\]""",          # df['col'] or df["col"]
    r"""df\s*\[\s*\[\s*['\"](.+?)['\"]\s*""",        # df[["col1" ...
    r"""df\s*\.\s*loc\s*\[.*?,\s*['\"](.+?)['\"]\s*\]""",  # df.loc[:, 'col']
    r"""['\"](.+?)['\"]\s*\]\s*\]""",                # ... "col2"]] continuation
]

_MAX_RESULT_ROWS = 50
_TIMEOUT_SECONDS = 10


def _check_code_safety(code: str) -> str | None:
    """Return an error message if code contains forbidden patterns, else None."""
    for pattern in _FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return f"代码安全检查未通过：检测到禁止的模式 '{pattern}'"
    return None


def _extract_column_refs(code: str) -> set[str]:
    """Extract column name references from pandas code."""
    refs = set()
    for pattern in _COLUMN_REF_PATTERNS:
        for match in re.finditer(pattern, code):
            refs.add(match.group(1))
    return refs


def _validate_columns(code: str, df: pd.DataFrame) -> dict | None:
    """Pre-validate that column names referenced in code exist in the DataFrame.

    Returns an error dict if invalid columns are found, else None.
    """
    referenced = _extract_column_refs(code)
    if not referenced:
        return None  # no column refs detected; skip validation

    actual_columns = set(df.columns)
    invalid = referenced - actual_columns

    if not invalid:
        return None  # all referenced columns exist

    return {
        "success": False,
        "error": (
            f"列名预校验失败：代码引用了不存在的列 {sorted(invalid)}。"
            f"\n实际可用列名：{list(df.columns)}"
            f"\n请检查列名后重新编写代码。"
        ),
        "available_columns": list(df.columns),
        "invalid_columns": sorted(invalid),
        "sample_data": df.head(3).to_dict(orient="records"),
    }


def _build_dataframe_meta(df: pd.DataFrame) -> dict:
    """Build DataFrame metadata for LLM context."""
    return {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


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

    Safety pipeline (in order):
    1. Forbidden-pattern scan
    2. Column-name pre-validation (catches wrong column refs before exec)
    3. Sandboxed execution with timeout
    4. Result serialisation with DataFrame metadata

    Args:
        file_path: Path to the spreadsheet file.
        code: Python/pandas code to execute.

    Returns:
        dict with ``success`` flag, ``result`` (data), ``row_count``,
        and ``dataframe_meta`` (columns, dtypes, shape).
    """
    # 1. Safety check
    error = _check_code_safety(code)
    if error:
        return {"success": False, "error": error}

    # 2. Load data
    try:
        df = _load_dataframe(file_path)
    except Exception as e:
        return {"success": False, "error": f"文件加载失败: {e}"}

    # 3. Column pre-validation — catch wrong column names before execution
    col_error = _validate_columns(code, df)
    if col_error:
        return col_error

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

    # Build metadata once for all return paths
    meta = _build_dataframe_meta(df)

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
                "dataframe_meta": meta,
            }
        elif isinstance(result, pd.Series):
            truncated = len(result) > _MAX_RESULT_ROWS
            data = result.head(_MAX_RESULT_ROWS).to_dict()
            return {
                "success": True,
                "result": data,
                "row_count": len(result),
                "truncated": truncated,
                "dataframe_meta": meta,
            }
        else:
            return {
                "success": True,
                "result": result,
                "dataframe_meta": meta,
            }
    except Exception as e:
        return {"success": False, "error": f"结果序列化失败: {e}"}

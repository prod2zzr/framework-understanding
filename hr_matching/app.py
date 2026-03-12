"""Streamlit UI for the HR Roster Matching Application."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
from hr_matching.llm.orchestrator import run_query

_CONFIG_DIR = Path.home() / ".hr_matching"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".et", ".csv"}


def _load_saved_key() -> str:
    """Load API key from local config file."""
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("api_key", "")
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def _save_key(key: str):
    """Save API key to local config file."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(
        json.dumps({"api_key": key}, ensure_ascii=False),
        encoding="utf-8",
    )


def _scan_data_dir() -> list[Path]:
    """Scan data/ directory for supported spreadsheet files."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(_DATA_DIR.iterdir()):
        if f.suffix.lower() in _SUPPORTED_EXTENSIONS:
            files.append(f)
    return files


st.set_page_config(page_title="HR花名册智能匹配", page_icon="👥", layout="wide")

# Resolve default key: saved file > env var
_default_key = _load_saved_key() or os.environ.get("OPENROUTER_API_KEY", "")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input(
        "OpenRouter API Key",
        value=_default_key,
        type="password",
        help="从 https://openrouter.ai/keys 获取，输入后自动保存到本地",
    )
    # Auto-save when key changes
    if api_key and api_key != _load_saved_key():
        _save_key(api_key)
        st.caption("API Key 已保存，下次无需重新输入")
    elif api_key:
        st.caption("API Key 已从本地加载")

    model = st.selectbox(
        "选择模型",
        [
            "anthropic/claude-sonnet-4",
            "anthropic/claude-haiku-4",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-2.0-flash-001",
        ],
        index=0,
    )
    st.divider()
    st.markdown("### 📖 使用说明")
    st.markdown(
        "1. 输入 OpenRouter API Key（仅需一次）\n"
        "2. 将花名册文件放入 `data/` 文件夹\n"
        "3. 在下方选择文件，用自然语言提问\n"
        "4. AI 会自动解析、筛选、评分"
    )

# --- Main Area ---
st.title("👥 HR花名册智能匹配系统")
st.caption("所有数据均在本地处理，不会上传到任何服务器")

# --- File Selection (local folder scan) ---
available_files = _scan_data_dir()

file_path = None
if not available_files:
    st.info(
        f"📂 请将 Excel/CSV 花名册文件放入项目的 **data/** 文件夹中\n\n"
        f"支持格式：.xlsx、.xls、.et（WPS）、.csv\n\n"
        f"文件夹路径：`{_DATA_DIR}`"
    )
    if st.button("🔄 刷新文件列表"):
        st.rerun()
else:
    selected_name = st.selectbox(
        "📂 选择花名册文件（来自 data/ 文件夹）",
        [f.name for f in available_files],
        help=f"将文件放入 {_DATA_DIR} 即可在此显示",
    )
    if selected_name:
        file_path = str(_DATA_DIR / selected_name)

        # Preview
        with st.expander("📋 预览文件内容", expanded=False):
            try:
                if selected_name.lower().endswith(".csv"):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                st.dataframe(df.head(10), use_container_width=True)
                st.caption(f"共 {len(df)} 行, {len(df.columns)} 列")
            except Exception as e:
                st.warning(f"预览失败: {e}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("描述你要找的人，例如：帮我找技术部3年以上经验的本科生"):
    if not api_key:
        st.error("请先在侧边栏输入 OpenRouter API Key")
        st.stop()

    if not file_path:
        st.error("请先将花名册文件放入 data/ 文件夹")
        st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run LLM query
    with st.chat_message("assistant"):
        tool_log = st.expander("🔧 工具调用过程", expanded=False)
        tool_calls_log = []

        def on_tool_call(name, args, result):
            # Show condensed args (don't dump huge data arrays)
            display_args = {}
            for k, v in args.items():
                if isinstance(v, list) and len(v) > 3:
                    display_args[k] = f"[...{len(v)} items...]"
                elif isinstance(v, str) and len(v) > 200:
                    display_args[k] = v[:200] + "..."
                else:
                    display_args[k] = v
            tool_calls_log.append({
                "tool": name,
                "args": display_args,
            })
            with tool_log:
                st.markdown(f"**调用工具**: `{name}`")
                st.json(display_args)

        with st.spinner("AI 正在分析花名册..."):
            try:
                response = run_query(
                    user_message=prompt,
                    file_path=file_path,
                    api_key=api_key,
                    model=model,
                    on_tool_call=on_tool_call,
                )
            except Exception as e:
                response = f"出错了: {e}"

        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

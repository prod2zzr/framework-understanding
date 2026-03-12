"""Streamlit UI for the HR Roster Matching Application."""

import json
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
from hr_matching.llm.orchestrator import run_query

_CONFIG_DIR = Path.home() / ".hr_matching"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


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
        "2. 上传任意格式的 HR Excel 花名册\n"
        "3. 用自然语言描述你要找的人\n"
        "4. AI 会自动解析、筛选、评分"
    )

# --- Main Area ---
st.title("👥 HR花名册智能匹配系统")
st.caption("上传任意格式的Excel花名册，用自然语言查找合适的人选")

# File uploader
uploaded_file = st.file_uploader(
    "上传Excel花名册",
    type=["xlsx", "xls"],
    help="支持任意格式的Excel花名册，系统会自动识别列含义",
)

# Save uploaded file to temp path
file_path = None
if uploaded_file is not None:
    suffix = ".xlsx" if uploaded_file.name.endswith(".xlsx") else ".xls"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        file_path = tmp.name

    # Preview the file
    with st.expander("📋 预览上传的文件", expanded=False):
        try:
            df = pd.read_excel(uploaded_file)
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
        st.error("请先上传Excel花名册文件")
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

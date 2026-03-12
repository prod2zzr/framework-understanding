import os

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = "anthropic/claude-sonnet-4"
MAX_TOOL_ITERATIONS = 15

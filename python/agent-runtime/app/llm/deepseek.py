"""DeepSeek 模型适配（向后兼容层）。

新代码请使用 app.llm.gateway：支持 DeepSeek + 通义千问双模型路由与故障降级。
"""
import os

from app.llm.gateway import generate_answer  # noqa: F401  re-export


def deepseek_enabled() -> bool:
    return os.getenv("DEEPSEEK_ENABLED", "false").lower() == "true" and bool(os.getenv("DEEPSEEK_API_KEY"))


def get_deepseek_model():
    if not deepseek_enabled():
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024")),
    )
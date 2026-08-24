"""模型网关：多模型路由与故障降级。

- 默认提供商 LLM_PROVIDER=deepseek，可切换 qwen（通义千问 OpenAI 兼容模式）；
- 主模型不可用或调用异常时自动降级备用模型（LLM_FALLBACK=true 时）；
- 所有提供商均不可用时返回 None，由调用方兜底提示。
"""
import logging
import os

logger = logging.getLogger(__name__)


def _deepseek_enabled() -> bool:
    return os.getenv("DEEPSEEK_ENABLED", "false").lower() == "true" and bool(os.getenv("DEEPSEEK_API_KEY"))


def _qwen_enabled() -> bool:
    return bool(os.getenv("QWEN_API_KEY"))


def available_providers() -> list[str]:
    providers: list[str] = []
    if _deepseek_enabled():
        providers.append("deepseek")
    if _qwen_enabled():
        providers.append("qwen")
    return providers


def default_provider() -> str | None:
    preferred = os.getenv("LLM_PROVIDER", "deepseek").lower()
    providers = available_providers()
    if preferred in providers:
        return preferred
    if providers:
        return providers[0]
    return None


def fallback_enabled() -> bool:
    return os.getenv("LLM_FALLBACK", "true").lower() != "false"


def _build_model(provider: str):
    from langchain_openai import ChatOpenAI

    if provider == "deepseek":
        return ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024")),
        )
    if provider == "qwen":
        return ChatOpenAI(
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            api_key=os.environ["QWEN_API_KEY"],
            base_url=os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            temperature=float(os.getenv("QWEN_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("QWEN_MAX_TOKENS", "1024")),
        )
    raise ValueError(f"未知模型提供商: {provider}")


async def generate_answer(
    system_prompt: str,
    user_message: str,
    provider: str | None = None,
) -> str | None:
    """按默认提供商调用大模型；失败且开启降级时自动切换备用提供商。"""
    providers = available_providers()
    if not providers:
        logger.warning("未配置任何可用的大模型提供商")
        return None

    primary = provider or default_provider()
    order = [primary] if primary in providers else list(providers)
    if fallback_enabled():
        order = order + [p for p in providers if p not in order]

    last_error: Exception | None = None
    for name in order:
        try:
            model = _build_model(name)
            response = await model.ainvoke([
                ("system", system_prompt),
                ("human", user_message),
            ])
            logger.info("LLM 调用成功：provider=%s", name)
            return str(response.content)
        except Exception as exc:
            last_error = exc
            logger.warning("LLM 调用失败 provider=%s: %s", name, exc)
    logger.error("所有模型提供商均调用失败: %s", last_error)
    return None
import os


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


async def generate_answer(system_prompt: str, user_message: str) -> str | None:
    model = get_deepseek_model()
    if model is None:
        return None
    response = await model.ainvoke([
        ("system", system_prompt),
        ("human", user_message),
    ])
    return str(response.content)


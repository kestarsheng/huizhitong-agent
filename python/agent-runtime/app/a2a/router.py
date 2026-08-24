"""A2A 智能体路由：LLM 识别应转发的智能体，失败自动降级规则匹配。

- 默认关闭 LLM 路由（A2A_LLM_ROUTING=false），使用注册表规则匹配；
- 开启后调用模型网关识别目标智能体（JSON 数组），解析失败/模型不可用一律返回
  None，由编排层降级到规则匹配，保证链路始终可用。
"""
import json
import logging
import os

from app.a2a.registry import AGENTS
from app.llm import gateway

logger = logging.getLogger(__name__)


def llm_routing_enabled() -> bool:
    return os.getenv("A2A_LLM_ROUTING", "false").lower() == "true"


def _agent_catalog() -> str:
    return "\n".join(
        f"- {agent_id}: {agent.name}，{agent.description}"
        for agent_id, agent in AGENTS.items()
    )


def _extract_json_array(raw: str) -> list | None:
    """从 LLM 输出中提取 JSON 数组，兼容 ```json 代码块包裹。"""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


async def llm_route(message: str) -> list[str] | None:
    """调用大模型做意图路由；任何异常返回 None 由调用方降级规则匹配。"""
    if not llm_routing_enabled():
        return None
    system_prompt = (
        "你是智能体中台的意图路由引擎。请根据用户消息判断应转发给哪些智能体，"
        "只输出 JSON 数组（元素为智能体 id，可多个），不要输出任何其它内容。\n\n"
        "可用智能体：\n"
        f"{_agent_catalog()}\n\n"
        "若消息不属于任何业务智能体，返回 [\"customer_service\"]。"
    )
    raw = await gateway.generate_answer(system_prompt, message)
    if not raw:
        return None
    parsed = _extract_json_array(raw)
    if parsed is None:
        logger.warning("LLM 路由输出解析失败，降级规则匹配: %s", raw[:80])
        return None
    return [item for item in parsed if item in AGENTS]
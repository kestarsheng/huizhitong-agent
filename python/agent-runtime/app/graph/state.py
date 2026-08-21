from typing import Annotated, TypedDict

RESET_MARKER = "__RESET__"


def resetable_add(left: list[str] | None, right: list[str] | None) -> list[str]:
    """支持回合重置的列表累加器。

    节点返回 [RESET_MARKER] 时清空历史（用于多轮会话中开启新回合）；
    其余情况按顺序拼接，配合 LangGraph 并行分支聚合各步结果。
    """
    if right:
        if right[0] == RESET_MARKER:
            return list(right[1:])
        return list(left or []) + list(right)
    return list(left or [])


class AgentState(TypedDict, total=False):
    agent_type: str
    conversation_id: str
    tenant_id: int
    user_message: str
    intent: str
    intents: list[str]
    plan: list[str]
    step_answers: Annotated[list[str], resetable_add]
    step_statuses: Annotated[list[str], resetable_add]
    answer: str
    status: str
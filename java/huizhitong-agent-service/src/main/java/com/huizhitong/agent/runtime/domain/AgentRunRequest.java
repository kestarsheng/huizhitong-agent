package com.huizhitong.agent.runtime.domain;

public record AgentRunRequest(String agentType, String conversationId, String message,
                              Long userId, Long tenantId, boolean stream) {
}

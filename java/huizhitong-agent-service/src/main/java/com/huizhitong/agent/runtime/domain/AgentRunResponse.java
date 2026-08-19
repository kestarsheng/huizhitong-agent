package com.huizhitong.agent.runtime.domain;

public record AgentRunResponse(String conversationId, String agentType, String status, String answer) {
}

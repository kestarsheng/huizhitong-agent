package com.huizhitong.agent.version;

import jakarta.validation.constraints.NotBlank;

public record AgentVersionRequest(@NotBlank String systemPrompt, @NotBlank String modelName) {
}

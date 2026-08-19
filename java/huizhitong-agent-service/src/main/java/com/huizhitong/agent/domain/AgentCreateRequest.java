package com.huizhitong.agent.domain;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AgentCreateRequest(
        @NotBlank @Size(max = 100) String agentType,
        @NotBlank @Size(max = 100) String name,
        @Size(max = 500) String description,
        @NotBlank String systemPrompt,
        @NotBlank @Size(max = 100) String modelName
) {}

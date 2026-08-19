package com.huizhitong.tool.domain;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class ToolGrantRequest {
    @NotBlank private String agentType;
    @NotNull private Long tenantId;
    @NotNull private Long toolId;
}

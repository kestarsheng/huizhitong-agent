package com.huizhitong.tool.domain;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ToolDefinition {
    private Long id;
    @NotBlank private String toolName;
    @NotBlank private String serverName;
    private String description;
    private String inputSchema;
    private Integer enabled = 1;
    private Long tenantId;
}

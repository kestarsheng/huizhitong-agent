-- 工具注册中心表结构（与 huizhitong 库共用，utf8mb4）
CREATE TABLE IF NOT EXISTS tool_registry (
    id          BIGINT       NOT NULL AUTO_INCREMENT,
    tool_name   VARCHAR(64)  NOT NULL COMMENT '工具名称，注册中心内唯一',
    server_name VARCHAR(64)  NOT NULL COMMENT '所属 MCP Server 名称',
    description VARCHAR(255) NOT NULL DEFAULT '' COMMENT '工具描述',
    input_schema TEXT        NULL COMMENT '入参 JSON Schema',
    enabled     TINYINT      NOT NULL DEFAULT 1 COMMENT '1 启用 / 0 停用',
    tenant_id   BIGINT       NULL COMMENT '归属租户，NULL 表示平台级公共工具',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_tool_name (tool_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 智能体/租户的工具授权关系
CREATE TABLE IF NOT EXISTS tool_grants (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    agent_type VARCHAR(64) NOT NULL COMMENT '智能体类型，如 ticket / inventory',
    tenant_id  BIGINT      NOT NULL COMMENT '租户 ID',
    tool_id    BIGINT      NOT NULL COMMENT 'tool_registry.id',
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_agent_tenant_tool (agent_type, tenant_id, tool_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

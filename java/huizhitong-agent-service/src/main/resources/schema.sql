CREATE TABLE IF NOT EXISTS agent (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    system_prompt TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    status TINYINT NOT NULL DEFAULT 1,
    version INT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tenant_agent_type (tenant_id, agent_type)
);

CREATE TABLE IF NOT EXISTS agent_version (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    agent_id BIGINT NOT NULL,
    tenant_id BIGINT NOT NULL,
    version INT NOT NULL,
    system_prompt TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    status TINYINT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME NULL,
    UNIQUE KEY uk_agent_version (agent_id, version),
    KEY idx_tenant_agent (tenant_id, agent_id)
);

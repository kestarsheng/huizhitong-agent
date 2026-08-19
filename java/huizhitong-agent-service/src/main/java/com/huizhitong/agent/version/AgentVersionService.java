package com.huizhitong.agent.version;

import com.baomidou.mybatisplus.extension.service.IService;

import java.util.List;

public interface AgentVersionService extends IService<AgentVersion> {
    AgentVersion create(Long tenantId, Long agentId, AgentVersionRequest request);
    AgentVersion publish(Long tenantId, Long agentId, Long versionId);
    AgentVersion rollback(Long tenantId, Long agentId, Long versionId);
    List<AgentVersion> listVersions(Long tenantId, Long agentId);
}

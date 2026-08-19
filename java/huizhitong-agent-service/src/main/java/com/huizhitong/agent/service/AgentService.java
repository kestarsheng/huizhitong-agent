package com.huizhitong.agent.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.huizhitong.agent.domain.Agent;
import com.huizhitong.agent.domain.AgentCreateRequest;
import com.huizhitong.agent.domain.AgentUpdateRequest;

import java.util.List;

public interface AgentService extends IService<Agent> {
    Agent create(Long tenantId, AgentCreateRequest request);
    Agent update(Long tenantId, Long id, AgentUpdateRequest request);
    List<Agent> listByTenant(Long tenantId);
}

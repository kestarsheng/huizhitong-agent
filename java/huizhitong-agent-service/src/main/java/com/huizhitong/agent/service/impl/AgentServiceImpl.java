package com.huizhitong.agent.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huizhitong.agent.domain.Agent;
import com.huizhitong.agent.domain.AgentCreateRequest;
import com.huizhitong.agent.domain.AgentUpdateRequest;
import com.huizhitong.agent.mapper.AgentMapper;
import com.huizhitong.agent.service.AgentService;
import com.huizhitong.common.api.ResultCode;
import com.huizhitong.common.exception.BusinessException;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AgentServiceImpl extends ServiceImpl<AgentMapper, Agent> implements AgentService {
    @Override
    public Agent create(Long tenantId, AgentCreateRequest request) {
        boolean exists = lambdaQuery().eq(Agent::getTenantId, tenantId)
                .eq(Agent::getAgentType, request.agentType()).exists();
        if (exists) {
            throw new BusinessException(409, "该租户下的智能体类型已存在");
        }
        Agent agent = new Agent();
        BeanUtils.copyProperties(request, agent);
        agent.setTenantId(tenantId);
        agent.setStatus(1);
        agent.setVersion(1);
        agent.setCreatedAt(LocalDateTime.now());
        agent.setUpdatedAt(LocalDateTime.now());
        save(agent);
        return agent;
    }

    @Override
    public Agent update(Long tenantId, Long id, AgentUpdateRequest request) {
        Agent agent = getByTenantAndId(tenantId, id);
        BeanUtils.copyProperties(request, agent);
        agent.setVersion(agent.getVersion() + 1);
        agent.setUpdatedAt(LocalDateTime.now());
        updateById(agent);
        return agent;
    }

    @Override
    public List<Agent> listByTenant(Long tenantId) {
        return list(new LambdaQueryWrapper<Agent>()
                .eq(Agent::getTenantId, tenantId)
                .orderByDesc(Agent::getUpdatedAt));
    }

    private Agent getByTenantAndId(Long tenantId, Long id) {
        Agent agent = lambdaQuery().eq(Agent::getTenantId, tenantId)
                .eq(Agent::getId, id).one();
        if (agent == null) {
            throw new BusinessException(ResultCode.NOT_FOUND);
        }
        return agent;
    }
}

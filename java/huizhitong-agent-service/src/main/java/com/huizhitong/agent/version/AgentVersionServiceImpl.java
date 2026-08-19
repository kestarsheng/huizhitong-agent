package com.huizhitong.agent.version;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huizhitong.agent.domain.Agent;
import com.huizhitong.agent.mapper.AgentMapper;
import com.huizhitong.common.api.ResultCode;
import com.huizhitong.common.exception.BusinessException;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class AgentVersionServiceImpl extends ServiceImpl<AgentVersionMapper, AgentVersion>
        implements AgentVersionService {
    private final AgentMapper agentMapper;

    public AgentVersionServiceImpl(AgentMapper agentMapper) {
        this.agentMapper = agentMapper;
    }

    @Override
    public AgentVersion create(Long tenantId, Long agentId, AgentVersionRequest request) {
        Agent agent = findAgent(tenantId, agentId);
        Integer nextVersion = lambdaQuery().eq(AgentVersion::getTenantId, tenantId)
                .eq(AgentVersion::getAgentId, agentId)
                .orderByDesc(AgentVersion::getVersion).last("LIMIT 1")
                .oneOpt().map(v -> v.getVersion() + 1).orElse(1);
        AgentVersion version = new AgentVersion();
        version.setAgentId(agent.getId());
        version.setTenantId(tenantId);
        version.setVersion(nextVersion);
        version.setSystemPrompt(request.systemPrompt());
        version.setModelName(request.modelName());
        version.setStatus(0);
        version.setCreatedAt(LocalDateTime.now());
        save(version);
        return version;
    }

    @Override
    public AgentVersion publish(Long tenantId, Long agentId, Long versionId) {
        AgentVersion version = findVersion(tenantId, agentId, versionId);
        lambdaUpdate().set(AgentVersion::getStatus, 0)
                .eq(AgentVersion::getTenantId, tenantId)
                .eq(AgentVersion::getAgentId, agentId)
                .update();
        version.setStatus(1);
        version.setPublishedAt(LocalDateTime.now());
        updateById(version);
        return version;
    }

    @Override
    public AgentVersion rollback(Long tenantId, Long agentId, Long versionId) {
        return publish(tenantId, agentId, versionId);
    }

    @Override
    public List<AgentVersion> listVersions(Long tenantId, Long agentId) {
        findAgent(tenantId, agentId);
        return list(new LambdaQueryWrapper<AgentVersion>().eq(AgentVersion::getTenantId, tenantId)
                .eq(AgentVersion::getAgentId, agentId).orderByDesc(AgentVersion::getVersion));
    }

    private Agent findAgent(Long tenantId, Long agentId) {
        Agent agent = agentMapper.selectOne(new LambdaQueryWrapper<Agent>()
                .eq(Agent::getTenantId, tenantId).eq(Agent::getId, agentId));
        if (agent == null) throw new BusinessException(ResultCode.NOT_FOUND);
        return agent;
    }

    private AgentVersion findVersion(Long tenantId, Long agentId, Long versionId) {
        AgentVersion version = lambdaQuery().eq(AgentVersion::getTenantId, tenantId)
                .eq(AgentVersion::getAgentId, agentId).eq(AgentVersion::getId, versionId).one();
        if (version == null) throw new BusinessException(ResultCode.NOT_FOUND);
        return version;
    }
}

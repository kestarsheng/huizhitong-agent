package com.huizhitong.tool.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.huizhitong.tool.domain.ToolDefinition;
import com.huizhitong.tool.domain.ToolGrant;
import com.huizhitong.tool.mapper.ToolGrantMapper;
import com.huizhitong.tool.mapper.ToolRegistryMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class ToolRegistryService {
    private final ToolRegistryMapper toolMapper;
    private final ToolGrantMapper grantMapper;

    public ToolRegistryService(ToolRegistryMapper toolMapper, ToolGrantMapper grantMapper) {
        this.toolMapper = toolMapper;
        this.grantMapper = grantMapper;
    }

    /** 注册工具；tool_name 已存在时直接返回已有记录，保证启动注册幂等。 */
    public ToolDefinition register(ToolDefinition definition) {
        ToolDefinition existing = toolMapper.selectOne(new LambdaQueryWrapper<ToolDefinition>()
                .eq(ToolDefinition::getToolName, definition.getToolName()));
        if (existing != null) {
            return existing;
        }
        toolMapper.insert(definition);
        return definition;
    }

    public List<ToolDefinition> list(Long tenantId, boolean enabledOnly) {
        LambdaQueryWrapper<ToolDefinition> wrapper = new LambdaQueryWrapper<>();
        if (tenantId != null) {
            wrapper.eq(ToolDefinition::getTenantId, tenantId);
        }
        if (enabledOnly) {
            wrapper.eq(ToolDefinition::getEnabled, 1);
        }
        return toolMapper.selectList(wrapper);
    }

    public ToolDefinition toggle(Long id, boolean enabled) {
        ToolDefinition definition = toolMapper.selectById(id);
        if (definition == null) throw new IllegalArgumentException("工具不存在: " + id);
        definition.setEnabled(enabled ? 1 : 0);
        toolMapper.updateById(definition);
        return definition;
    }

    @Transactional
    public void grant(String agentType, Long tenantId, Long toolId) {
        if (toolMapper.selectById(toolId) == null) throw new IllegalArgumentException("工具不存在: " + toolId);
        Long count = grantMapper.selectCount(new LambdaQueryWrapper<ToolGrant>()
                .eq(ToolGrant::getAgentType, agentType)
                .eq(ToolGrant::getTenantId, tenantId)
                .eq(ToolGrant::getToolId, toolId));
        if (count == null || count == 0) {
            ToolGrant grant = new ToolGrant();
            grant.setAgentType(agentType);
            grant.setTenantId(tenantId);
            grant.setToolId(toolId);
            grantMapper.insert(grant);
        }
    }

    /** 撤销租户/智能体对某工具的使用授权。 */
    public void revoke(String agentType, Long tenantId, Long toolId) {
        grantMapper.delete(new LambdaQueryWrapper<ToolGrant>()
                .eq(ToolGrant::getAgentType, agentType)
                .eq(ToolGrant::getTenantId, tenantId)
                .eq(ToolGrant::getToolId, toolId));
    }

    /** 查询授权记录；可按智能体类型与租户过滤。 */
    public List<ToolGrant> listGrants(String agentType, Long tenantId) {
        LambdaQueryWrapper<ToolGrant> wrapper = new LambdaQueryWrapper<>();
        if (agentType != null && !agentType.isBlank()) {
            wrapper.eq(ToolGrant::getAgentType, agentType);
        }
        if (tenantId != null) {
            wrapper.eq(ToolGrant::getTenantId, tenantId);
        }
        return grantMapper.selectList(wrapper);
    }

    public List<ToolDefinition> available(String agentType, Long tenantId) {
        List<ToolGrant> grants = grantMapper.selectList(new LambdaQueryWrapper<ToolGrant>()
                .eq(ToolGrant::getAgentType, agentType)
                .eq(ToolGrant::getTenantId, tenantId));
        if (grants.isEmpty()) {
            return List.of();
        }
        List<Long> toolIds = grants.stream().map(ToolGrant::getToolId).toList();
        return toolMapper.selectList(new LambdaQueryWrapper<ToolDefinition>()
                .in(ToolDefinition::getId, toolIds)
                .eq(ToolDefinition::getEnabled, 1));
    }
}
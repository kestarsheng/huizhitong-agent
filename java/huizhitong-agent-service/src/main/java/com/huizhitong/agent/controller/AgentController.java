package com.huizhitong.agent.controller;

import com.huizhitong.agent.domain.Agent;
import com.huizhitong.agent.domain.AgentCreateRequest;
import com.huizhitong.agent.domain.AgentUpdateRequest;
import com.huizhitong.agent.service.AgentService;
import com.huizhitong.common.api.ApiResult;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/agents")
public class AgentController {
    private final AgentService agentService;

    public AgentController(AgentService agentService) {
        this.agentService = agentService;
    }

    @GetMapping
    public ApiResult<List<Agent>> list(
            @RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId) {
        return ApiResult.success(agentService.listByTenant(tenantId), "");
    }

    @PostMapping
    public ApiResult<Agent> create(
            @RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
            @Valid @RequestBody AgentCreateRequest request) {
        return ApiResult.success(agentService.create(tenantId, request), "");
    }

    @PutMapping("/{id}")
    public ApiResult<Agent> update(
            @RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
            @PathVariable Long id,
            @Valid @RequestBody AgentUpdateRequest request) {
        return ApiResult.success(agentService.update(tenantId, id, request), "");
    }

    @DeleteMapping("/{id}")
    public ApiResult<Void> delete(
            @RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
            @PathVariable Long id) {
        Agent agent = agentService.getOne(new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Agent>()
                .eq(Agent::getTenantId, tenantId).eq(Agent::getId, id));
        if (agent == null) {
            throw new com.huizhitong.common.exception.BusinessException(com.huizhitong.common.api.ResultCode.NOT_FOUND);
        }
        agentService.removeById(id);
        return ApiResult.success(null, "");
    }
}

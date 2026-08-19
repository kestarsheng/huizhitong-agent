package com.huizhitong.agent.runtime.controller;

import com.huizhitong.agent.domain.Agent;
import com.huizhitong.agent.runtime.client.AgentRuntimeClient;
import com.huizhitong.agent.runtime.domain.AgentRunRequest;
import com.huizhitong.agent.runtime.domain.AgentRunResponse;
import com.huizhitong.agent.service.AgentService;
import com.huizhitong.common.api.ApiResult;
import com.huizhitong.common.api.ResultCode;
import com.huizhitong.common.exception.BusinessException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/agents")
public class AgentRuntimeController {
    private final AgentService agentService;
    private final AgentRuntimeClient runtimeClient;

    public AgentRuntimeController(AgentService agentService, AgentRuntimeClient runtimeClient) {
        this.agentService = agentService;
        this.runtimeClient = runtimeClient;
    }

    @PostMapping("/{agentId}/run")
    public ApiResult<AgentRunResponse> run(
            @RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
            @PathVariable Long agentId,
            @Valid @RequestBody RunRequest request) {
        Agent agent = agentService.getOne(new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Agent>()
                .eq(Agent::getId, agentId).eq(Agent::getTenantId, tenantId));
        if (agent == null) throw new BusinessException(ResultCode.NOT_FOUND);
        AgentRunResponse response = runtimeClient.run(new AgentRunRequest(
                agent.getAgentType(), request.conversationId(), request.message(),
                request.userId(), tenantId, false));
        return ApiResult.success(response, "");
    }

    public record RunRequest(@NotBlank String conversationId, @NotBlank String message, Long userId) {
    }
}

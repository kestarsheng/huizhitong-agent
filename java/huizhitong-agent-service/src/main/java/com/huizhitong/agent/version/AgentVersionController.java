package com.huizhitong.agent.version;

import com.huizhitong.common.api.ApiResult;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/agents/{agentId}/versions")
public class AgentVersionController {
    private final AgentVersionService service;

    public AgentVersionController(AgentVersionService service) { this.service = service; }

    @GetMapping
    public ApiResult<List<AgentVersion>> list(@RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
                                              @PathVariable Long agentId) {
        return ApiResult.success(service.listVersions(tenantId, agentId), "");
    }

    @PostMapping
    public ApiResult<AgentVersion> create(@RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
                                          @PathVariable Long agentId,
                                          @Valid @RequestBody AgentVersionRequest request) {
        return ApiResult.success(service.create(tenantId, agentId, request), "");
    }

    @PostMapping("/{versionId}/publish")
    public ApiResult<AgentVersion> publish(@RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
                                           @PathVariable Long agentId, @PathVariable Long versionId) {
        return ApiResult.success(service.publish(tenantId, agentId, versionId), "");
    }

    @PostMapping("/{versionId}/rollback")
    public ApiResult<AgentVersion> rollback(@RequestHeader(value = "X-Tenant-Id", defaultValue = "1") Long tenantId,
                                            @PathVariable Long agentId, @PathVariable Long versionId) {
        return ApiResult.success(service.rollback(tenantId, agentId, versionId), "");
    }
}

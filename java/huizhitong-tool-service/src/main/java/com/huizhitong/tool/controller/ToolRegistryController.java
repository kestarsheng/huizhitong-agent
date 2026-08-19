package com.huizhitong.tool.controller;

import com.huizhitong.tool.domain.ToolDefinition;
import com.huizhitong.tool.domain.ToolGrantRequest;
import com.huizhitong.tool.service.ToolRegistryService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/internal/tools")
public class ToolRegistryController {
    private final ToolRegistryService service;
    public ToolRegistryController(ToolRegistryService service) { this.service = service; }

    @PostMapping
    public ToolDefinition register(@Valid @RequestBody ToolDefinition definition) { return service.register(definition); }

    @GetMapping
    public List<ToolDefinition> list(@RequestParam(required = false) Long tenantId,
                                     @RequestParam(defaultValue = "true") boolean enabledOnly) {
        return service.list(tenantId, enabledOnly);
    }

    @PatchMapping("/{id}/status")
    public ToolDefinition toggle(@PathVariable Long id, @RequestParam boolean enabled) {
        return service.toggle(id, enabled);
    }

    @PostMapping("/grants")
    public void grant(@Valid @RequestBody ToolGrantRequest request) {
        service.grant(request.getAgentType(), request.getTenantId(), request.getToolId());
    }

    @GetMapping("/available")
    public List<ToolDefinition> available(@RequestParam String agentType, @RequestParam Long tenantId) {
        return service.available(agentType, tenantId);
    }
}

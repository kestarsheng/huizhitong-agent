package com.huizhitong.tool.service;

import com.huizhitong.tool.domain.ToolDefinition;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.Set;
import java.util.HashSet;

@Service
public class ToolRegistryService {
    private final AtomicLong sequence = new AtomicLong(0);
    private final Map<Long, ToolDefinition> tools = new ConcurrentHashMap<>();
    private final Map<String, Set<Long>> grants = new ConcurrentHashMap<>();

    public ToolDefinition register(ToolDefinition definition) {
        definition.setId(sequence.incrementAndGet());
        tools.put(definition.getId(), definition);
        return definition;
    }

    public List<ToolDefinition> list(Long tenantId, boolean enabledOnly) {
        return tools.values().stream()
                .filter(item -> tenantId == null || tenantId.equals(item.getTenantId()))
                .filter(item -> !enabledOnly || Integer.valueOf(1).equals(item.getEnabled()))
                .toList();
    }

    public ToolDefinition toggle(Long id, boolean enabled) {
        ToolDefinition definition = tools.get(id);
        if (definition == null) throw new IllegalArgumentException("工具不存在: " + id);
        definition.setEnabled(enabled ? 1 : 0);
        return definition;
    }

    public void grant(String agentType, Long tenantId, Long toolId) {
        if (!tools.containsKey(toolId)) throw new IllegalArgumentException("工具不存在: " + toolId);
        grants.computeIfAbsent(key(agentType, tenantId), ignored -> ConcurrentHashMap.newKeySet()).add(toolId);
    }

    public List<ToolDefinition> available(String agentType, Long tenantId) {
        Set<Long> ids = grants.getOrDefault(key(agentType, tenantId), Set.of());
        return ids.stream().map(tools::get).filter(item -> item != null && Integer.valueOf(1).equals(item.getEnabled())).toList();
    }

    private String key(String agentType, Long tenantId) { return tenantId + ":" + agentType; }
}

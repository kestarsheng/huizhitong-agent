package com.huizhitong.agent.runtime.client;

import com.huizhitong.agent.runtime.domain.AgentRunRequest;
import com.huizhitong.agent.runtime.domain.AgentRunResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "agent-runtime", url = "${agent.runtime.url:http://localhost:8000}")
public interface AgentRuntimeClient {
    @PostMapping("/internal/agents/run")
    AgentRunResponse run(@RequestBody AgentRunRequest request);
}

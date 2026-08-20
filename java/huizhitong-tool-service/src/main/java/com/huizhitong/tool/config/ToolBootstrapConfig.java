package com.huizhitong.tool.config;

import com.huizhitong.tool.domain.ToolDefinition;
import com.huizhitong.tool.service.ToolRegistryService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ToolBootstrapConfig {
    @Bean
    CommandLineRunner registerBuiltInTools(ToolRegistryService service) {
        return args -> {
            ToolDefinition query = new ToolDefinition();
            query.setToolName("query_inventory");
            query.setServerName("inventory-server");
            query.setDescription("查询商品库存和仓库信息");
            query.setInputSchema("{\"product_id\":\"string\"}");
            service.register(query);

            ToolDefinition risk = new ToolDefinition();
            risk.setToolName("analyze_inventory_risk");
            risk.setServerName("inventory-server");
            risk.setDescription("分析库存安全风险并给出补货建议");
            risk.setInputSchema("{\"product_id\":\"string\"}");
            service.register(risk);

            ToolDefinition createTicket = new ToolDefinition();
            createTicket.setToolName("create_ticket");
            createTicket.setServerName("ticket-server");
            createTicket.setDescription("创建售后工单并返回工单号");
            createTicket.setInputSchema("{\"subject\":\"string\",\"description\":\"string\",\"priority\":\"string\"}");
            service.register(createTicket);

            ToolDefinition queryTicket = new ToolDefinition();
            queryTicket.setToolName("query_ticket");
            queryTicket.setServerName("ticket-server");
            queryTicket.setDescription("按工单号查询工单状态与详情");
            queryTicket.setInputSchema("{\"ticket_id\":\"string\"}");
            service.register(queryTicket);
        };
    }
}

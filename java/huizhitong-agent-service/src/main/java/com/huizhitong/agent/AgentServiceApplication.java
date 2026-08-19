package com.huizhitong.agent;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@MapperScan("com.huizhitong.agent.mapper")
@SpringBootApplication
public class AgentServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AgentServiceApplication.class, args);
    }
}

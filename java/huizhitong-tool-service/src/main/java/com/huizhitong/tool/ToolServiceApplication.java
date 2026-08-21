package com.huizhitong.tool;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.mybatis.spring.annotation.MapperScan;

@SpringBootApplication
@MapperScan("com.huizhitong.tool.mapper")
public class ToolServiceApplication {
    public static void main(String[] args) { SpringApplication.run(ToolServiceApplication.class, args); }
}

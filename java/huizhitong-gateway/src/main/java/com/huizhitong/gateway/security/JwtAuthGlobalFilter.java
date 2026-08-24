package com.huizhitong.gateway.security;

import io.jsonwebtoken.Claims;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;

@Component
public class JwtAuthGlobalFilter implements GlobalFilter, Ordered {
    private final JwtUtil jwtUtil;

    private static final String[] WHITELIST = {"/api/auth/login", "/api/internal/health", "/internal/health", "/actuator/"};

    public JwtAuthGlobalFilter(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();
        for (String prefix : WHITELIST) {
            if (path.startsWith(prefix)) {
                return chain.filter(exchange);
            }
        }
        String header = exchange.getRequest().getHeaders().getFirst("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            return unauthorized(exchange, "缺少访问令牌");
        }
        try {
            Claims claims = jwtUtil.parse(header.substring(7));
            ServerWebExchange mutated = exchange.mutate()
                    .request(builder -> builder
                            .header("X-User-Id", claims.get("uid", String.class))
                            .header("X-Username", claims.getSubject())
                            .header("X-User-Role", String.valueOf(claims.get("role", String.class))))
                    .build();
            return chain.filter(mutated);
        } catch (Exception ex) {
            return unauthorized(exchange, "访问令牌无效或已过期");
        }
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        exchange.getResponse().getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] bytes = ("{\"code\":401,\"message\":\"" + message + "\"}").getBytes(StandardCharsets.UTF_8);
        DataBuffer buffer = exchange.getResponse().bufferFactory().wrap(bytes);
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
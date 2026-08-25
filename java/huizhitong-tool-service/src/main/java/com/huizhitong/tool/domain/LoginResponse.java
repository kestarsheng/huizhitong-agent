package com.huizhitong.tool.domain;

public record LoginResponse(String token, String username, String role, long expiresIn, Long tenantId) {
}

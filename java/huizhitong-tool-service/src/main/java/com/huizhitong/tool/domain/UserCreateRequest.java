package com.huizhitong.tool.domain;

public record UserCreateRequest(String username, String password, String role, Long tenantId) {
}

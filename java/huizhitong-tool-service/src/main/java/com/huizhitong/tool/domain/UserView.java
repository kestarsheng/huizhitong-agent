package com.huizhitong.tool.domain;

public record UserView(Long id, String username, String role, Integer enabled, String createdAt, Long tenantId) {
}

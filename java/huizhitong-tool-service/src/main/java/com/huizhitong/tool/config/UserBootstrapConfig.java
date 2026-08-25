package com.huizhitong.tool.config;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.huizhitong.tool.domain.SysUser;
import com.huizhitong.tool.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;

@Configuration
public class UserBootstrapConfig {

    @Bean
    CommandLineRunner initAdminUser(JdbcTemplate jdbc, UserMapper userMapper, PasswordEncoder encoder,
                                    @Value("${auth.admin-username:admin}") String adminUsername,
                                    @Value("${auth.admin-init-password:admin123}") String adminPassword) {
        return args -> {
            jdbc.execute("CREATE TABLE IF NOT EXISTS users ("
                    + "id BIGINT AUTO_INCREMENT PRIMARY KEY,"
                    + "username VARCHAR(64) NOT NULL UNIQUE,"
                    + "password_hash VARCHAR(100) NOT NULL,"
                    + "role VARCHAR(32) NOT NULL DEFAULT 'ADMIN',"
                    + "tenant_id BIGINT NULL,"
                    + "enabled TINYINT NOT NULL DEFAULT 1,"
                    + "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    + ") DEFAULT CHARSET=utf8mb4");
            Integer tenantCol = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'tenant_id'",
                    Integer.class);
            if (tenantCol == null || tenantCol == 0) {
                jdbc.execute("ALTER TABLE users ADD COLUMN tenant_id BIGINT NULL");
            }
            Long count = userMapper.selectCount(new LambdaQueryWrapper<SysUser>()
                    .eq(SysUser::getUsername, adminUsername));
            if (count == null || count == 0) {
                SysUser user = new SysUser();
                user.setUsername(adminUsername);
                user.setPasswordHash(encoder.encode(adminPassword));
                user.setRole("ADMIN");
                user.setEnabled(1);
                userMapper.insert(user);
                System.out.println("已初始化管理员账号: " + adminUsername);
            }
            Long tenantCount = userMapper.selectCount(new LambdaQueryWrapper<SysUser>()
                    .eq(SysUser::getUsername, "tenant1"));
            if (tenantCount == null || tenantCount == 0) {
                SysUser tenantUser = new SysUser();
                tenantUser.setUsername("tenant1");
                tenantUser.setPasswordHash(encoder.encode("123456"));
                tenantUser.setRole("USER");
                tenantUser.setEnabled(1);
                tenantUser.setTenantId(1L);
                userMapper.insert(tenantUser);
                System.out.println("已初始化演示租户账号: tenant1 / 123456 (tenantId=1)");
            }
        };
    }
}

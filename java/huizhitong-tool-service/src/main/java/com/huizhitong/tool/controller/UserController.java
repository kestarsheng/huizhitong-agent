package com.huizhitong.tool.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.huizhitong.tool.domain.PasswordUpdateRequest;
import com.huizhitong.tool.domain.SysUser;
import com.huizhitong.tool.domain.UserCreateRequest;
import com.huizhitong.tool.domain.UserView;
import com.huizhitong.tool.mapper.UserMapper;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/internal/users")
public class UserController {

    private static final Set<String> ROLES = Set.of("ADMIN", "OPERATOR", "VIEWER", "USER");

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    public UserController(UserMapper userMapper, PasswordEncoder passwordEncoder) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
    }

    @GetMapping
    public List<UserView> list() {
        return userMapper.selectList(new LambdaQueryWrapper<SysUser>().orderByAsc(SysUser::getId))
                .stream().map(this::toView).toList();
    }

    @PostMapping
    public UserView create(@RequestBody UserCreateRequest request) {
        String username = request.username() == null ? "" : request.username().trim();
        String password = request.password() == null ? "" : request.password();
        String role = request.role() == null ? "" : request.role().trim().toUpperCase();
        if (username.length() < 3 || username.length() > 64) {
            throw new IllegalArgumentException("用户名长度需在 3-64 之间");
        }
        if (password.length() < 6 || password.length() > 64) {
            throw new IllegalArgumentException("密码长度需在 6-64 之间");
        }
        if (!ROLES.contains(role)) {
            throw new IllegalArgumentException("角色仅支持 ADMIN / OPERATOR / VIEWER / USER");
        }
        if ("USER".equals(role) && (request.tenantId() == null || request.tenantId() <= 0)) {
            throw new IllegalArgumentException("租户用户必须指定租户 ID");
        }
        Long exists = userMapper.selectCount(new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getUsername, username));
        if (exists != null && exists > 0) {
            throw new IllegalArgumentException("用户名已存在");
        }
        SysUser user = new SysUser();
        user.setUsername(username);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setRole(role);
        user.setTenantId(request.tenantId());
        user.setEnabled(1);
        userMapper.insert(user);
        return toView(user);
    }

    @PatchMapping("/{id}/status")
    public UserView toggleStatus(@PathVariable Long id, @RequestParam boolean enabled, Authentication authentication) {
        SysUser user = requireUser(id);
        if (user.getUsername().equals(authentication.getName())) {
            throw new IllegalArgumentException("不能停用自己的账号");
        }
        user.setEnabled(enabled ? 1 : 0);
        userMapper.updateById(user);
        return toView(user);
    }

    @PatchMapping("/{id}/password")
    public Map<String, Object> resetPassword(@PathVariable Long id, @RequestBody PasswordUpdateRequest request) {
        String password = request.newPassword() == null ? "" : request.newPassword();
        if (password.length() < 6 || password.length() > 64) {
            throw new IllegalArgumentException("密码长度需在 6-64 之间");
        }
        SysUser user = requireUser(id);
        user.setPasswordHash(passwordEncoder.encode(password));
        userMapper.updateById(user);
        return Map.of("message", "密码已重置");
    }

    private SysUser requireUser(Long id) {
        SysUser user = userMapper.selectById(id);
        if (user == null) {
            throw new IllegalArgumentException("用户不存在");
        }
        return user;
    }

    private UserView toView(SysUser user) {
        return new UserView(user.getId(), user.getUsername(), user.getRole(), user.getEnabled(), user.getCreatedAt(), user.getTenantId());
    }
}

package com.huizhitong.tool.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.huizhitong.tool.domain.LoginRequest;
import com.huizhitong.tool.domain.LoginResponse;
import com.huizhitong.tool.domain.SysUser;
import com.huizhitong.tool.mapper.UserMapper;
import com.huizhitong.tool.security.JwtUtil;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthController(UserMapper userMapper, PasswordEncoder passwordEncoder, JwtUtil jwtUtil) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @PostMapping("/login")
    public LoginResponse login(@RequestBody LoginRequest request) {
        SysUser user = userMapper.selectOne(new LambdaQueryWrapper<SysUser>()
                .eq(SysUser::getUsername, request.username()));
        if (user == null || user.getEnabled() == null || user.getEnabled() != 1
                || !passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new IllegalArgumentException("用户名或密码错误");
        }
        String token = jwtUtil.createToken(user.getId(), user.getUsername(), user.getRole());
        return new LoginResponse(token, user.getUsername(), user.getRole(), jwtUtil.getExpireSeconds());
    }
}
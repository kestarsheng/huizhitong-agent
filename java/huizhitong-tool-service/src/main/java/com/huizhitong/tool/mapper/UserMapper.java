package com.huizhitong.tool.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huizhitong.tool.domain.SysUser;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<SysUser> {
}
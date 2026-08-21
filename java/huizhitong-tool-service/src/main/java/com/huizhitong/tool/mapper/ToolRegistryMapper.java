package com.huizhitong.tool.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huizhitong.tool.domain.ToolDefinition;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface ToolRegistryMapper extends BaseMapper<ToolDefinition> {
}

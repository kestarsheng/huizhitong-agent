package com.huizhitong.tool.domain;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("tool_grants")
public class ToolGrant {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String agentType;
    private Long tenantId;
    private Long toolId;
}

package com.huizhitong.agent.version;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("agent_version")
public class AgentVersion {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long agentId;
    private Long tenantId;
    private Integer version;
    private String systemPrompt;
    private String modelName;
    private Integer status;
    private LocalDateTime createdAt;
    private LocalDateTime publishedAt;
}

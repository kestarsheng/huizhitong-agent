-- 汇智通工单表结构（MySQL）
CREATE DATABASE IF NOT EXISTS huizhitong DEFAULT CHARACTER SET utf8mb4;
USE huizhitong;

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id   VARCHAR(32)  NOT NULL COMMENT '工单号',
    subject     VARCHAR(255) NOT NULL COMMENT '工单主题',
    description TEXT         NOT NULL COMMENT '工单描述',
    priority    VARCHAR(16)  NOT NULL COMMENT '优先级 LOW/MEDIUM/HIGH',
    customer_id VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '客户编号',
    status      VARCHAR(16)  NOT NULL COMMENT '状态 OPEN/CLOSED',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (ticket_id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '售后工单表';

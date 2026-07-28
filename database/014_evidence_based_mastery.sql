-- 掌握度改为基于真实答题证据计算。
-- 50 仅是服务端内部中性先验；answer_count=0 时客户端必须显示“待评估”。
ALTER TABLE `knowledge_mastery`
    MODIFY COLUMN `mastery_score` INT NOT NULL DEFAULT 50
        COMMENT '掌握度内部估计: 0-100；无证据时显示待评估',
    MODIFY COLUMN `learning_status` VARCHAR(32) NOT NULL DEFAULT 'weak'
        COMMENT 'weak/consolidating/mastered';

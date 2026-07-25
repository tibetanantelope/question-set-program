-- ============================================================
-- 成员三：答案分析、掌握度、错题订正与定期复习
-- 迁移编号: 004_mastery_and_mistake.sql
-- 创建时间: 2026-07-23
-- ============================================================
-- 依赖: question 表（003_learning_and_practice.sql）
-- ============================================================

-- 答题记录表（每道题的判题结果持久化）
CREATE TABLE IF NOT EXISTS `answer_record` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `practice_id` INT NOT NULL COMMENT '关联练习组ID',
    `question_id` INT NOT NULL COMMENT '关联题目ID',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '知识点名称',
    `difficulty` VARCHAR(32) NOT NULL DEFAULT 'easy' COMMENT 'easy/medium/hard',
    `user_answer` TEXT DEFAULT NULL COMMENT '学生答案',
    `is_correct` TINYINT(1) NOT NULL COMMENT '判断结果',
    `error_type` VARCHAR(32) DEFAULT NULL COMMENT 'knowledge/calculation/reading/method',
    `error_description` TEXT DEFAULT NULL COMMENT '错因说明',
    `request_id` VARCHAR(128) DEFAULT NULL COMMENT '幂等标识',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '答题时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_practice_id` (`practice_id`),
    INDEX `idx_question_id` (`question_id`),
    INDEX `idx_knowledge_point` (`user_id`, `knowledge_point_id`),
    UNIQUE INDEX `idx_request_id` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='答题记录表';

-- 知识点掌握度表（每个用户每个知识点一条记录）
CREATE TABLE IF NOT EXISTS `knowledge_mastery` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `knowledge_point_id` INT NOT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) NOT NULL COMMENT '知识点名称',
    `mastery_score` INT NOT NULL DEFAULT 60 COMMENT '掌握度: 0-100',
    `learning_status` VARCHAR(32) NOT NULL DEFAULT 'consolidating' COMMENT 'weak/consolidating/mastered',
    `answer_count` INT NOT NULL DEFAULT 0 COMMENT '累计答题次数',
    `correct_count` INT NOT NULL DEFAULT 0 COMMENT '累计答对次数',
    `last_studied_at` DATETIME DEFAULT NULL COMMENT '最近一次学习时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_user_id` (`user_id`),
    UNIQUE INDEX `idx_user_knowledge` (`user_id`, `knowledge_point_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识点掌握度表';

-- 错题记录表
CREATE TABLE IF NOT EXISTS `mistake` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `question_id` INT DEFAULT NULL COMMENT '关联题目ID',
    `question_content` TEXT DEFAULT NULL COMMENT '题目内容（冗余，便于离线查询）',
    `user_answer` TEXT DEFAULT NULL COMMENT '学生错误答案',
    `standard_answer` TEXT DEFAULT NULL COMMENT '标准答案',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '知识点名称',
    `difficulty` VARCHAR(32) NOT NULL DEFAULT 'easy' COMMENT '题目难度',
    `error_type` VARCHAR(32) DEFAULT NULL COMMENT 'knowledge/calculation/reading/method',
    `correction_status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'pending/corrected/review_due',
    `correction_answer` TEXT DEFAULT NULL COMMENT '订正答案',
    `correction_correct` TINYINT(1) DEFAULT NULL COMMENT '订正是否正确',
    `first_correction_success` TINYINT(1) DEFAULT 0 COMMENT '首次订正是否成功（是否已发放积分）',
    `correction_request_id` VARCHAR(128) DEFAULT NULL COMMENT '订正幂等标识',
    `corrected_at` DATETIME DEFAULT NULL COMMENT '订正完成时间',
    `next_review_at` DATETIME DEFAULT NULL COMMENT '下一次复习到期时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '错题生成时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_user_kp` (`user_id`, `knowledge_point_id`),
    INDEX `idx_correction_status` (`user_id`, `correction_status`),
    INDEX `idx_next_review` (`user_id`, `next_review_at`),
    UNIQUE INDEX `idx_correction_request` (`correction_request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错题记录表';

-- 复习计划表（订正成功后自动生成 1/3/7 天复习记录）
CREATE TABLE IF NOT EXISTS `review_plan` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `mistake_id` INT NOT NULL COMMENT '关联错题ID',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '知识点名称',
    `review_date` DATE NOT NULL COMMENT '复习日期',
    `status` VARCHAR(32) NOT NULL DEFAULT 'pending' COMMENT 'pending/completed',
    `reviewed_at` DATETIME DEFAULT NULL COMMENT '实际复习时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_user_review` (`user_id`, `review_date`),
    INDEX `idx_mistake_id` (`mistake_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='复习计划表';

INSERT IGNORE INTO schema_version(version, description)
VALUES ('004', '创建答题记录、知识点掌握度、错题和复习计划表');

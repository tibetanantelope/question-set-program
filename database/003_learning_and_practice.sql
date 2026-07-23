-- ============================================================
-- 成员二：智能诊断、练习生成与答题分析
-- 迁移编号: 003_learning_and_practice.sql
-- 创建时间: 2026-07-23
-- ============================================================

-- 学习会话表
CREATE TABLE IF NOT EXISTS `learning_session` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `session_key` VARCHAR(128) DEFAULT NULL COMMENT '会话标识（关联短期记忆）',
    `status` VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT 'active/completed/abandoned',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `completed_at` DATETIME DEFAULT NULL COMMENT '完成时间',
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学习会话表';

-- 学情诊断表
CREATE TABLE IF NOT EXISTS `diagnosis` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `session_id` INT DEFAULT NULL COMMENT '关联学习会话ID',
    `input_type` VARCHAR(32) NOT NULL COMMENT 'question/learning_question/weakness',
    `content` TEXT NOT NULL COMMENT '用户输入的题目、问题或薄弱点描述',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '识别出的知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '识别出的知识点名称',
    `mastery_score` INT DEFAULT 60 COMMENT '当前掌握度: 0-100',
    `learning_status` VARCHAR(32) DEFAULT 'consolidating' COMMENT 'weak/consolidating/mastered',
    `weakness` TEXT DEFAULT NULL COMMENT '薄弱点分析',
    `practice_suggestion` TEXT DEFAULT NULL COMMENT '建议练习方向',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学情诊断表';

-- 练习组表
CREATE TABLE IF NOT EXISTS `practice` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `diagnosis_id` INT DEFAULT NULL COMMENT '关联诊断ID',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '知识点名称',
    `difficulty` VARCHAR(32) NOT NULL DEFAULT 'easy' COMMENT 'easy/medium/hard',
    `status` VARCHAR(32) NOT NULL DEFAULT 'in_progress' COMMENT 'in_progress/completed',
    `question_count` INT NOT NULL DEFAULT 3 COMMENT '题目数量',
    `correct_count` INT DEFAULT 0 COMMENT '答对数量',
    `accuracy` FLOAT DEFAULT 0.0 COMMENT '正确率',
    `is_valid` TINYINT(1) DEFAULT 0 COMMENT '是否为有效练习（成功生成且提交）',
    `request_id` VARCHAR(128) DEFAULT NULL COMMENT '幂等标识',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `submitted_at` DATETIME DEFAULT NULL COMMENT '提交时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_diagnosis_id` (`diagnosis_id`),
    UNIQUE INDEX `idx_request_id` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='练习组表';

-- 题目表
CREATE TABLE IF NOT EXISTS `question` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `practice_id` INT NOT NULL COMMENT '关联练习组ID',
    `question_order` INT NOT NULL COMMENT '题目序号（组内）',
    `content` TEXT NOT NULL COMMENT '题目内容',
    `question_type` VARCHAR(32) NOT NULL DEFAULT 'short_answer' COMMENT '题型',
    `difficulty` VARCHAR(32) NOT NULL DEFAULT 'easy' COMMENT 'easy/medium/hard',
    `knowledge_point_id` INT DEFAULT NULL COMMENT '知识点ID',
    `knowledge_point_name` VARCHAR(128) DEFAULT NULL COMMENT '知识点名称',
    `standard_answer` TEXT DEFAULT NULL COMMENT '标准答案',
    `analysis` TEXT DEFAULT NULL COMMENT '基础解析',
    `user_answer` TEXT DEFAULT NULL COMMENT '学生答案',
    `is_correct` TINYINT(1) DEFAULT NULL COMMENT '判断结果',
    `error_type` VARCHAR(32) DEFAULT NULL COMMENT 'knowledge/calculation/reading/method',
    `error_description` TEXT DEFAULT NULL COMMENT '错因说明',
    `next_suggestion` TEXT DEFAULT NULL COMMENT '下一步建议',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `answered_at` DATETIME DEFAULT NULL COMMENT '答题时间',
    INDEX `idx_practice_id` (`practice_id`),
    INDEX `idx_practice_order` (`practice_id`, `question_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目表';

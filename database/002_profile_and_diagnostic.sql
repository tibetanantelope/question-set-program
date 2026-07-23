-- 智学伴 002: 用户画像扩展、首次诊断表
-- 依赖: 001_initial.sql（user 表和 user_profile 基础表已存在）

-- ============================================================
-- 1. 扩展 user_profile 表
-- ============================================================

-- MySQL 8 不支持 ADD COLUMN IF NOT EXISTS，使用存储过程安全添加
-- 仅添加不存在的列，已存在则跳过

-- 添加 stage（学段）
SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user_profile ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT "" COMMENT ''学段: primary/junior/senior/university'' AFTER subject;',
    'SELECT "column stage already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profile' AND COLUMN_NAME = 'stage');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 添加 learning_goal（学习目标）
SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user_profile ADD COLUMN learning_goal VARCHAR(32) NOT NULL DEFAULT "" COMMENT ''学习目标: daily/weakness/exam'' AFTER stage;',
    'SELECT "column learning_goal already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profile' AND COLUMN_NAME = 'learning_goal');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 添加 weekly_study_days（每周学习天数）
SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user_profile ADD COLUMN weekly_study_days INT NOT NULL DEFAULT 5 COMMENT ''每周学习天数: 1-7'' AFTER learning_goal;',
    'SELECT "column weekly_study_days already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profile' AND COLUMN_NAME = 'weekly_study_days');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 添加 daily_target_groups（每日目标练习组数）
SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user_profile ADD COLUMN daily_target_groups INT NOT NULL DEFAULT 3 COMMENT ''每日目标练习组数: 1-5'' AFTER weekly_study_days;',
    'SELECT "column daily_target_groups already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profile' AND COLUMN_NAME = 'daily_target_groups');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 添加 diagnostic_status（首次诊断状态）
SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user_profile ADD COLUMN diagnostic_status VARCHAR(32) NOT NULL DEFAULT ''required'' COMMENT ''诊断状态: required/in_progress/completed/skipped'' AFTER daily_target_groups;',
    'SELECT "column diagnostic_status already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_profile' AND COLUMN_NAME = 'diagnostic_status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ============================================================
-- 2. 首次诊断会话表
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnostic_session (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress' COMMENT 'in_progress/completed/skipped',
    question_count INT NOT NULL DEFAULT 5 COMMENT '诊断题目数量',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME DEFAULT NULL,
    CONSTRAINT fk_diag_user FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    INDEX idx_diag_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 3. 首次诊断答题记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS diagnostic_answer (
    id INT PRIMARY KEY AUTO_INCREMENT,
    diagnostic_id INT NOT NULL,
    question_id INT NOT NULL COMMENT '题目编号（诊断会话内自增）',
    content TEXT NOT NULL COMMENT '题目内容',
    question_type VARCHAR(32) NOT NULL DEFAULT 'short_answer' COMMENT '题型',
    difficulty VARCHAR(32) NOT NULL DEFAULT 'easy' COMMENT '难度: easy/medium/hard',
    knowledge_point_id INT DEFAULT NULL,
    knowledge_point_name VARCHAR(128) DEFAULT NULL,
    user_answer TEXT DEFAULT NULL COMMENT '学生答案',
    is_correct BOOLEAN DEFAULT NULL COMMENT '判题结果',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_diag_answer FOREIGN KEY (diagnostic_id) REFERENCES diagnostic_session(id) ON DELETE CASCADE,
    INDEX idx_diag_ans (diagnostic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 4. 记录版本
-- ============================================================

INSERT IGNORE INTO schema_version(version, description)
VALUES ('002', '扩展用户画像字段，创建首次诊断会话和答题记录表');

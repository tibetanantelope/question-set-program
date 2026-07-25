-- 成员二/三跨模块表 + user_profile 字段扩展
-- 供成员四（学习记录/报告/推荐/提醒）使用
-- 已有数据库重复执行不会清空数据（使用 IF NOT EXISTS 和 COLUMN_CHECK）

-- 错题表（成员三写入）
CREATE TABLE IF NOT EXISTS mistake (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    knowledge_point_name VARCHAR(200) DEFAULT NULL,
    error_type VARCHAR(20) DEFAULT NULL COMMENT 'knowledge/calculation/reading/method',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mistake_user (user_id),
    INDEX idx_mistake_created (user_id, created_at),
    CONSTRAINT fk_mistake_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 复习计划表（成员三写入）
CREATE TABLE IF NOT EXISTS review_plan (
    id INT PRIMARY KEY AUTO_INCREMENT,
    mistake_id INT NOT NULL,
    user_id INT NOT NULL,
    review_date DATE NOT NULL,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rp_user_date (user_id, review_date),
    INDEX idx_rp_mistake (mistake_id),
    CONSTRAINT fk_rp_mistake
        FOREIGN KEY (mistake_id) REFERENCES mistake(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rp_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 知识点掌握度表（成员二写入）
CREATE TABLE IF NOT EXISTS knowledge_mastery (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    knowledge_point_name VARCHAR(200) NOT NULL,
    mastery_score INT DEFAULT 0 COMMENT '0-100 掌握度分数',
    last_studied_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_km_user (user_id),
    INDEX idx_km_score (user_id, mastery_score),
    CONSTRAINT fk_km_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- user_profile 新增字段（如果列不存在则添加）
-- 注意：存储过程方式兼容性更好；如果已存在会跳过
SET @sql_goal = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_profile ADD COLUMN learning_goal VARCHAR(32) DEFAULT ''daily'' COMMENT ''学习目标: daily/weakness/exam'' AFTER preferences',
        'SELECT ''learning_goal already exists'' AS msg'
    )
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_profile'
      AND COLUMN_NAME = 'learning_goal'
);
PREPARE stmt_goal FROM @sql_goal; EXECUTE stmt_goal; DEALLOCATE PREPARE stmt_goal;

SET @sql_target = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE user_profile ADD COLUMN daily_target_groups INT DEFAULT 3 COMMENT ''每日目标练习组数'' AFTER learning_goal',
        'SELECT ''daily_target_groups already exists'' AS msg'
    )
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_profile'
      AND COLUMN_NAME = 'daily_target_groups'
);
PREPARE stmt_target FROM @sql_target; EXECUTE stmt_target; DEALLOCATE PREPARE stmt_target;

INSERT IGNORE INTO schema_version(version, description)
VALUES ('006', '跨模块表（错题/复习/掌握度）+ user_profile 扩展字段');

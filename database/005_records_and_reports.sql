-- 成员四：学习记录、首页推荐、学习报告与提醒
-- 数据表：learning_record、daily_plan、notification、learning_report

CREATE TABLE IF NOT EXISTS learning_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    record_type VARCHAR(20) NOT NULL COMMENT 'diagnosis/practice/correction/review/report',
    title VARCHAR(200) NOT NULL,
    subject VARCHAR(32) DEFAULT NULL,
    knowledge_point_name VARCHAR(200) DEFAULT NULL,
    question_count INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT NULL,
    mastery_change INT DEFAULT 0,
    request_id VARCHAR(64) DEFAULT NULL,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_record_user (user_id),
    INDEX idx_record_type (record_type),
    INDEX idx_record_subject (subject),
    INDEX idx_record_occurred (user_id, occurred_at),
    UNIQUE INDEX idx_record_request (request_id),
    CONSTRAINT fk_record_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS daily_plan (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    plan_date DATE NOT NULL,
    target_groups INT NOT NULL DEFAULT 3,
    completed_groups INT NOT NULL DEFAULT 0,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_plan_user_date (user_id, plan_date),
    CONSTRAINT fk_plan_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notification (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    type VARCHAR(20) NOT NULL COMMENT 'review_due/daily_plan/vip_expiring',
    title VARCHAR(200) NOT NULL,
    content VARCHAR(500) DEFAULT NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notify_user (user_id, is_read),
    CONSTRAINT fk_notify_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_report (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    practice_count INT NOT NULL DEFAULT 0,
    question_count INT NOT NULL DEFAULT 0,
    accuracy DECIMAL(5,2) DEFAULT NULL,
    mastery_change INT DEFAULT 0,
    frequent_error_type VARCHAR(20) DEFAULT NULL COMMENT 'knowledge/calculation/reading/method',
    weak_points JSON DEFAULT NULL,
    suggestion VARCHAR(500) DEFAULT NULL,
    request_id VARCHAR(64) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_report_user (user_id),
    UNIQUE INDEX idx_report_request (request_id),
    CONSTRAINT fk_report_user
        FOREIGN KEY (user_id) REFERENCES `user`(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO schema_version(version, description)
VALUES ('005', '成员四：学习记录、每日计划、站内提醒、学情报告');

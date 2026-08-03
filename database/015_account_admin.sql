-- 015: 用户角色、状态与管理员操作审计表

-- 1. user 表新增 role 和 status 字段

SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT ''user'' COMMENT ''角色: user/admin'' AFTER password;',
    'SELECT "column role already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user' AND COLUMN_NAME = 'role');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @sql = (SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE user ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT ''active'' COMMENT ''状态: active/disabled'' AFTER role;',
    'SELECT "column status already exists" AS msg'
) FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user' AND COLUMN_NAME = 'status');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 2. 管理员操作审计日志表

CREATE TABLE IF NOT EXISTS admin_audit (
    id INT PRIMARY KEY AUTO_INCREMENT,
    admin_id INT NOT NULL COMMENT '操作管理员ID',
    admin_username VARCHAR(20) NOT NULL COMMENT '操作管理员用户名',
    action VARCHAR(64) NOT NULL COMMENT '操作类型: login/logout/disable_user/restore_user/view_users/view_user_detail',
    target_type VARCHAR(32) DEFAULT NULL COMMENT '操作对象类型: user',
    target_id INT DEFAULT NULL COMMENT '操作对象ID',
    detail TEXT DEFAULT NULL COMMENT '操作详情（JSON）',
    ip_address VARCHAR(64) DEFAULT NULL COMMENT '操作IP',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_admin (admin_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. 更新 schema_version

INSERT IGNORE INTO schema_version(version, description)
VALUES ('015', '用户新增 role/status 字段，创建管理审计日志表');

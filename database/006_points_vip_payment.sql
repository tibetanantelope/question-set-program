-- 成员五：积分、使用次数、VIP 与支付订单。
-- 可重复执行建表语句，不会删除或清空已有业务数据。

CREATE TABLE IF NOT EXISTS point_account (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    balance INT NOT NULL DEFAULT 0,
    earned_total INT NOT NULL DEFAULT 0,
    spent_total INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_point_account_user UNIQUE (user_id),
    CONSTRAINT ck_point_account_balance CHECK (balance >= 0),
    CONSTRAINT ck_point_account_earned_total CHECK (earned_total >= 0),
    CONSTRAINT ck_point_account_spent_total CHECK (spent_total >= 0),
    CONSTRAINT fk_point_account_user
        FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS point_transaction (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    account_id BIGINT NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    business_type VARCHAR(32) NOT NULL,
    business_id VARCHAR(64) NULL,
    change_amount INT NOT NULL,
    balance_after INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_point_transaction_request UNIQUE (request_id),
    CONSTRAINT uq_point_transaction_business UNIQUE (user_id, business_type, business_id),
    CONSTRAINT ck_point_transaction_change CHECK (change_amount <> 0),
    CONSTRAINT ck_point_transaction_balance CHECK (balance_after >= 0),
    CONSTRAINT fk_point_transaction_user
        FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    CONSTRAINT fk_point_transaction_account
        FOREIGN KEY (account_id) REFERENCES point_account(id) ON DELETE CASCADE,
    INDEX idx_point_transaction_user_created (user_id, created_at),
    INDEX idx_point_transaction_business_type (business_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS usage_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    usage_date DATE NOT NULL,
    feature VARCHAR(32) NOT NULL,
    usage_source VARCHAR(16) NOT NULL DEFAULT 'quota',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_usage_record_request UNIQUE (request_id),
    CONSTRAINT fk_usage_record_user
        FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    INDEX idx_usage_record_daily_feature (user_id, usage_date, feature),
    INDEX idx_usage_record_source (usage_source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vip_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    started_at DATETIME NULL,
    expires_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_vip_info_user UNIQUE (user_id),
    CONSTRAINT ck_vip_info_period CHECK (
        started_at IS NULL OR expires_at IS NULL OR expires_at > started_at
    ),
    CONSTRAINT fk_vip_info_user
        FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    INDEX idx_vip_info_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payment_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) NOT NULL,
    user_id INT NOT NULL,
    request_id VARCHAR(64) NOT NULL,
    plan VARCHAR(32) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    alipay_trade_no VARCHAR(64) NULL,
    paid_at DATETIME NULL,
    vip_applied_at DATETIME NULL,
    closed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_payment_order_no UNIQUE (order_no),
    CONSTRAINT uq_payment_order_request UNIQUE (request_id),
    CONSTRAINT uq_payment_order_alipay_trade UNIQUE (alipay_trade_no),
    CONSTRAINT ck_payment_order_amount CHECK (amount > 0),
    CONSTRAINT fk_payment_order_user
        FOREIGN KEY (user_id) REFERENCES `user`(id) ON DELETE CASCADE,
    INDEX idx_payment_order_user_created (user_id, created_at),
    INDEX idx_payment_order_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO schema_version(version, description)
VALUES ('006', '创建积分、次数、VIP和支付订单表');

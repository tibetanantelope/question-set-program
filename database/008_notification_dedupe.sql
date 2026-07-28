-- 第五批：站内提醒增加幂等键，避免轮询未读数时重复生成同一天的提醒。

ALTER TABLE notification
    ADD COLUMN dedupe_key VARCHAR(100) NULL COMMENT '同一用户的提醒幂等键' AFTER content,
    ADD UNIQUE KEY uq_notification_user_dedupe (user_id, dedupe_key);

INSERT IGNORE INTO schema_version (version, description)
VALUES ('008', 'add notification dedupe key');

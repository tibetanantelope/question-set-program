-- 第二批：为答案提交增加独立幂等键。
-- 练习生成和答案提交是两次不同写操作，不能共用同一个 request_id。

ALTER TABLE practice
    ADD COLUMN answer_request_id VARCHAR(64) NULL COMMENT '提交答案幂等标识' AFTER request_id,
    ADD UNIQUE KEY uq_practice_answer_request_id (answer_request_id);

INSERT IGNORE INTO schema_version (version, description)
VALUES ('007', 'add practice answer submission idempotency key');

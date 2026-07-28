-- 为练习、答题和错题补齐“发生当时的学科”快照。
-- 历史行保持 NULL：不能用用户当前学科反推过去，否则切换学科后会产生错误分类。

ALTER TABLE practice
    ADD COLUMN subject VARCHAR(32) NULL COMMENT '生成练习时的学科快照' AFTER knowledge_point_name,
    ADD INDEX idx_practice_subject (subject);

ALTER TABLE answer_record
    ADD COLUMN subject VARCHAR(32) NULL COMMENT '答题时的学科快照' AFTER knowledge_point_name,
    ADD INDEX idx_answer_subject (subject);

ALTER TABLE mistake
    ADD COLUMN subject VARCHAR(32) NULL COMMENT '答题时的学科快照' AFTER knowledge_point_name,
    ADD INDEX idx_mistake_subject (subject);

INSERT IGNORE INTO schema_version(version, description)
VALUES ('011', '保存练习、答题和错题的学科历史快照');

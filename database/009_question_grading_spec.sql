-- 混合智能判题：为每道题保存答案类型和结构化评分标准。

ALTER TABLE question
    ADD COLUMN answer_type VARCHAR(32) NOT NULL DEFAULT 'short_text'
        COMMENT 'numeric/symbolic/set/proof/code/short_text' AFTER standard_answer,
    ADD COLUMN grading_spec JSON NULL COMMENT '结构化评分标准' AFTER answer_type;

INSERT IGNORE INTO schema_version (version, description)
VALUES ('009', 'add structured question grading specification');

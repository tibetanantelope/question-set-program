-- ============================================================
-- 成员三（第二阶段）：题库题来源链接
-- 迁移编号: 017_question_source_link.sql
-- 创建时间: 2026-08-05
-- ============================================================
-- 练习落库的题目若来自题库原题，记录 source_question_id，
-- 使答题统计能反查并更新到题库原题的使用次数/正确率。
-- ============================================================

ALTER TABLE question ADD COLUMN source_question_id INT NULL COMMENT '来源题库题ID（练习落库时记录，用于统计反查）' AFTER practice_id;

-- 已有练习生成的题库题：按内容精确匹配反填（尽力而为，不影响新数据）
UPDATE question q
JOIN question bank
  ON q.source_question_id IS NULL
 AND q.practice_id IS NOT NULL
 AND bank.practice_id IS NULL
 AND q.content = bank.content
 AND q.knowledge_point_name = bank.knowledge_point_name
SET q.source_question_id = bank.id;

CREATE INDEX idx_question_source ON question(source_question_id);

INSERT IGNORE INTO schema_version(version, description)
VALUES ('017', '题目增加来源题库题ID，用于答题统计反查');

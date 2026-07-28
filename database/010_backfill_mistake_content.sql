-- 补齐历史错题快照；仅更新内容为空且能关联到原题的记录。

UPDATE mistake AS m
INNER JOIN question AS q ON q.id = m.question_id
SET
    m.question_content = CASE
        WHEN m.question_content IS NULL OR m.question_content = '' THEN q.content
        ELSE m.question_content
    END,
    m.user_answer = CASE
        WHEN m.user_answer IS NULL OR m.user_answer = '' THEN q.user_answer
        ELSE m.user_answer
    END,
    m.standard_answer = CASE
        WHEN m.standard_answer IS NULL OR m.standard_answer = '' THEN q.standard_answer
        ELSE m.standard_answer
    END
WHERE
    m.question_content IS NULL OR m.question_content = ''
    OR m.user_answer IS NULL OR m.user_answer = ''
    OR m.standard_answer IS NULL OR m.standard_answer = '';

INSERT IGNORE INTO schema_version (version, description)
VALUES ('010', 'backfill historical mistake question and answer snapshots');

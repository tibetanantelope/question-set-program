-- 将 user_id=1 在 2026-07-26 产生的“综合知识点”遗留数据回填为真实知识点。
-- 同步更新完整业务链，避免画像、错题、记录和报告之间名称不一致。

START TRANSACTION;

UPDATE diagnosis
SET knowledge_point_name = CASE id
    WHEN 25 THEN '运算顺序与括号'
    WHEN 27 THEN '现在完成时'
    WHEN 28 THEN '主将从现'
END
WHERE user_id = 1 AND id IN (25, 27, 28) AND knowledge_point_name = '综合知识点';

UPDATE practice
SET knowledge_point_name = CASE id
    WHEN 16 THEN '运算顺序与括号'
    WHEN 19 THEN '现在完成时'
    WHEN 20 THEN '主将从现'
    WHEN 21 THEN '主将从现'
    WHEN 22 THEN '主将从现'
END
WHERE user_id = 1 AND id IN (16, 19, 20, 21, 22) AND knowledge_point_name = '综合知识点';

UPDATE question
SET knowledge_point_name = CASE
    WHEN practice_id = 16 THEN '运算顺序与括号'
    WHEN practice_id = 19 THEN '现在完成时'
    WHEN practice_id IN (20, 21, 22) THEN '主将从现'
END
WHERE practice_id IN (16, 19, 20, 21, 22) AND knowledge_point_name = '综合知识点';

UPDATE mistake
SET knowledge_point_name = CASE
    WHEN knowledge_point_id = 238 THEN '运算顺序与括号'
    WHEN knowledge_point_id = 2074 THEN '现在完成时'
    WHEN knowledge_point_id = 8730 THEN '主将从现'
END
WHERE user_id = 1
  AND knowledge_point_id IN (238, 2074, 8730)
  AND knowledge_point_name = '综合知识点';

UPDATE knowledge_mastery
SET knowledge_point_name = CASE knowledge_point_id
    WHEN 238 THEN '运算顺序与括号'
    WHEN 2074 THEN '现在完成时'
    WHEN 8730 THEN '主将从现'
END
WHERE user_id = 1
  AND knowledge_point_id IN (238, 2074, 8730)
  AND knowledge_point_name = '综合知识点';

UPDATE learning_record
SET knowledge_point_name = CASE
        WHEN subject = '数学' THEN '运算顺序与括号'
        WHEN subject = '英语' AND occurred_at < '2026-07-26 20:00:00' THEN '现在完成时'
        WHEN subject = '英语' THEN '主将从现'
    END,
    title = CASE
        WHEN record_type = 'correction' THEN '错题订正 - 主将从现'
        WHEN subject = '数学' THEN '运算顺序与括号'
        WHEN subject = '英语' AND occurred_at < '2026-07-26 20:00:00' THEN '现在完成时'
        WHEN subject = '英语' THEN '主将从现'
    END
WHERE user_id = 1 AND knowledge_point_name = '综合知识点';

UPDATE learning_report
SET weak_points = JSON_ARRAY('运算顺序与括号', '现在完成时'),
    suggestion = '优先修复运算顺序与括号、现在完成时两个薄弱点；主将从现已具备基础，但需要继续降低知识性错误。'
WHERE user_id = 1
  AND JSON_SEARCH(weak_points, 'one', '综合知识点') IS NOT NULL;

-- 报告列表中的摘要也改为仅统计首次练习，订正次数在新版详情中单独展示。
UPDATE learning_report lr
JOIN (
    SELECT lr2.id,
           COUNT(rec.id) AS practice_count,
           COALESCE(SUM(rec.question_count), 0) AS question_count,
           COALESCE(
               ROUND(SUM(rec.correct_count) * 100 / NULLIF(SUM(rec.question_count), 0), 2),
               0
           ) AS accuracy
    FROM learning_report lr2
    LEFT JOIN learning_record rec
      ON rec.user_id = lr2.user_id
     AND rec.record_type = 'practice'
     AND rec.occurred_at BETWEEN CONCAT(lr2.date_from, ' 00:00:00')
                             AND CONCAT(lr2.date_to, ' 23:59:59')
    WHERE lr2.user_id = 1
    GROUP BY lr2.id
) calculated ON calculated.id = lr.id
SET lr.practice_count = calculated.practice_count,
    lr.question_count = calculated.question_count,
    lr.accuracy = calculated.accuracy;

COMMIT;

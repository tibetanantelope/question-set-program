-- ============================================================
-- 成员三（第二阶段）：题目题库管理
-- 迁移编号: 016_question_bank.sql
-- 创建时间: 2026-08-05
-- ============================================================
-- 扩展 question 表支持独立题库 + 新建知识点表
-- 注意：已执行的列会报 Duplicate column 错，属正常情况，可忽略。
-- ============================================================

ALTER TABLE question MODIFY practice_id INT NULL COMMENT '关联练习组ID（题库独立时可为空）';
ALTER TABLE question ADD COLUMN subject VARCHAR(32) NULL COMMENT '学科快照' AFTER practice_id;
ALTER TABLE question ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'approved' COMMENT '审核状态: draft/pending/approved/rejected' AFTER subject;
ALTER TABLE question ADD COLUMN review_status VARCHAR(32) NOT NULL DEFAULT 'published' COMMENT '上架状态: published/off_shelf' AFTER status;
ALTER TABLE question ADD COLUMN options JSON NULL COMMENT '选择题选项（仅choice题型）' AFTER standard_answer;
ALTER TABLE question ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'builtin' COMMENT '来源: builtin/admin/llm' AFTER options;
ALTER TABLE question ADD COLUMN usage_count INT NOT NULL DEFAULT 0 COMMENT '被练习使用次数' AFTER source;
ALTER TABLE question ADD COLUMN total_correct INT NOT NULL DEFAULT 0 COMMENT '累计答对次数' AFTER usage_count;
ALTER TABLE question ADD COLUMN created_by INT NULL COMMENT '录入管理员ID' AFTER total_correct;
ALTER TABLE question ADD COLUMN reviewed_by INT NULL COMMENT '审核管理员ID' AFTER created_by;
ALTER TABLE question ADD COLUMN reviewed_at DATETIME NULL COMMENT '审核时间' AFTER reviewed_by;

ALTER TABLE question MODIFY question_order INT NULL COMMENT '题目序号（组内，题库独立时可空）';

UPDATE question SET status = 'approved', review_status = 'published', source = 'builtin'
WHERE status = '' OR status IS NULL;

CREATE TABLE IF NOT EXISTS `knowledge_point` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键',
    `name` VARCHAR(128) NOT NULL COMMENT '知识点名称',
    `subject` VARCHAR(32) NOT NULL DEFAULT '数学' COMMENT '所属学科',
    `grade_range` VARCHAR(64) NULL COMMENT '适用年级范围，如 七年级,八年级',
    `parent_id` INT NULL COMMENT '父知识点ID（树形结构）',
    `description` TEXT NULL COMMENT '知识点说明',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_subject` (`subject`),
    INDEX `idx_parent` (`parent_id`),
    UNIQUE INDEX `idx_name_subject` (`name`, `subject`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识点表';

INSERT IGNORE INTO knowledge_point (name, subject, grade_range) VALUES
('有理数加减法', '数学', '七年级'),
('有理数乘除法', '数学', '七年级'),
('整式的加减', '数学', '七年级'),
('去括号法则', '数学', '七年级'),
('一元一次方程', '数学', '七年级'),
('一元一次方程-移项', '数学', '七年级'),
('二元一次方程组', '数学', '七年级'),
('不等式与不等式组', '数学', '七年级'),
('平面直角坐标系', '数学', '七年级'),
('三角形基础', '数学', '八年级'),
('全等三角形', '数学', '八年级'),
('因式分解', '数学', '八年级'),
('分式运算', '数学', '八年级'),
('勾股定理', '数学', '八年级'),
('一次函数', '数学', '八年级'),
('二次函数', '数学', '九年级'),
('相似三角形', '数学', '九年级'),
('锐角三角函数', '数学', '九年级'),
('圆的有关性质', '数学', '九年级');

INSERT IGNORE INTO schema_version(version, description)
VALUES ('016', '题目题库化扩展：独立题目字段、知识点表、种子数据');

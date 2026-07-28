CREATE TABLE IF NOT EXISTS knowledge_review_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    subject VARCHAR(32) NULL,
    knowledge_point_name VARCHAR(128) NOT NULL,
    review_mode VARCHAR(20) NOT NULL DEFAULT 'full',
    quiz_score INT NOT NULL DEFAULT 0,
    quiz_total INT NOT NULL DEFAULT 0,
    answers JSON NULL,
    request_id VARCHAR(128) NOT NULL,
    completed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_knowledge_review_request (request_id),
    KEY idx_knowledge_review_user_time (user_id, completed_at),
    KEY idx_knowledge_review_user_kp (user_id, knowledge_point_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识点概念复习与自测记录';

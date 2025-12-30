-- =========================================================
-- AI 学习社区 - 高级仿真数据生成 (带时间流逝逻辑)
-- =========================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 重建表结构
-- ----------------------------
DROP TABLE IF EXISTS `comments`;
DROP TABLE IF EXISTS `posts`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_deleted TINYINT(1) DEFAULT 0,
    view_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE comments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    parent_id BIGINT DEFAULT NULL,
    root_id BIGINT DEFAULT NULL,
    reply_to_user_id BIGINT DEFAULT NULL,
    content TEXT NOT NULL,
    is_deleted TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_post_root (post_id, root_id),
    INDEX idx_root (root_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------
-- 2. 数据生成存储过程 (核心逻辑优化)
-- ----------------------------
DROP PROCEDURE IF EXISTS `GenerateMockData`;

DELIMITER $$

CREATE PROCEDURE `GenerateMockData`()
BEGIN
    -- 循环变量
    DECLARE i INT DEFAULT 1;
    DECLARE j INT DEFAULT 1;
    DECLARE k INT DEFAULT 1;
    
    -- ID 缓存变量
    DECLARE v_user_id BIGINT;
    DECLARE v_post_id BIGINT;
    DECLARE v_comment_id BIGINT;
    DECLARE v_root_id BIGINT;
    DECLARE v_parent_id BIGINT;
    DECLARE v_reply_to_uid BIGINT;
    
    -- 内容与状态变量
    DECLARE v_comment_count INT;
    DECLARE v_is_deleted INT;
    DECLARE v_is_root BOOLEAN;
    DECLARE v_content TEXT;
    
    -- 时间控制变量 (核心)
    DECLARE v_base_time DATETIME DEFAULT '2024-01-01 00:00:00'; -- 时间起点
    DECLARE v_user_reg_time DATETIME;
    DECLARE v_post_time DATETIME;
    DECLARE v_comment_time DATETIME;

    -- ===================================
    -- 第一步：生成 20 个用户 (分布在 2024 前半年)
    -- ===================================
    SET i = 1;
    WHILE i <= 20 DO
        -- 用户注册时间：基准时间 + 0~180天内的随机时间
        SET v_user_reg_time = DATE_ADD(v_base_time, INTERVAL FLOOR(RAND() * 180) DAY);
        
        INSERT INTO users (username, avatar_url, created_at) 
        VALUES (
            CONCAT('User_', i), 
            CONCAT('https://api.dicebear.com/7.x/avataaars/svg?seed=User_', i),
            v_user_reg_time
        );
        SET i = i + 1;
    END WHILE;

    -- ===================================
    -- 第二步：生成 50 个帖子 (分布在 2024下半年 ~ 2025)
    -- ===================================
    SET j = 1;
    WHILE j <= 50 DO
        SET v_user_id = FLOOR(1 + (RAND() * 20));
        
        -- 获取该作者的注册时间，保证发帖晚于注册
        SELECT created_at INTO v_user_reg_time FROM users WHERE id = v_user_id;
        
        -- 发帖时间：注册时间 + 1~400天随机 (跨度拉大)
        SET v_post_time = DATE_ADD(v_user_reg_time, INTERVAL FLOOR(1 + RAND() * 400) DAY);
        
        SET v_comment_count = FLOOR(50 + (RAND() * 51)); -- 50-100条评论
        
        INSERT INTO posts (user_id, title, content, view_count, comment_count, created_at, updated_at) 
        VALUES (
            v_user_id, 
            CONCAT('Topic_', j, ': Vue3与AI结合的技术探讨'), 
            CONCAT('这是帖子 ', j, ' 的内容。时间戳测试：', v_post_time),
            FLOOR(100 + (RAND() * 5000)),
            v_comment_count,
            v_post_time,
            v_post_time
        );
        
        SET v_post_id = LAST_INSERT_ID();

        -- ===================================
        -- 第三步：生成评论 (时间随楼层递增)
        -- ===================================
        SET k = 1;
        -- 初始化第一条评论的时间 = 帖子时间 + 随机 1~60 分钟
        SET v_comment_time = DATE_ADD(v_post_time, INTERVAL FLOOR(1 + RAND() * 60) MINUTE);

        WHILE k <= v_comment_count DO
            SET v_user_id = FLOOR(1 + (RAND() * 20));
            SET v_is_deleted = IF(RAND() < 0.05, 1, 0); 

            -- 时间流逝算法：每一层楼，时间向后推移 10分钟 ~ 10小时 不等
            -- 这样楼层越高，时间越晚，符合逻辑
            SET v_comment_time = DATE_ADD(v_comment_time, INTERVAL FLOOR(10 + RAND() * 600) MINUTE);

            -- 逻辑判断：根评论还是回复
            IF k <= 3 OR RAND() < 0.3 THEN
                SET v_is_root = TRUE;
            ELSE
                SET v_is_root = FALSE;
            END IF;

            IF v_is_root THEN
                -- 根评论
                IF v_is_deleted THEN SET v_content = '该评论已删除'; ELSE SET v_content = CONCAT('这是根评论 #', k, ' 时间:', DATE_FORMAT(v_comment_time, '%m-%d %H:%i')); END IF;
                
                INSERT INTO comments (post_id, user_id, parent_id, root_id, reply_to_user_id, content, is_deleted, created_at)
                VALUES (v_post_id, v_user_id, NULL, NULL, NULL, v_content, v_is_deleted, v_comment_time);
                
                SET v_comment_id = LAST_INSERT_ID();
                UPDATE comments SET root_id = v_comment_id WHERE id = v_comment_id;
            ELSE
                -- 子回复
                -- 随机找一个根
                SELECT id INTO v_root_id FROM comments WHERE post_id = v_post_id AND parent_id IS NULL ORDER BY RAND() LIMIT 1;
                
                IF v_root_id IS NOT NULL THEN
                     SET v_parent_id = v_root_id; -- 简化：直接挂在根下面
                     SELECT user_id INTO v_reply_to_uid FROM comments WHERE id = v_parent_id;
                     
                     IF v_is_deleted THEN SET v_content = '该评论已删除'; ELSE SET v_content = CONCAT('回复 #', v_root_id, ' 楼中楼 时间:', DATE_FORMAT(v_comment_time, '%m-%d %H:%i')); END IF;

                     INSERT INTO comments (post_id, user_id, parent_id, root_id, reply_to_user_id, content, is_deleted, created_at)
                     VALUES (v_post_id, v_user_id, v_parent_id, v_root_id, v_reply_to_uid, v_content, v_is_deleted, v_comment_time);
                END IF;
            END IF;

            SET k = k + 1;
        END WHILE;

        SET j = j + 1;
    END WHILE;
END$$

DELIMITER ;

-- ----------------------------
-- 3. 执行生成
-- ----------------------------
CALL GenerateMockData();
DROP PROCEDURE GenerateMockData;
SET FOREIGN_KEY_CHECKS = 1;
-- =========================================================
-- AI 学习社区 - 全自动测试数据生成脚本
-- 包含：重置表结构 + 生成 20用户 + 50帖子 + ~3500条评论
-- =========================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 重置表结构 (使用你提供的 Schema)
-- ----------------------------
DROP TABLE IF EXISTS `comments`;
DROP TABLE IF EXISTS `posts`;
DROP TABLE IF EXISTS `users`;

-- 用户表
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL COMMENT '用户名',
    avatar_url VARCHAR(255) COMMENT '头像URL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户基本信息表';

-- 帖子表
CREATE TABLE posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL COMMENT '作者ID',
    title VARCHAR(100) NOT NULL COMMENT '帖子标题',
    content TEXT NOT NULL COMMENT '帖子内容',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
    view_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='帖子主表';

-- 评论表
CREATE TABLE comments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT NOT NULL COMMENT '归属的帖子ID',
    user_id BIGINT NOT NULL COMMENT '评论发布者ID',
    parent_id BIGINT DEFAULT NULL COMMENT '父评论ID',
    root_id BIGINT DEFAULT NULL COMMENT '根评论ID',
    reply_to_user_id BIGINT DEFAULT NULL COMMENT '被回复的用户ID',
    content TEXT NOT NULL COMMENT '评论内容',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_post_root (post_id, root_id),
    INDEX idx_root (root_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论表';

-- ----------------------------
-- 2. 定义数据生成存储过程
-- ----------------------------
DROP PROCEDURE IF EXISTS `GenerateMockData`;

DELIMITER $$

CREATE PROCEDURE `GenerateMockData`()
BEGIN
    -- 变量定义
    DECLARE i INT DEFAULT 1;
    DECLARE j INT DEFAULT 1;
    DECLARE k INT DEFAULT 1;
    
    DECLARE v_user_id BIGINT;
    DECLARE v_post_id BIGINT;
    DECLARE v_comment_id BIGINT;
    DECLARE v_root_id BIGINT;
    DECLARE v_parent_id BIGINT;
    DECLARE v_reply_to_uid BIGINT;
    
    DECLARE v_comment_count INT;
    DECLARE v_is_deleted INT;
    DECLARE v_is_root BOOLEAN;
    DECLARE v_content TEXT;
    
    -- ===================================
    -- 第一步：生成 20 个用户
    -- ===================================
    SET i = 1;
    WHILE i <= 20 DO
        INSERT INTO users (username, avatar_url) 
        VALUES (
            CONCAT('User_', i), 
            CONCAT('https://api.dicebear.com/7.x/avataaars/svg?seed=User_', i)
        );
        SET i = i + 1;
    END WHILE;

    -- ===================================
    -- 第二步：生成 50 个帖子
    -- ===================================
    SET j = 1;
    WHILE j <= 50 DO
        -- 随机作者 (1-20)
        SET v_user_id = FLOOR(1 + (RAND() * 20));
        
        -- 随机评论数 (50-100)
        SET v_comment_count = FLOOR(50 + (RAND() * 51));
        
        -- 插入帖子
        INSERT INTO posts (user_id, title, content, view_count, comment_count, created_at) 
        VALUES (
            v_user_id, 
            CONCAT('关于 AI 学习社区的第 ', j, ' 个讨论'), 
            CONCAT('这是第 ', j, ' 个帖子的正文内容。大家在使用 Vue3 和 FastAPI 开发过程中遇到了什么坑吗？欢迎讨论！'),
            FLOOR(100 + (RAND() * 5000)), -- 随机浏览量
            v_comment_count,
            DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY) -- 随机最近30天
        );
        
        SET v_post_id = LAST_INSERT_ID();

        -- ===================================
        -- 第三步：为该帖子生成 50-100 条评论
        -- ===================================
        SET k = 1;
        WHILE k <= v_comment_count DO
            -- 随机评论者
            SET v_user_id = FLOOR(1 + (RAND() * 20));
            -- 5% 概率已删除
            SET v_is_deleted = IF(RAND() < 0.05, 1, 0); 
            
            -- 决定是根评论(30%) 还是 子回复(70%)
            -- 如果是该帖子的前3条，强制设为根评论，确保有根可回
            IF k <= 3 OR RAND() < 0.3 THEN
                SET v_is_root = TRUE;
            ELSE
                SET v_is_root = FALSE;
            END IF;

            IF v_is_root THEN
                -- === 插入根评论 ===
                IF v_is_deleted THEN SET v_content = '该评论已删除'; ELSE SET v_content = '大佬说得对，受教了！(根评论)'; END IF;
                
                -- 先插入，parent_id=NULL, root_id 先设为 NULL (稍后更新)
                INSERT INTO comments (post_id, user_id, parent_id, root_id, reply_to_user_id, content, is_deleted)
                VALUES (v_post_id, v_user_id, NULL, NULL, NULL, v_content, v_is_deleted);
                
                -- 获取刚插入的 ID，并将 root_id 更新为自身 ID
                SET v_comment_id = LAST_INSERT_ID();
                UPDATE comments SET root_id = v_comment_id WHERE id = v_comment_id;
                
            ELSE
                -- === 插入子回复 ===
                -- 随机找一个当前帖子下现有的根评论 ID
                -- 注意：性能较差但逻辑准确。在存储过程中随机取一条作为 root
                SELECT id INTO v_root_id FROM comments 
                WHERE post_id = v_post_id AND parent_id IS NULL 
                ORDER BY RAND() LIMIT 1;
                
                -- 如果找不到根评论（极少情况），就作为根评论处理
                IF v_root_id IS NULL THEN
                    SET v_root_id = 0; -- 标记失败，稍后逻辑处理
                END IF;

                IF v_root_id > 0 THEN
                     -- 这里简单处理：子回复直接挂在 Root 下 (二级扁平化)，或者随机挂在 Root 下的某个子评论下
                     -- 为了符合“二级评论”模型，parent_id 可以是 root，也可以是其他子评论，但 root_id 必须是 v_root_id
                     SET v_parent_id = v_root_id; 
                     
                     -- 模拟 "回复 @某人"
                     -- 获取 parent 的作者
                     SELECT user_id INTO v_reply_to_uid FROM comments WHERE id = v_parent_id;
                     
                     IF v_is_deleted THEN SET v_content = '该评论已删除'; ELSE SET v_content = '确实，我也觉得这里有个坑。(子回复)'; END IF;

                     INSERT INTO comments (post_id, user_id, parent_id, root_id, reply_to_user_id, content, is_deleted)
                     VALUES (v_post_id, v_user_id, v_parent_id, v_root_id, v_reply_to_uid, v_content, v_is_deleted);
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

-- ----------------------------
-- 4. 清理存储过程
-- ----------------------------
DROP PROCEDURE GenerateMockData;
SET FOREIGN_KEY_CHECKS = 1;

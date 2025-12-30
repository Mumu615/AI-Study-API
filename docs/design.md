# 第一阶段：需求分析与设计决策

## 1. 删除逻辑 (Deletion Logic)
- **策略**: 软删除 (Soft Delete)
- **字段**: `is_deleted` (Boolean/TinyInt)
- **原因**: 保持数据完整性，保留由于级联关系需要显示的数据占位符。
- **级联处理**:
  - **帖子删除**: 帖子标记为 `is_deleted=1`。接口逻辑：帖子详情接口返回 404 或已删除状态，评论列表接口不再返回该帖子的评论数据（逻辑上隐藏，数据库保留）。
  - **评论删除**: 
    - **一级评论（根评论）被删**: 标记 `is_deleted=1`。接口返回时，如果不含子回复，则不显示；如果包含子回复，则显示为“该评论已删除”或折叠状态，保留楼层以展示子回复。
    - **二级回复被删**: 标记 `is_deleted=1`。接口直接过滤掉该条数据，**不显示**。

## 2. 评论架构 (Comment Hierarchy)
- **模式**: 主评论 + 子回复 (类似B站/公众号，非无限嵌套)。
- **层级**:
  - `Level 1`: 根评论 (Root Comment) - 直接关联帖子。
  - `Level 2`: 子回复 (Reply) - 关联根评论，回复具体的某人。

## 3. 分页策略 (Pagination)
- **目标**: 按层级返回，避免断层。
- **方案**:
  - **针对根评论分页**: `SELECT * FROM comments WHERE post_id = ? AND parent_id IS NULL LIMIT ?, ?`
  - **子评论加载**: 获取当前页根评论的 ID 列表，查询所有挂载在这些根评论下的子回复。
  - **API 响应结构**:
    ```json
    {
      "page": 1,
      "total": 100,
      "list": [
        {
          "id": 1,
          "content": "Root comment",
          "replies": [
            { "id": 2, "content": "Reply to root", "reply_to_user": ... }
          ]
        }
      ]
    }
    ```

## 4. 数据库建模 (Phase 2: DB Modeling)
- **Schema File**: `docs/schema.sql`
- **核心表结构**: `users`, `posts`, `comments`.
- **关键决策**:
  - **`root_id` 策略**: 采用 **Option B**。即根评论的 `root_id` 等于它自己的 `id`。
    - *优势*: 查询逻辑统一，方便一次性拉取整个对话树。
    - *注意*: 插入根评论时需二次更新或在事务中处理。
  - **冗余字段**: 在 `posts` 表中引入 `comment_count` 和 `view_count` 以优化列表查询性能。
  - **Redis 规划**:
    - 计数器缓存 (`comment_count`).
    - 热门帖子第一页评论缓存 (`post:comments:page:1:{postId}`).

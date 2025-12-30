# 学习社区 API 接口文档
版本: 1.0
基础路径: `/api/v1`

## 1. 概览 (Overview)
本文档提供了管理帖子（Posts）和二级嵌套评论系统（根评论 + 子回复）的接口定义。

### 通用逻辑
- **软删除 (Soft Deletion)**: 数据不会被物理删除，仅更新 `is_deleted` 标记。
- **分页 (Pagination)**: 使用标准的 `page` (页码) 和 `pageSize` (每页数量) 查询参数。

---

## 2. 帖子 (Posts) /posts

### 2.1 发布新帖子 (Create Post)
**POST** `/posts`

**请求体 (Request Body):**
```json
{
  "user_id": 1, 
  "title": "关于软删除的讨论",
  "content": "如果评论下有回复，我们应该如何处理删除逻辑？"
}
```

**响应 (201 Created):**
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": 100,
    "title": "关于软删除的讨论",
    "created_at": "2025-12-26T10:00:00Z"
  }
}
```

### 2.2 获取帖子列表 (Get Post List)
**GET** `/posts`

**查询参数 (Query Parameters):**
- `page`: int (默认 1)
- `pageSize`: int (默认 10)

**响应 (200 OK):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "pagination": { "page": 1, "pageSize": 10, "total": 50 },
    "list": [
      {
        "id": 100,
        "title": "关于软删除的讨论",
        "content_snippet": "如果评论下有...",
        "user_id": 1,
        "view_count": 120,
        "comment_count": 5,
        "created_at": "2025-12-26T10:00:00Z"
      }
    ]
  }
}
```

### 2.3 获取帖子详情 (Get Post Detail)
**GET** `/posts/:id`

**响应 (200 OK):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 100,
    "user_id": 1,
    "title": "关于软删除的讨论",
    "content": "完整内容...",
    "view_count": 121,
    "comment_count": 5,
    "created_at": "2025-12-26T10:00:00Z"
  }
}
```

### 2.4 删除帖子 (Delete Post)
**DELETE** `/posts/:id`

**逻辑**: 软删除 (`is_deleted = 1`)。
**响应 (200 OK):**
```json
{ "code": 200, "msg": "success" }
```

---

## 3. 评论 (Comments)

### 3.1 发布评论 (Create Comment)
**POST** `/posts/:postId/comments`

**描述**: 根据 `parent_id` 自动处理“根评论”和“子回复”。

**请求体 (Request Body):**
```json
{
  "user_id": 10,
  "content": "这是一条非常有深度的评论",
  "parent_id": 101, 
  "reply_to_user_id": 55
}
```
*字段说明*:
- `parent_id`: 可选。**空 (NULL)** 表示根评论；**有值** 表示子回复。
- `reply_to_user_id`: 可选。仅在子回复时需要，用于前端展示 "回复 @某人"。

**后端逻辑 (Option B)**:
1. **如果是根评论** (`parent_id` 为空):
   - 插入数据。
   - 更新 `root_id` = `id` (自引用)。
2. **如果是子回复** (`parent_id` 有值):
   - 查找父评论所属的 `root_id`。
   - 插入数据，并带上该 `root_id`。

**响应 (201 Created):**
```json
{
  "code": 201,
  "msg": "success",
  "data": {
    "id": 104,
    "root_id": 101,
    "parent_id": 101,
    "content": "这是一条非常有深度的评论"
  }
}
```

### 3.2 获取评论列表 (Get Comment List)
**GET** `/posts/:postId/comments`

**查询参数 (Query Parameters):**
- `page`: int (默认 1) - **特指根评论的页码**。
- `pageSize`: int (默认 10)
- `sort`: string (默认 'newest')

**响应模板 (Response Template):**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "pagination": {
      "page": 1,
      "pageSize": 10,
      "total_root_comments": 42 // 注意：统计的是根评论总数
    },
    "list": [
      {
        "id": 101,
        "user": { "id": 10, "username": "李将", "avatar": "url..." },
        "content": "这是一个根评论",
        "created_at": "2025-12-26T10:00:00Z",
        "like_count": 5,
        "is_deleted": false,
        "replies": [
          {
            "id": 102,
            "user": { "id": 20, "username": "路人甲", "avatar": "url..." },
            "reply_to_user": { "id": 10, "username": "李将" },
            "content": "回复楼主：确实如此",
            "created_at": "2025-12-26T10:05:00Z",
            "parent_id": 101
          }
        ]
      }
    ]
  }
}
```

### 3.3 删除评论 (Delete Comment)
**DELETE** `/comments/:id`

**逻辑**: 更新 `is_deleted = 1`。**不要**物理删除级联的子评论。

**响应 (200 OK):**
```json
{ "code": 200, "msg": "success" }
```

---

## 4. 边缘情况展示逻辑 (Edge Case Display Logic)

### A. 根评论被删 (Root Comment Deleted) - 有子回复
- **后端状态**: `is_deleted=1` 但 `replies` 数组非空。
- **返回处理**:
  - `content`: 替换为 "该评论已删除" (或由前端处理)。
  - `user`: 置空或返回占位符。
  - `replies`: 正常返回子回复数据。
- **UI 展示**: 显示为一个灰色的可折叠/占位楼层，保留结构以展示子回复。

### B. 根评论被删 (Root Comment Deleted) - 无子回复
- **后端状态**: `is_deleted=1` 且无有效子回复。
- **行为**: 直接从返回列表中剔除，不返回。

### C. 子回复被删 (Reply Deleted)
- **后端状态**: `is_deleted=1`。
- **行为**: 直接从 `replies` 数组中剔除，不返回。

# 学习社区 API (Learning Community API)

这是一个基于 FastAPI 构建的现代学习社区后端服务，旨在提供高性能、可扩展的 RESTful API 接口。项目包含了完整的用户认证、帖子管理以及支持二级嵌套结构的评论系统。

此外，本项目还包含了一个基于 Vue 3 的前端参考实现。

## 🛠 技术栈

### 后端 (Backend)
- **框架**: [FastAPI](https://fastapi.tiangolo.com/) - 高性能、易于学习的 Python 异步 Web 框架。
- **数据库 ORM**: [SQLAlchemy](https://www.sqlalchemy.org/) (Async) - 强大的 SQL 工具包和对象关系映射器。
- **数据库驱动**: [aiomysql](https://github.com/aio-libs/aiomysql) - 用于 MySQL 的异步驱动。
- **验证**: [Pydantic](https://docs.pydantic.dev/) - 数据验证和设置管理。
- **缓存**: Redis - 用于热门数据缓存和性能优化。
- **迁移**: [Alembic](https://alembic.sqlalchemy.org/) - 数据库版本控制和迁移工具。
- **认证**: JWT (JSON Web Tokens) - 安全的用户身份验证机制。

### 前端 (Frontend)
- **核心**: Vue 3
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router

## 📂 项目结构

```
.
├── my_app/              # 后端核心代码
│   ├── main.py          # 程序入口
│   ├── models.py        # 数据库模型定义
│   ├── schemas.py       # Pydantic 数据模型 (Response/Request)
│   ├── crud.py          # 数据库操作逻辑
│   ├── database.py      # 数据库连接配置
│   ├── security.py      # 安全与认证相关工具
│   └── redis_utils.py   # Redis 工具函数
├── frontend/            # 前端应用源码
├── tests/               # Pytest 测试套件
├── docs/                # 设计文档与测试报告
├── alembic/             # 数据库迁移脚本
└── requirements.txt     # Python 依赖列表
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- MySQL 8.0+
- Redis Server
- Node.js (用于前端)

### 后端设置

1. **克隆仓库并进入目录**
   ```bash
   git clone <repository_url>
   cd 学习社区API
   ```

2. **创建并激活虚拟环境**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   在根目录创建一个 `.env` 文件，并根据您的环境填入以下配置：
   ```ini
   DB_CONNECTION=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_DATABASE=your_database_name
   DB_USERNAME=your_username
   DB_PASSWORD=your_password
   
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   SECRET_KEY=your_secure_secret_key
   ```

5. **运行数据库迁移**
   ```bash
   alembic upgrade head
   ```

6. **启动开发服务器**
   ```bash
   uvicorn my_app.main:app --reload
   ```
   API 文档将在 `http://localhost:8000/docs` 自动生成。

### 🐳 Docker 部署 (推荐)

如果您希望快速启动完整的运行环境（包含 MySQL 和 Redis），可以使用 Docker Compose。

1. **确保已安装 Docker 和 Docker Compose**

2. **启动服务**
   在项目根目录下运行：
   ```bash
   docker-compose up -d
   ```
   该命令会自动：
   - 拉取并启动 MySQL 8.0 数据库容器。
   - 拉取并启动 Redis 容器。
   - 构建后端镜像，并在容器启动时自动执行数据库迁移。

3. **访问应用**
   后端 API 将在 `http://localhost:8000` 运行。

4. **停止服务**
   ```bash
   docker-compose down
   ```

### 前端设置

1. **进入前端目录**
   ```bash
   cd frontend
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **启动开发服务**
   ```bash
   npm run dev
   ```

## 📝 API 使用示例 (cURL)

以下是使用 `curl` 命令行工具测试 API 的常用命令。请确保后端服务已运行在 `http://localhost:8000`。

### 1. 用户认证

**注册新用户**
```bash
curl -X POST "http://localhost:8000/users" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123", "avatar_url": "https://example.com/avatar.png"}'
```

**登录获取 Token**
```bash
curl -X POST "http://localhost:8000/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=testuser&password=password123"
```
> **注意**: 登录成功后会返回 `access_token`。请将后续请求中的 `YOUR_ACCESS_TOKEN` 替换为实际获取的 Token。

**获取当前用户信息**
```bash
curl -X GET "http://localhost:8000/users/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 2. 帖子管理

**发布帖子**
```bash
curl -X POST "http://localhost:8000/posts" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "这是我的第一篇帖子", "content": "FastAPI 和 Vue 3 的组合真是太棒了！"}'
```

**获取帖子列表 (分页)**
```bash
curl -X GET "http://localhost:8000/posts?page=1&pageSize=10"
```

**获取帖子详情**
```bash
# 将 1 替换为实际的 post_id
curl -X GET "http://localhost:8000/posts/1"
```

**删除帖子**
```bash
# 仅限作者操作
curl -X DELETE "http://localhost:8000/posts/1" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. 评论系统

**发表根评论 (对帖子)**
```bash
# 将 1 替换为 post_id
curl -X POST "http://localhost:8000/posts/1/comments" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"content": "这是一个很棒的观点！"}'
```

**发表子回复 (对评论)**
```bash
# 将 1 替换为 post_id
# 将 100 替换为父评论的 ID (parent_id)
# 将 50 替换为被回复用户的 ID (reply_to_user_id)
curl -X POST "http://localhost:8000/posts/1/comments" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"content": "我完全同意你的看法。", "parent_id": 100, "reply_to_user_id": 50}'
```

**获取帖子的根评论列表**
```bash
curl -X GET "http://localhost:8000/posts/1/comments?page=1&pageSize=10&sort=newest"
```

**获取某个根评论下的所有子回复**
```bash
# 将 100 替换为根评论 ID (root_id)
curl -X GET "http://localhost:8000/comments/100/replies"
```

**删除评论**
```bash
# 将 100 替换为 comment_id
curl -X DELETE "http://localhost:8000/comments/100" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## ✨ 核心功能

### 1. 用户系统
- 支持用户注册与登录。
- 基于 JWT 的身份验证流程。
- 密码使用 Argon2 算法进行哈希加密，保障账户安全。

### 2. 内容管理 (Posts)
- 帖子的增删改查 (CRUD)。
- 支持分页获取帖子列表。
- 只有帖子的作者或管理员可以删除帖子（软删除机制）。

### 3. 评论系统 (Comments)
- **二级嵌套结构**：支持“根评论”及“回复”（Reply）。
- **层级展示**：前端可根据 `root_id` 和 `parent_id` 渲染树状评论区。
- **软删除逻辑**：
  - 若根评论被删除，其内容会被替换为占位符（如“该评论已删除”），但其下属的回复依然可见。
  - 若子回复被删除，则不再在列表中返回。
- **高性能查询**：优化了数据库查询逻辑，支持分页加载根评论。

## 💡 设计理念与技术选型

### 为什么选择 FastAPI？
FastAPI 是目前 Python 生态中最现代化且增长最快的 Web 框架之一。我们在本项目中选择它，主要基于以下考量：
1.  **原生异步支持**: 结合 Python 的 `async/await` 语法和 `aiomysql`，FastAPI 能够轻松处理高并发请求，特别适合 I/O 密集型的社区类应用。
2.  **自动文档生成**: 基于 OpenAPI 标准，FastAPI 能够自动生成交互式 API 文档（Swagger UI），这极大地降低了前后端联调的沟通成本。
3.  **类型安全与验证**: 深度集成 Pydantic，使得数据验证逻辑与业务逻辑解耦，代码更健壮，IDE 提示更友好，减少了大量运行时错误。

### 数据库设计思路
在设计评论系统时，我们面临着存储树状结构数据的挑战。我们最终选择了 **邻接表 (Adjacency List)** 模型的变体，并针对不同查询场景做了优化：
1.  **两级嵌套结构**: 为了在用户体验和系统复杂度之间取得平衡，我们没有采用无限嵌套，而是强制将评论结构扁平和标准化为“根评论”与“子回复”两级。这种设计在移动端和 Web 端展示时更加清晰。
2.  **冗余字段设计**:
    *   在 `comments` 表中引入 `root_id` 字段：无论是根评论还是子回复，都记录其所属的根评论 ID。
    *   **优势**: 这样设计使得“获取某条根评论下的所有回复”这一高频操作，变成了一个简单的单表 `WHERE root_id = ?` 查询，无需复杂的递归查询（CTE），显著提升了读取性能。

### API 架构设计
API 设计遵循 RESTful 规范，并特别注重**按需加载**与**性能优化**：
1.  **分页与懒加载策略**:
    *   `/posts/{id}/comments` 接口仅返回根评论列表及其回复数量，不一次性加载所有子回复。
    *   只有当用户点击“查看回复”时，才会请求 `/comments/{id}/replies` 接口加载子数据。
    *   **目的**: 这种策略极大地减少了首屏加载的数据量，提升了页面响应速度，同时节省了服务器带宽。
2.  **DTO (Data Transfer Object) 隔离**: 通过 Pydantic 定义明确的 `Schema`（如 `UserCreate` vs `UserOut`），严格分离了内部数据库模型与外部 API 响应模型，防止敏感数据（如密码 hash）意外泄露，并确保了接口契约的稳定性。

### 🧩 难点攻克：评论的层级查询实现

在多级评论系统中，最大的痛点往往是**N+1 查询问题**以及复杂的状态判断。我们在项目中采用了以下策略来优雅解决：

1.  **分步查询与批量聚合 (Solve N+1)**:
    我们没有在获取根评论的同时通过循环去查询每条评论的子回复，而是采用分步策略：
    *   **第一步**：`SELECT * FROM comments WHERE parent_id IS NULL ...` —— 仅获取一页根评论。
    *   **第二步**：收集上述根评论的 ID 列表，执行一次聚合查询：
        ```sql
        SELECT root_id, COUNT(*) FROM comments 
        WHERE root_id IN (...) AND is_deleted = false 
        GROUP BY root_id
        ```
    *   **结果**: 这里只消耗了 **2 次** 数据库查询，就完成了“获取根评论列表 + 每条评论的回复数”的任务，哪怕一页有 20 条评论，也不会产生 21 次查询。

2.  **“幽灵评论”的判定 (Ghost Comments)**:
    业务有个特殊需求：*如果一个根评论被删除了，但它下面还有未删除的回复，这个根评论不能消失，而是显示“该评论已删除”并保留占位*。
    
    为了在数据库层面高效过滤（避免把被删且无回复的垃圾数据查出来），我们构造了一个**相关子查询 (Correlated Subquery)**：
    ```python
    # SQLAlchemy 伪代码
    has_valid_children = exists(
        select(1).where(Child.root_id == Parent.id, Child.is_deleted == False)
    )
    filter_condition = or_(
        Parent.is_deleted == False,                 # 正常评论
        and_(Parent.is_deleted == True, has_valid_children) # 被删但有“香火”的评论
    )
    ```
    这个设计将复杂的业务逻辑下沉到了数据库层面执行，大大减少了 Python 层的内存开销和循环判断。

## 🔮 局限性与未来展望

### 当前实现的局限性
虽然当前架构对于中小型社区（几万用户）完全足够，但在面对海量数据时存在以下短板：
1.  **实时 Count 的性能隐患**: 目前帖子列表的 `comment_count` 和评论列表的 `reply_count` 都是基于 `GROUP BY` 或子查询实时计算的。当单表数据突破百万级，这种聚合查询会导致数据库 CPU 飙升。
2.  **数据库单点**: 所有的读写请求都打在同一个 MySQL 实例上，高并发下数据库连接数和 I/O 会成为瓶颈。
3.  **搜索能力弱**: 目前的搜索仅依赖 SQL 的 `LIKE` 语句，无法支持模糊搜索、分词搜索或按相关度排序，且性能随数据量增加而线性下降。

### 🚀 百万级用户架构演进计划
如果需要支持百万级活跃用户，我们将进行以下架构调整：

1.  **数据库读写分离与分库分表**:
    *   部署 MySQL 主从集群，主库负责写，多个从库负责读，实现读写分离。
    *   对 `comments` 和 `posts` 表进行**水平分表**（Sharding），例如按 `post_id` 取模分片，将数据分散到不同的物理库中，解决单表数据过大的问题。

2.  **计数器服务与异步化**:
    *   **去实时 Count**: 废弃 `SELECT COUNT(*)`。在 Redis 中维护这一计数，或者在 `posts` 表中增加 `comment_count` 字段。
    *   **异步写入**: 引入消息队列（如 Kafka 或 RabbitMQ）。当用户发表评论时，先写入 MQ，由消费者异步更新数据库和 Redis 计数器，实现**流量削峰**。

3.  **多级缓存策略**:
    *   **热点数据**: 对热门帖子和其第一页评论进行激进的 Redis 缓存（设置 TTL）。
    *   **Cache Aside**: 严格遵循 Cache Aside 模式，优先读缓存，缓存未命中再读库并回填。

4.  **引入全文搜索引擎**:
    *   搭建 **Elasticsearch** 集群。将帖子的标题、内容同步到 ES 中，承担所有的关键词搜索与复杂的筛选请求，减轻 MySQL 负担。

# 学习社区 API (Learning Community API)

这是一个用于学习和演示的社区后端项目，基于 FastAPI 开发。除了常见的用户和帖子功能外，我主要花时间实现了一套支持**二级嵌套**的评论系统（包含软删除和防 N+1 查询优化）。

为了方便调试，我也顺手写了一个简单的 Vue 3 前端。

## 🛠 技术栈

没搞太复杂的，选得都是目前 Python 生态里比较主流和好用的库：

*   **FastAPI**: 核心 Web 框架，自动生成文档这点太好用了。
*   **SQLAlchemy (Async) + aiomysql**: 全程异步 ORM，性能比同步版本好很多。
*   **Pydantic**: 专门用来做数据校验，把脏数据挡在外面。
*   **Redis**: 用来做一些简单的缓存。
*   **Alembic**: 数据库迁移工具，改表结构全靠它。
*   **Vue 3 + Vite**: 前端那一套。

## 🚀 怎么跑起来

### 方式一：Docker 一键启动 (推荐)

如果你懒得配环境，直接用 Docker 最快：

```bash
# 启动 MySQL, Redis 和 Backend
docker-compose up -d
```

启动后访问 `http://localhost:8000/docs` 就能看到接口文档了。

### 方式二：手动安装

如果想改改代码，本地跑比较方便：

1.  **准备环境**: 需要 Python 3.10+, MySQL 8.0+ 和 Redis。
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **配置数据库**:
    复制一份 `.env.example` (或者自己建一个 `.env`)，填上你的数据库账号密码：
    ```ini
    DB_HOST=localhost
    DB_PASSWORD=your_password
    ...
    ```
4.  **初始化数据库**:
    ```bash
    alembic upgrade head
    ```
5.  **启动**:
    ```bash
    uvicorn my_app.main:app --reload
    ```

## ✨ 做了哪些功能

1.  **用户**: 注册、登录（JWT 鉴权）、密码加密（用的是 Argon2，比 plain text 安全）。
2.  **帖子**: 标准的增删改查。加了个软删除，删了不是真删，是标记为 deleted。
3.  **评论系统 (重点)**:
    *   **二级结构**: 这里设计成了“根评论”和“回复”两层。这种结构比无限嵌套好维护，展示也清晰。
    *   **软删除逻辑**: 有点绕。如果一个根评论被删了，但它下面还有人回复，这楼不能塌，得显示“该评论已删除”占位；如果是子回复被删，那就直接不显示了。
    *   **性能优化**: 分页读取，不会一次把所有数据拉出来。

## 💡 一些设计思路

### 为什么选 FastAPI?
以前用 Flask 比较多，但换 FastAPI 后发现开发效率确实高。主要是那个 **Type Hint** 配合 **Pydantic**，写代码的时候 IDE 智能提示很全，运行时参数校验也自动做好了，省了很多 `if/else` 的检查代码。而且原生支持异步，应对高并发场景更有底气。

### 数据库这里怎么考虑的？
评论系统最纠结的是怎么存树状结构。
我最后选了 **邻接表** 的变体。为了查询快，我在表里冗余了一个 `root_id` 字段。
*   **好处**: 不管是查根评论，还是查某条评论下的所有回复，只要一条 SQL `WHERE root_id = ...` 就搞定了，不用去写复杂的递归查询（CTE）。
*   **代价**: 写数据的时候多存一个字段，我觉得划算。

### 🧩 遇到的坑：N+1 查询问题
开发评论列表时，如果直接用 ORM 的 lazy load，查一页 10 条评论，后台可能会发出 11 条 SQL（1 条查列表，10 条分别查回复数）。
为了解决这个问题，我改成了**分步查询**：
1.  先查出一页根评论。
2.  把这页的 ID 拿出来，去数据库里 `GROUP BY` 一次算出所有回复数。
3.  在内存里拼装回去。
这样数据库查询次数就是固定的，不会随着数据量变大而变慢。

## 📝 常用 API (cURL)

给你几个现成的命令，粘贴到终端就能测：

**1. 登录拿 Token**
```bash
curl -X POST "http://localhost:8000/token" \
     -d "username=testuser&password=password123"
```

**2. 发个帖子**
```bash
curl -X POST "http://localhost:8000/posts" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Hello World", "content": "测试一下"}'
```

**3. 查评论**
```bash
curl -X GET "http://localhost:8000/posts/1/comments?page=1"
```

## 🔮 这以后还能怎么改？
现在的架构跑个几万用户没问题，但如果真到百万级，肯定有瓶颈：
*   **实时 Count 扛不住**: 现在的回复数是实时 `Select Count(*)` 出来的，数据多了数据库 CPU 会炸。以后得把计数放到 Redis 里，或者异步去更新。
*   **搜索太弱**: 现在就是 `LIKE` 模糊匹配。后面数据多了肯定得上 Elasticsearch。

---
*代码这东西，跑通了是第一步，后面优化永无止境。欢迎提 PR 一起改进。*

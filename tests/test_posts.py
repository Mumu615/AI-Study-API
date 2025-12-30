import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from my_app import models

# =======================
# 1. 功能与业务逻辑测试 (Functional & Logic)
# =======================

@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, auth_headers_a: dict, db_session: AsyncSession):
    """
    Test 1.A: 正常发布帖子
    - 预期: 201 Created, 返回包含 id 和 created_at
    - 数据完整性: DB新增记录, user_id正确, 默认值正确
    """
    payload = {"title": "Test Post Title", "content": "This is a test content that is long enough."}
    response = await client.post("/posts", json=payload, headers=auth_headers_a)
    
    # Check Response
    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    assert "created_at" in data
    assert data["title"] == payload["title"]
    
    # Check DB
    post_id = data["id"]
    result = await db_session.execute(select(models.Post).where(models.Post.id == post_id))
    db_post = result.scalar_one()
    
    assert db_post.title == payload["title"]
    assert db_post.user_id is not None # specific value depends on fixture ID
    assert db_post.is_deleted is False
    assert db_post.view_count == 0
    assert db_post.comment_count == 0

@pytest.mark.asyncio
async def test_list_posts_pagination_and_snippet(client: AsyncClient, auth_headers_a: dict):
    """
    Test 1.B: 获取帖子列表 (分页, 摘要)
    - 场景: 发布 6 篇帖子 (5 + 1)
    - 预期: page=1返回5篇, page=2返回1篇
    - 预期: 摘要截断
    """
    # Create 6 posts
    base_content = "A" * 60 # > 50 chars
    for i in range(6):
        await client.post(
            "/posts", 
            json={"title": f"Post {i}", "content": f"{i} {base_content}"}, 
            headers=auth_headers_a
        )
        
    # Page 1
    resp_p1 = await client.get("/posts?page=1&pageSize=5")
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()["data"]
    assert len(data_p1["list"]) == 5
    assert data_p1["pagination"]["total"] == 6 # Total existing unknown, but at least 6 + any mainly created
    # Check ordering (desc): Post 5 should be first (if no other tests ran before)
    # Actually DB is cleared per function, so exactly 6.
    assert data_p1["list"][0]["title"] == "Post 5"
    
    # Check Snippet
    snippet = data_p1["list"][0]["content_snippet"]
    assert len(snippet) == 50 + 3 # 50 chars + "..."
    assert snippet.endswith("...")

    # Page 2
    resp_p2 = await client.get("/posts?page=2&pageSize=5")
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()["data"]
    assert len(data_p2["list"]) == 1
    assert data_p2["list"][0]["title"] == "Post 0"

@pytest.mark.asyncio
async def test_soft_delete_filter(client: AsyncClient, auth_headers_a: dict):
    """
    Test 1.B & 1.D: 软删除过滤
    - 场景: 发布并删除
    - 预期: 列表不包含
    """
    # Create post
    create_resp = await client.post(
        "/posts", 
        json={"title": "To Delete", "content": "Content"}, 
        headers=auth_headers_a
    )
    post_id = create_resp.json()["data"]["id"]
    
    # Delete it
    del_resp = await client.delete(f"/posts/{post_id}", headers=auth_headers_a)
    assert del_resp.status_code == 200
    
    # List Check
    list_resp = await client.get("/posts")
    posts = list_resp.json()["data"]["list"]
    ids = [p["id"] for p in posts]
    assert post_id not in ids

@pytest.mark.asyncio
async def test_get_post_detail_side_effect(client: AsyncClient, auth_headers_a: dict, db_session: AsyncSession):
    """
    Test 1.C: 详情与浏览量
    - 预期: 200 OK, view_count + 1
    """
    # Create
    create_resp = await client.post(
        "/posts", 
        json={"title": "Detail Test", "content": "Content"}, 
        headers=auth_headers_a
    )
    post_id = create_resp.json()["data"]["id"]
    
    # Get Detail
    detail_resp = await client.get(f"/posts/{post_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()["data"]
    assert data["content"] == "Content"
    # Note: returned data might show 0 or 1 depending on whether increment happens before or after fetch
    # Code: `crud.get_post` fetches first, then increments. BUT wait, `result.scalar_one_or_none()` fetches object.
    # Then `post.view_count += 1`.
    # Since it's invalidating the object in session or not? 
    # Usually the returned object object is the one in session. If we updated it, it should reflect?
    # Actually, SQLAlchemy objects track changes. If we modify `post.view_count += 1` and return `post`, 
    # it *should* show the incremented value if we don't refresh?
    # Let's verify DB state to be sure.
    
    db_session.expire_all() # Force reload from DB
    result = await db_session.execute(select(models.Post).where(models.Post.id == post_id))
    db_post = result.scalar_one()
    assert db_post.view_count == 1

@pytest.mark.asyncio
async def test_get_deleted_post_detail(client: AsyncClient, auth_headers_a: dict):
    """
    Test 1.C: 获取已删除详情
    - 预期: 404
    """
    # Create & Delete
    create_resp = await client.post("/posts", json={"title": "Del", "content": "C"}, headers=auth_headers_a)
    post_id = create_resp.json()["data"]["id"]
    await client.delete(f"/posts/{post_id}", headers=auth_headers_a)
    
    # Get
    resp = await client.get(f"/posts/{post_id}")
    assert resp.status_code == 404

# =======================
# 2. 安全与权限测试 (Security & Authorization)
# =======================

@pytest.mark.asyncio
async def test_create_post_unauthorized(client: AsyncClient):
    """
    Test 2: 未登录发布
    - 预期: 401
    """
    resp = await client.post("/posts", json={"title": "No Auth", "content": "..."})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_delete_other_user_post(client: AsyncClient, auth_headers_a: dict, auth_headers_b: dict):
    """
    Test 2: 越权删除
    - 场景: User B 删除 User A 的帖子
    - 预期: 403
    """
    # A Create
    create_resp = await client.post("/posts", json={"title": "A Post", "content": "Content"}, headers=auth_headers_a)
    post_id = create_resp.json()["data"]["id"]
    
    # B Try Delete
    del_resp = await client.delete(f"/posts/{post_id}", headers=auth_headers_b)
    assert del_resp.status_code == 403

@pytest.mark.asyncio
async def test_repeat_delete(client: AsyncClient, auth_headers_a: dict):
    """
    Test 2: 重复删除
    - 预期: 第一次 200, 第二次 404 (因为 get_post 过滤了 is_deleted)
    """
    # Create
    create_resp = await client.post("/posts", json={"title": "Del", "content": "C"}, headers=auth_headers_a)
    post_id = create_resp.json()["data"]["id"]
    
    # Del 1
    resp1 = await client.delete(f"/posts/{post_id}", headers=auth_headers_a)
    assert resp1.status_code == 200
    
    # Del 2
    resp2 = await client.delete(f"/posts/{post_id}", headers=auth_headers_a)
    assert resp2.status_code == 404

# =======================
# 3. 边界与参数校验测试 (Boundary & Validation)
# =======================

@pytest.mark.asyncio
async def test_create_post_missing_fields(client: AsyncClient, auth_headers_a: dict):
    """
    Test 3: 必填项缺失
    - 预期: 422
    """
    # Missing content
    resp = await client.post("/posts", json={"title": "Only Title"}, headers=auth_headers_a)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_create_post_long_title(client: AsyncClient, auth_headers_a: dict):
    """
    Test 3: 标题超长
    - 预期: 422
    """
    long_title = "a" * 101
    resp = await client.post("/posts", json={"title": long_title, "content": "c"}, headers=auth_headers_a)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_invalid_id(client: AsyncClient, auth_headers_a: dict):
    """
    Test 3: 无效ID
    - 预期: 404 for not found (valid type), 422 for invalid type
    """
    # Not Found
    resp = await client.get("/posts/999999")
    assert resp.status_code == 404
    
    # Invalid Type (FastAPI auto validate int)
    resp2 = await client.get("/posts/abc")
    assert resp2.status_code == 422

# =======================
# 4. 数据一致性测试 (Consistency)
# =======================
@pytest.mark.asyncio
async def test_comment_count_consistency(client: AsyncClient, auth_headers_a: dict, db_session: AsyncSession):
    """
    Test 4: 评论数一致性
    - 场景: 发帖 -> 发评论
    - 预期: Post.comment_count 增加
    """
    # Create Post
    create_resp = await client.post("/posts", json={"title": "Post", "content": "C"}, headers=auth_headers_a)
    post_id = create_resp.json()["data"]["id"]
    
    # Create Comment
    await client.post(
        f"/posts/{post_id}/comments", 
        json={"content": "Comment 1"}, 
        headers=auth_headers_a
    )
    
    # Check Post
    db_session.expire_all()
    result = await db_session.execute(select(models.Post).where(models.Post.id == post_id))
    db_post = result.scalar_one()
    assert db_post.comment_count == 1

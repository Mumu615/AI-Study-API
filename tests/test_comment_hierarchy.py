import pytest
from httpx import AsyncClient
from my_app import models, schemas

@pytest.fixture
async def test_post(db_session, user_a):
    post = models.Post(
        title="Test Post for Comments",
        content="This is a test post.",
        user_id=user_a.id
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post

@pytest.mark.asyncio
async def test_pagination_and_hierarchy(client: AsyncClient, auth_headers_a, test_post):
    post_id = test_post.id
    headers = auth_headers_a

    # 1. 准备数据：创建 15 条根评论
    # 注意：我们希望最新的在最前面，所以按顺序创建。
    # Root 0 created first... Root 14 created last.
    # Sorted by desc: Root 14, Root 13...
    for i in range(15):
        resp = await client.post(
            f"/posts/{post_id}/comments", 
            json={"content": f"Root {i}", "post_id": post_id}, 
            headers=headers
        )
        assert resp.status_code == 201

    # 2. 测试分页 (Page 1)
    # 预期: Root 14 到 Root 5 (10 items)
    resp = await client.get(f"/posts/{post_id}/comments", params={"page": 1, "pageSize": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()['data']
    
    assert data['pagination']['total'] == 15
    assert len(data['list']) == 10
    
    # 验证排序：最新的在最前 (Root 14 应该是第一个)
    assert data['list'][0]['content'] == "Root 14"
    assert data['list'][9]['content'] == "Root 5"

    # 3. 测试分页 (Page 2)
    # 预期: Root 4 到 Root 0 (5 items)
    resp = await client.get(f"/posts/{post_id}/comments", params={"page": 2, "pageSize": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()['data']
    assert len(data['list']) == 5
    assert data['list'][0]['content'] == "Root 4"
    assert data['list'][4]['content'] == "Root 0" # The oldest one

    # 4. 测试层级与回复数
    # 在 "Root 4" 下创建 2 个回复
    # Root 4 is data['list'][0] from Page 2
    target_root_id = data['list'][0]['id']
    
    # Reply 1
    resp_r1 = await client.post(
        f"/posts/{post_id}/comments", 
        json={"content": "Reply 1", "parent_id": target_root_id, "post_id": post_id}, 
        headers=headers
    )
    assert resp_r1.status_code == 201
    
    # Reply 2
    resp_r2 = await client.post(
        f"/posts/{post_id}/comments", 
        json={"content": "Reply 2", "parent_id": target_root_id, "post_id": post_id}, 
        headers=headers
    )
    assert resp_r2.status_code == 201

    # 再次查询根评论列表，验证 count
    resp = await client.get(f"/posts/{post_id}/comments", params={"page": 2, "pageSize": 10}, headers=headers)
    assert resp.status_code == 200
    
    # Find Root 4 in the list
    page2_list = resp.json()['data']['list']
    target_root = next((item for item in page2_list if item['id'] == target_root_id), None)
    
    assert target_root is not None
    assert target_root['reply_count'] == 2  # 验证计数

    # 5. 验证子回复接口
    resp = await client.get(f"/comments/{target_root_id}/replies", headers=headers)
    assert resp.status_code == 200
    replies = resp.json()['data']
    
    assert len(replies) == 2
    assert replies[0]['content'] == "Reply 1"
    assert replies[0]['root_id'] == target_root_id
    assert replies[1]['content'] == "Reply 2"
    
    # 验证子回复排序 (正序: earliest to newest)
    # Reply 1 created before Reply 2
    assert replies[0]['id'] < replies[1]['id']

@pytest.mark.asyncio
async def test_ghost_comment_logic(client: AsyncClient, auth_headers_a, test_post):
    post_id = test_post.id
    headers = auth_headers_a
    
    # 创建根评论
    resp = await client.post(
        f"/posts/{post_id}/comments", 
        json={"content": "To be deleted", "post_id": post_id}, 
        headers=headers
    )
    root_data = resp.json()['data']
    root_id = root_data['id']
    
    # 创建子回复
    await client.post(
        f"/posts/{post_id}/comments", 
        json={"content": "Survivor", "parent_id": root_id, "post_id": post_id}, 
        headers=headers
    )
    
    # 删除根评论
    # Author can delete their own comment
    del_resp = await client.delete(f"/comments/{root_id}", headers=headers)
    assert del_resp.status_code == 200
    
    # 验证幽灵状态
    resp = await client.get(f"/posts/{post_id}/comments", headers=headers)
    roots = resp.json()['data']['list']
    
    # 找到刚才删除的 ID
    ghost = next((r for r in roots if r['id'] == root_id), None)
    
    assert ghost is not None, "根评论虽已删除但有子回复，应保留在列表中"
    assert ghost['content'] == "该评论已删除"
    assert ghost['user'] is None
    # Assuming the API returns is_deleted flag or we can infer it. 
    # Based on schema defaults, let's check what we have.
    # Note: schemas.CommentListItem might not expose is_deleted directly if not added to schema, 
    # but the logic modifies content/user based on it.
    
    # 场景 3：根评论已删，子回复也全删了
    # Get the child reply id first
    replies_resp = await client.get(f"/comments/{root_id}/replies", headers=headers)
    child_id = replies_resp.json()['data'][0]['id']
    
    # Delete the child
    await client.delete(f"/comments/{child_id}", headers=headers)
    
    # Verify root is now gone from list (because no valid children)
    resp = await client.get(f"/posts/{post_id}/comments", headers=headers)
    roots = resp.json()['data']['list']
    
    ghost_again = next((r for r in roots if r['id'] == root_id), None)
    assert ghost_again is None, "根评论已删且无有效子回复，不应出现在列表中"

@pytest.mark.asyncio
async def test_hierarchy_structure_details(client: AsyncClient, auth_headers_a, test_post):
    """
    Detailed test for structure:
    A (Root) -> B (Reply to A) -> C (Reply to B, but root is A)
    """
    post_id = test_post.id
    headers = auth_headers_a
    
    # 1. Create A
    resp_a = await client.post(f"/posts/{post_id}/comments", json={"content": "A", "post_id": post_id}, headers=headers)
    id_a = resp_a.json()['data']['id']
    
    # 2. Create B (Reply to A)
    resp_b = await client.post(f"/posts/{post_id}/comments", json={"content": "B", "parent_id": id_a, "post_id": post_id}, headers=headers)
    id_b = resp_b.json()['data']['id']
    root_id_b = resp_b.json()['data']['root_id']
    assert root_id_b == id_a
    
    # 3. Create C (Reply to B)
    # Logic: C is child of B. But in 2-level system, C's root should be A.
    resp_c = await client.post(f"/posts/{post_id}/comments", json={"content": "C", "parent_id": id_b, "post_id": post_id}, headers=headers)
    id_c = resp_c.json()['data']['id']
    root_id_c = resp_c.json()['data']['root_id']
    
    # Verify Flattening/Nesting logic
    # The CRUD `create_comment` sets root_id based on parent's root_id.
    assert root_id_c == id_a
    
    # Verify Fetching Replies for A
    # API B: `GET /comments/{id_a}/replies` should return B and C
    resp = await client.get(f"/comments/{id_a}/replies", headers=headers)
    replies = resp.json()['data']
    
    reply_ids = [r['id'] for r in replies]
    assert id_b in reply_ids
    assert id_c in reply_ids
    assert len(replies) == 2
    
    # Check parentage in response
    reply_c_obj = next(r for r in replies if r['id'] == id_c)
    assert reply_c_obj['parent_id'] == id_b
    assert reply_c_obj['root_id'] == id_a

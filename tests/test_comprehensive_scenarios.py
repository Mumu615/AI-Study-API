
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from my_app import models, security

# =======================
# Test Data Fixtures
# =======================

@pytest_asyncio.fixture(scope="function")
async def admin_user(db_session: AsyncSession) -> models.User:
    """Create a user with ID=1 (Admin)"""
    # Force ID=1 (if possible, otherwise update ID)
    # Since autoincrement starts at 1, the first user created might be 1.
    # But conftest might have created others. Let's try to ensure we have ID=1.
    # However, if ID=1 is already taken by user_a, we might have issues.
    # Let's check or just insert with specific ID if dialect allows, or update.
    
    # Check if user 1 exists
    res = await db_session.execute(select(models.User).where(models.User.id == 1))
    u1 = res.scalar_one_or_none()
    
    if u1:
        return u1
        
    user = models.User(id=1, username="admin_user", avatar_url="http://admin.com/pic")
    db_session.add(user)
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        # If explicit ID insert fails, just create and hope, or update.
        user = models.User(username="admin_user", avatar_url="http://admin.com/pic")
        db_session.add(user)
        await db_session.commit()
        
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture(scope="function")
async def auth_headers_admin(admin_user: models.User) -> dict:
    token = security.create_access_token(data={"sub": admin_user.username})
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture(scope="function")
async def user_c(db_session: AsyncSession) -> models.User:
    user = models.User(username="user_c", avatar_url="http://c.com/pic")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture(scope="function")
async def auth_headers_c(user_c: models.User) -> dict:
    token = security.create_access_token(data={"sub": user_c.username})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def sample_post(db_session: AsyncSession, user_b: models.User) -> models.Post:
    """Post created by User B"""
    post = models.Post(title="Features of Rust", content="Rust is memory safe...", user_id=user_b.id)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post

# =======================
# Test Cases
# =======================

@pytest.mark.asyncio
async def test_comment_lifecycle_and_structure(
    client: AsyncClient, 
    sample_post: models.Post, 
    auth_headers_a: dict, 
    auth_headers_b: dict,
    db_session: AsyncSession
):
    """
    1.1 & 1.2: Create comments, replies, nested replies. Verify flattening (root_id).
    """
    post_id = sample_post.id
    
    # 1. User A creates Root Comment
    resp = await client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Root Comment A"},
        headers=auth_headers_a
    )
    assert resp.status_code == 201
    root_data = resp.json()["data"]
    root_id = root_data["id"]
    assert root_data["root_id"] == root_id
    assert root_data["parent_id"] is None
    
    # Verify Post Comment Count
    await db_session.refresh(sample_post)
    assert sample_post.comment_count == 1
    
    # 2. User B replies to Root (Child 1)
    resp = await client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Reply B to A", "parent_id": root_id},
        headers=auth_headers_b
    )
    assert resp.status_code == 201
    child1_data = resp.json()["data"]
    child1_id = child1_data["id"]
    assert child1_data["root_id"] == root_id  # Should point to Root
    assert child1_data["parent_id"] == root_id
    
    # Verify Post Comment Count
    await db_session.refresh(sample_post)
    assert sample_post.comment_count == 2
    
    # 3. User A replies to Child 1 ("Floor within Floor" -> Should flatten)
    resp = await client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Reply A to B", "parent_id": child1_id},
        headers=auth_headers_a
    )
    assert resp.status_code == 201
    child2_data = resp.json()["data"]
    assert child2_data["root_id"] == root_id # Flattening check! Crucial.
    assert child2_data["parent_id"] == child1_id

    # 4. Verify Root List (Get Comments)
    resp = await client.get(f"/posts/{post_id}/comments")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["pagination"]["total_root_comments"] == 1
    item = data["list"][0]
    assert item["id"] == root_id
    assert item["reply_count"] == 2 # child1 + child2
    
    # 5. Verify Child List
    resp = await client.get(f"/comments/{root_id}/replies")
    assert resp.status_code == 200
    replies = resp.json()["data"]
    assert len(replies) == 2
    # Verify order (Cronological)
    assert replies[0]["id"] == child1_id
    assert replies[1]["id"] == child2_data["id"]


@pytest.mark.asyncio
async def test_ghost_comment_logic(
    client: AsyncClient, 
    sample_post: models.Post, 
    auth_headers_a: dict, 
    auth_headers_b: dict,
    db_session: AsyncSession
):
    """
    3.1: Ghost Comments
    - Create Root -> Reply.
    - Delete Root.
    - Check List: Root should still appear but with filtered content.
    - Delete Reply.
    - Check List: Root should disappear.
    """
    post_id = sample_post.id
    
    # Create Root (User A)
    resp = await client.post(f"/posts/{post_id}/comments", json={"content": "Root"}, headers=auth_headers_a)
    root_id = resp.json()["data"]["id"]
    
    # Create Reply (User B)
    resp = await client.post(f"/posts/{post_id}/comments", json={"content": "Reply", "parent_id": root_id}, headers=auth_headers_b)
    reply_id = resp.json()["data"]["id"]
    
    # Delete Root (User A)
    resp = await client.delete(f"/comments/{root_id}", headers=auth_headers_a)
    assert resp.status_code == 200
    
    # Check List - Should be "Ghost"
    resp = await client.get(f"/posts/{post_id}/comments")
    data = resp.json()["data"]
    assert len(data["list"]) == 1
    ghost = data["list"][0]
    assert ghost["id"] == root_id
    assert ghost["content"] == "该评论已删除"
    assert ghost["user"] is None
    assert ghost["reply_count"] == 1
    
    # Get Replies - Should still get reply
    resp = await client.get(f"/comments/{root_id}/replies")
    assert len(resp.json()["data"]) == 1
    
    # Now Delete Reply (User B)
    resp = await client.delete(f"/comments/{reply_id}", headers=auth_headers_b)
    assert resp.status_code == 200
    
    # Check List - Root should now disappear as it has no valid children
    resp = await client.get(f"/posts/{post_id}/comments")
    data = resp.json()["data"]
    assert len(data["list"]) == 0


@pytest.mark.asyncio
async def test_permission_matrix(
    client: AsyncClient, 
    sample_post: models.Post,
    user_a: models.User, auth_headers_a: dict, 
    user_b: models.User, auth_headers_b: dict, # B is Post Author
    admin_user: models.User, auth_headers_admin: dict,
    user_c: models.User, auth_headers_c: dict,
    db_session: AsyncSession
):
    """
    2.1: Permission Matrix
    Target Comment: Created by User A.
    Post Author: User B.
    
    Scenarios:
    1. A deletes A (Author) -> OK
    2. Admin deletes A -> OK
    3. B deletes A (Post Owner) -> OK
    4. C deletes A (Unauthorized) -> 403
    5. Anon deletes A -> 401
    """
    post_id = sample_post.id
    
    async def create_target_comment():
        resp = await client.post(f"/posts/{post_id}/comments", json={"content": "Target"}, headers=auth_headers_a)
        return resp.json()["data"]["id"]
    
    # 4. User C deletes (Unauthorized)
    cid = await create_target_comment()
    resp = await client.delete(f"/comments/{cid}", headers=auth_headers_c)
    assert resp.status_code == 403
    
    # 5. Anon deletes
    resp = await client.delete(f"/comments/{cid}") # No headers
    assert resp.status_code == 401
    
    # 1. User A deletes (Self)
    resp = await client.delete(f"/comments/{cid}", headers=auth_headers_a)
    assert resp.status_code == 200
    
    # 2. Admin deletes
    cid = await create_target_comment()
    # Ensure current admin_user has id=1 for the logic to work (if logic is hardcoded `id==1`)
    # Check admin id
    assert admin_user.id == 1, "Admin user fixture must have ID 1 for this test"
    
    resp = await client.delete(f"/comments/{cid}", headers=auth_headers_admin)
    assert resp.status_code == 200
    
    # 3. User B (Post Owner) deletes
    cid = await create_target_comment()
    resp = await client.delete(f"/comments/{cid}", headers=auth_headers_b)
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_pagination_and_sorting(
    client: AsyncClient, 
    sample_post: models.Post, 
    auth_headers_a: dict,
):
    """
    1.2: Pagination limits and sorting
    """
    post_id = sample_post.id
    
    # Create 15 comments
    for i in range(15):
        await client.post(f"/posts/{post_id}/comments", json={"content": f"Comment {i}"}, headers=auth_headers_a)
        
    # Page 1 (Size 10)
    resp = await client.get(f"/posts/{post_id}/comments?page=1&pageSize=10")
    data = resp.json()["data"]
    assert len(data["list"]) == 10
    assert data["pagination"]["total"] == 15
    
    # Verify Order (Default Newest First -> Comment 14 should be first)
    first_id = data["list"][0]["id"]
    second_id = data["list"][1]["id"]
    assert first_id > second_id 
    
    # Page 2
    resp = await client.get(f"/posts/{post_id}/comments?page=2&pageSize=10")
    data = resp.json()["data"]
    assert len(data["list"]) == 5

from typing import List, Optional, Sequence, Dict
from datetime import datetime
from sqlalchemy import select, update, desc, func, or_, exists, and_
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas
# from .security import get_password_hash # 导入哈希函数 (Removded for simulation mode)

# =======================
# User CRUD
# =======================
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[models.User]:
    # 新增：用于登录查询
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    # 修改：移除密码哈希处理 (模拟模式)
    # user_data = user.model_dump(exclude={"password"}) 
    # db_user = models.User(**user_data, hashed_password=hashed_pwd)
    
    # 直接使用用户名和头像创建
    db_user = models.User(
        username=user.username,
        avatar_url=user.avatar_url
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user(db: AsyncSession, user_id: int) -> Optional[models.User]:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()

# =======================
# Post CRUD
# =======================
# =======================
# Post CRUD
# =======================
async def create_post(db: AsyncSession, post: schemas.PostCreate, user_id: int) -> models.Post:
    db_post = models.Post(**post.model_dump(), user_id=user_id)
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return db_post

async def get_post(db: AsyncSession, post_id: int) -> Optional[models.Post]:
    stmt = (
        select(models.Post)
        .options(selectinload(models.Post.user))
        .where(models.Post.id == post_id)
        .where(models.Post.is_deleted == False)
    )
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    
    # Increment view count if found (simple implementation)
    if post:
        # Note: This is not concurrency safe for high traffic, use atomic update in real prod
        post.view_count += 1
        await db.commit()
        await db.refresh(post)
    
    return post

async def get_posts(db: AsyncSession, page: int = 1, page_size: int = 10, user_id: Optional[int] = None) -> tuple[Sequence[models.Post], int]:
    skip = (page - 1) * page_size
    
    # Count query
    count_stmt = select(func.count()).select_from(models.Post).where(models.Post.is_deleted == False)
    if user_id is not None:
        count_stmt = count_stmt.where(models.Post.user_id == user_id)
        
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Data query
    stmt = (
        select(models.Post)
        # .options(selectinload(models.Post.user)) # Optimize: Load user if we want to show author name
        .where(models.Post.is_deleted == False)
    )
    
    if user_id is not None:
        stmt = stmt.where(models.Post.user_id == user_id)
        
    stmt = (
        stmt.order_by(desc(models.Post.created_at), desc(models.Post.id))
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    posts = result.scalars().all()
    
    return posts, total

async def delete_post(db: AsyncSession, post_id: int) -> bool:
    stmt = (
        update(models.Post)
        .where(models.Post.id == post_id)
        .values(is_deleted=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


# =======================
# Comment CRUD
# =======================
async def create_comment(db: AsyncSession, comment: schemas.CommentCreate, user_id: int) -> models.Comment:
    # 1. Prepare base data
    db_comment = models.Comment(
        post_id=comment.post_id,
        user_id=user_id,
        content=comment.content,
        parent_id=comment.parent_id,
        reply_to_user_id=comment.reply_to_user_id
    )
    
    # 2. Add to session (don't commit yet)
    db.add(db_comment)
    # Flush to generate ID
    await db.flush() 
    
    # 3. Handle root_id logic
    if comment.parent_id is None:
        # It's a root comment, root_id = its own id
        db_comment.root_id = db_comment.id
    else:
        # It's a reply, find the parent's root_id
        parent_comment = await db.get(models.Comment, comment.parent_id)
        if parent_comment:
            db_comment.root_id = parent_comment.root_id
        else:
            # Fallback or Error? Assuming parent exists or validation caught it.
            # If parent doesn't exist, this might be invalid. 
            # For robustness we effectively treat it as root or raise error.
            db_comment.root_id = db_comment.id 
            
    # 4. Update Post stats (comment_count)
    # Using specific update statement avoids race conditions better than obj.count += 1
    await db.execute(
        update(models.Post)
        .where(models.Post.id == comment.post_id)
        .values(comment_count=models.Post.comment_count + 1)
    )
    
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def get_root_comments(
    db: AsyncSession, post_id: int, page: int = 1, page_size: int = 10, sort: str = "newest"
) -> tuple[Sequence[models.Comment], int]:
    """
    Get paginated root comments for a post.
    """
    skip = (page - 1) * page_size
    
    # Define condition: Valid if not deleted OR (deleted but has active children)
    # We need an alias for the subquery to correlate properly
    ChildComment = aliased(models.Comment)
    
    # Subquery to check for valid children
    has_valid_children = exists(
        select(1)
        .where(ChildComment.root_id == models.Comment.id)
        .where(ChildComment.parent_id != None) # Must be a child
        .where(ChildComment.is_deleted == False)
    )

    filter_condition = or_(
        models.Comment.is_deleted == False,
        and_(models.Comment.is_deleted == True, has_valid_children)
    )

    # Count root comments
    count_stmt = (
        select(func.count())
        .select_from(models.Comment)
        .where(models.Comment.post_id == post_id)
        .where(models.Comment.parent_id == None)
        .where(filter_condition)
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Determine ordering
    # if sort == "hottest":
        # Order by like_count desc, then created_at desc (removed)
    #    order_clause = desc(models.Comment.created_at) 
    # else:
        # Default newest
    order_clause = desc(models.Comment.created_at)

    # Fetch data
    stmt = (
        select(models.Comment)
        .options(selectinload(models.Comment.user))
        .where(models.Comment.post_id == post_id)
        .where(models.Comment.parent_id == None)  # Root comments only
        .where(filter_condition)
        .order_by(order_clause, desc(models.Comment.id))
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return result.scalars().all(), total

async def delete_comment(db: AsyncSession, comment_id: int) -> bool:
    stmt = (
        update(models.Comment)
        .where(models.Comment.id == comment_id)
        .values(is_deleted=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0

async def get_replies_by_root_id(
    db: AsyncSession, root_id: int
) -> Sequence[models.Comment]:
    """
    Get all child replies for a specific root comment.
    """
    stmt = (
        select(models.Comment)
        .options(
            selectinload(models.Comment.user),
            selectinload(models.Comment.reply_to_user)
        )
        .where(models.Comment.root_id == root_id)
        .where(models.Comment.parent_id != None) # Only children
        .where(models.Comment.is_deleted == False)
        .order_by(models.Comment.created_at.asc(), models.Comment.id.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

async def count_replies_for_roots(
    db: AsyncSession, root_ids: List[int]
) -> Dict[int, int]:
    """
    Get existing reply counts for a list of root IDs.
    Returns a dict {root_id: count}
    """
    if not root_ids:
        return {}
        
    stmt = (
        select(models.Comment.root_id, func.count())
        .where(models.Comment.root_id.in_(root_ids))
        .where(models.Comment.parent_id != None)
        .where(models.Comment.is_deleted == False)
        .group_by(models.Comment.root_id)
    )
    result = await db.execute(stmt)
    # result.all() returns list of (root_id, count) tuples
    return dict(result.all())


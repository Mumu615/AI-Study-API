from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud, schemas, database, models, security

app = FastAPI(
    title="学习社区 API",
    description="支持帖子发布、软删除及二级嵌套评论系统的 API 接口。",
    version="1.0"
)

# CORS 配置
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost",
    "http://localhost:3000", # 例如 React/Vue 开发服务器
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://localhost:5173", # Vite Default
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
get_db = database.get_db

# OAuth2 方案 (Token URL指向登录接口)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# =======================
# Authentication Dependency
# =======================
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    核心依赖：验证 Token 并返回当前用户对象
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except security.JWTError:
        raise credentials_exception
        
    user = await crud.get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# =======================
# Routers
# =======================
user_router = APIRouter(prefix="/users", tags=["用户管理"])
post_router = APIRouter(prefix="/posts", tags=["帖子管理"])
comment_router = APIRouter(tags=["评论管理"]) 

# =======================
# Auth / Login Endpoint
# =======================
@app.post("/token", response_model=schemas.Token, summary="用户登录")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    # 1. 验证用户
    user = await crud.get_user_by_username(db, form_data.username)
    # 模拟模式：只检查用户是否存在，不检查密码
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. 生成 Token
    access_token = security.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# =======================
# Users Endpoints
# =======================
@user_router.post("", response_model=schemas.ResponseModel[schemas.UserOut], summary="创建用户")
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """创建新用户"""
    # 检查用户名是否存在
    db_user = await crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = await crud.create_user(db=db, user=user)
    return schemas.ResponseModel(data=new_user)

@user_router.get("/me", response_model=schemas.ResponseModel[schemas.UserOut], summary="获取当前登录用户信息")
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return schemas.ResponseModel(data=current_user)

@user_router.get("/{user_id}", response_model=schemas.ResponseModel[schemas.UserOut], summary="获取用户详情")
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """根据ID获取用户信息"""
    db_user = await crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return schemas.ResponseModel(data=db_user)

# =======================
# Posts Endpoints
# =======================
@post_router.post("", response_model=schemas.ResponseModel[schemas.PostCreatedData], status_code=201, summary="发布帖子")
async def create_post(
    post: schemas.PostCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 必须登录
):
    """发布新的讨论帖"""
    db_post = await crud.create_post(db=db, post=post, user_id=current_user.id)
    return schemas.ResponseModel(
        code=201,
        msg="success",
        data=schemas.PostCreatedData(
            id=db_post.id,
            title=db_post.title,
            created_at=db_post.created_at
        )
    )

@post_router.get("", response_model=schemas.ResponseModel[schemas.PaginatedList[schemas.PostListItem]], summary="获取帖子列表")
async def read_posts(
    page: int = 1, 
    pageSize: int = 10, 
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取分页的帖子列表"""
    posts, total = await crud.get_posts(db, page=page, page_size=pageSize, user_id=user_id)
    
    post_list = []
    for p in posts:
        # Create snippet (first 50 chars)
        snippet = p.content[:50] + "..." if len(p.content) > 50 else p.content
        item = schemas.PostListItem(
            id=p.id,
            user_id=p.user_id,
            title=p.title,
            content_snippet=snippet,
            view_count=p.view_count,
            comment_count=p.comment_count,
            created_at=p.created_at
        )
        post_list.append(item)

    return schemas.ResponseModel(
        data=schemas.PaginatedList(
            pagination=schemas.PaginationData(page=page, pageSize=pageSize, total=total),
            list=post_list
        )
    )

@post_router.get("/{post_id}", response_model=schemas.ResponseModel[schemas.PostDetail], summary="获取帖子详情")
async def read_post(post_id: int, db: AsyncSession = Depends(get_db)):
    """获取单篇帖子的完整内容"""
    db_post = await crud.get_post(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
        
    return schemas.ResponseModel(
        data=schemas.PostDetail(
            id=db_post.id,
            user_id=db_post.user_id,
            title=db_post.title,
            content=db_post.content,
            view_count=db_post.view_count,
            comment_count=db_post.comment_count,
            created_at=db_post.created_at
        )
    )

@post_router.delete("/{post_id}", response_model=schemas.ResponseModel, summary="删除帖子")
async def delete_post(
    post_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 必须登录
):
    """软删除帖子 (仅限作者)"""
    # 1. 先查帖子
    db_post = await crud.get_post(db, post_id=post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 2. 权限检查：当前用户ID 是否等于 帖子作者ID
    if db_post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    success = await crud.delete_post(db, post_id=post_id)
    if not success:
         raise HTTPException(status_code=404, detail="Post not found")
    return schemas.ResponseModel(msg="success")

# =======================
# Comments Endpoints
# =======================
@comment_router.post("/posts/{post_id}/comments", response_model=schemas.ResponseModel[schemas.CommentCreatedData], status_code=201, summary="发布评论")
async def create_comment(
    post_id: int, 
    comment: schemas.CommentCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 必须登录
):
    """
    发布评论（支持根评论和子回复）。
    - parent_id 为空：根评论
    - parent_id 有值：子回复
    """
    # Override post_id in schema with path param to be safe/consistent
    comment.post_id = post_id
    
    # 使用当前登录用户
    db_comment = await crud.create_comment(db=db, comment=comment, user_id=current_user.id)
    
    return schemas.ResponseModel(
        code=201,
        msg="success",
        data=schemas.CommentCreatedData(
            id=db_comment.id,
            root_id=db_comment.root_id,
            parent_id=db_comment.parent_id,
            content=db_comment.content
        )
    )

@comment_router.get("/posts/{post_id}/comments", response_model=schemas.ResponseModel[schemas.CommentListResponse], summary="获取评论列表")
async def read_post_comments(
    post_id: int, 
    page: int = 1, 
    pageSize: int = 10, 
    sort: str = "newest",
    db: AsyncSession = Depends(get_db)
):
    """
    获取帖子下的评论列表（仅返回根评论 + 回复数量）。
    """
    # 1. Get roots and total count
    root_comments, total = await crud.get_root_comments(db, post_id=post_id, page=page, page_size=pageSize, sort=sort)
    
    # 2. Get reply counts
    root_ids = [c.id for c in root_comments]
    reply_counts_map = await crud.count_replies_for_roots(db, root_ids)
    
    # 3. Assemble
    root_list: List[schemas.CommentListItem] = []
    for root in root_comments:
        root_item = schemas.CommentListItem.model_validate(root)
        root_item.reply_count = reply_counts_map.get(root.id, 0)
        root_item.replies = [] # No replies returned initially
        
        # Edge Case A: Root deleted but has children
        if root.is_deleted:
            root_item.content = "该评论已删除"
            root_item.user = None
            
        root_list.append(root_item)

    return schemas.ResponseModel(
        data=schemas.CommentListResponse(
            pagination=schemas.PaginationData(
                page=page, 
                pageSize=pageSize, 
                total=total, 
                total_root_comments=total
            ),
            list=root_list
        )
    )

@comment_router.get("/comments/{comment_id}/replies", response_model=schemas.ResponseModel[List[schemas.CommentListItem]], summary="获取子回复")
async def read_comment_replies(
    comment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定根评论下的所有子回复
    """
    # Check if root exists (optional, but good for 404)
    # For performance we might skip, but let's be safe
    # db_comment = await db.get(models.Comment, comment_id)
    # if not db_comment: ...
    
    replies = await crud.get_replies_by_root_id(db, root_id=comment_id)
    
    # Convert to schema
    reply_list = []
    for r in replies:
        item = schemas.CommentListItem.model_validate(r)
        reply_list.append(item)
        
    return schemas.ResponseModel(data=reply_list)

@comment_router.delete("/comments/{comment_id}", response_model=schemas.ResponseModel, summary="删除评论")
async def delete_comment(
    comment_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # 必须登录
):
    """软删除评论 (仅限作者或管理员-id=1)"""
    # 1. 查评论
    # 我们需要获取评论详情来检查作者，这里简单用 db.get 
    db_comment = await db.get(models.Comment, comment_id)
    
    if not db_comment or db_comment.is_deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    # 2. 权限检查
    # userid=1为管理员，可以删除所有人的评论，且自己的帖子下可以删除别人的评论
    # 逻辑：
    # if current_user.id == 1: pass (Admin)
    # elif current_user.id == db_comment.user_id: pass (Owner)
    # elif (current_user.id == post_owner_id): pass (Post Owner - need to fetch post)
    
    # 按照需求: "删除时，代码先对比 db_obj.user_id == current_user.id，如果不是本人则报 403 错误。userid=1为管理员，可以删除所有人的评论，且自己的帖子下可以删除别人的评论"
    
    is_admin = (current_user.id == 1)
    is_author = (current_user.id == db_comment.user_id)
    
    if is_admin or is_author:
        pass # Allow
    else:
        # Check Post Owner
        # Need to fetch post to check owner
        db_post = await db.get(models.Post, db_comment.post_id)
        if db_post and db_post.user_id == current_user.id:
            pass # Allow (Post Owner)
        else:
             raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    success = await crud.delete_comment(db, comment_id=comment_id)
    if not success:
         raise HTTPException(status_code=404, detail="Comment not found")
    return schemas.ResponseModel(msg="success")

# Register Routers
app.include_router(user_router)
app.include_router(post_router)
app.include_router(comment_router)

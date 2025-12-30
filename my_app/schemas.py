from datetime import datetime
from typing import Optional, List, Generic, TypeVar, Any
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# =======================
# Common Response wrapper
# =======================
class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: Optional[T] = None

# --- 新增 Token Schema ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class PaginationData(BaseModel):
    page: int
    pageSize: int
    total: int
    # Specific field for comments as per doc, but we can make it generic or use alias
    # The doc says "total" for posts, "total_root_comments" for comments.
    # We can handle this by using a loose schema or specific subclass, 
    # but for simplicity let's stick to 'total' and mapping it, 
    # or allow extra fields via strict=False (default).
    total_root_comments: Optional[int] = None 

class PaginatedList(BaseModel, Generic[T]):
    pagination: PaginationData
    list: List[T]

# =======================
# User Schemas
# =======================
class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=255)

class UserCreate(UserBase):
    password: Optional[str] = Field(None, description="用户密码 (仅用于模拟，不存储)")

class UserOut(UserBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# =======================
# Comment Schemas
# =======================
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    # post_id is passed in URL usually, but we keep it here if needed or extract from URL
    post_id: Optional[int] = None
    # user_id: int  <-- removed, inferred from token 
    parent_id: Optional[int] = None
    reply_to_user_id: Optional[int] = None

class CommentCreatedData(BaseModel):
    id: int
    root_id: int
    parent_id: Optional[int]
    content: str
    model_config = ConfigDict(from_attributes=True)

class CommentListItem(BaseModel):
    id: int
    user: Optional[UserOut] = None
    # Reply to user info
    reply_to_user: Optional[UserOut] = None 
    
    content: str
    # like_count: int = 0
    created_at: datetime
    is_deleted: bool
    parent_id: Optional[int] = None
    root_id: Optional[int] = None
    
    # Nested replies (Initially empty, loaded on demand)
    replies: List["CommentListItem"] = []
    reply_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class CommentListResponse(BaseModel):
    pagination: PaginationData
    list: List[CommentListItem]


# =======================
# Post Schemas
# =======================
class PostBase(BaseModel):
    title: str = Field(..., max_length=100)

class PostCreate(PostBase):
    # user_id: int <-- removed, inferred from token
    content: str

class PostCreatedData(BaseModel):
    id: int
    title: str
    created_at: datetime

class PostListItem(PostBase):
    id: int
    user_id: int
    content_snippet: str
    view_count: int
    comment_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PostDetail(PostBase):
    id: int
    user_id: int
    content: str
    view_count: int
    comment_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

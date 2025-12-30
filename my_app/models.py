from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="头像URL")
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), comment="创建时间"
    )

    # Relationships
    # Relationships
    posts: Mapped[List["Post"]] = relationship(back_populates="user", primaryjoin="User.id == Post.user_id")
    comments: Mapped[List["Comment"]] = relationship("Comment", foreign_keys="Comment.user_id", back_populates="user")

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="作者ID")
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="帖子标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="帖子内容")
    
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="软删除标记")
    
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[List["Comment"]] = relationship(back_populates="post")

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"), nullable=False, comment="归属的帖子ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="评论发布者ID")
    
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="父评论ID")
    root_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="所属的根评论ID")
    reply_to_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="被回复的用户ID")
    
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评论内容")
    # like_count removed
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, comment="软删除标记")
    
    created_at: Mapped[datetime] = mapped_column(
        insert_default=func.now(), comment="创建时间"
    )

    # Relationships
    post: Mapped["Post"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="comments")
    reply_to_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reply_to_user_id])
    
    # Optional: Logic relationships for nested comments usually handled by query, 
    # but we can declare them if needed.

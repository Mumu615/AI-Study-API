import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from my_app.main import app, get_db
from my_app.database import Base
from my_app import models, security

# Use in-memory SQLite for testing
# check_same_thread=False is needed for SQLite with asyncio
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport to avoid "Event loop is closed" issues? 
    # Or just standard AsyncClient(app=app, base_url="http://test")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
        
    app.dependency_overrides.clear()

# =======================
# User Fixtures
# =======================

@pytest_asyncio.fixture(scope="function")
async def user_a(db_session: AsyncSession) -> models.User:
    """Create a regular user A"""
    user = models.User(username="user_a", avatar_url="http://a.com/pic")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture(scope="function")
async def user_token_a(user_a: models.User) -> str:
    """Return a valid token for user_a"""
    return security.create_access_token(data={"sub": user_a.username})

@pytest_asyncio.fixture(scope="function")
async def auth_headers_a(user_token_a: str) -> dict:
    return {"Authorization": f"Bearer {user_token_a}"}

@pytest_asyncio.fixture(scope="function")
async def user_b(db_session: AsyncSession) -> models.User:
    """Create a regular user B"""
    user = models.User(username="user_b", avatar_url="http://b.com/pic")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest_asyncio.fixture(scope="function")
async def user_token_b(user_b: models.User) -> str:
    """Return a valid token for user_b"""
    return security.create_access_token(data={"sub": user_b.username})

@pytest_asyncio.fixture(scope="function")
async def auth_headers_b(user_token_b: str) -> dict:
    return {"Authorization": f"Bearer {user_token_b}"}

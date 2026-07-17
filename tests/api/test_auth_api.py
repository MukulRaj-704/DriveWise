"""API-level tests for auth endpoints, run against an in-memory SQLite DB
(swapping out the Postgres dependency purely for test speed/isolation)."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "full_name": "Test User", "password": "password123"},
    )
    assert register_resp.status_code == 201
    assert register_resp.json()["email"] == "test@example.com"

    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "test@example.com", "password": "password123"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_duplicate_registration_fails(client: AsyncClient):
    payload = {"email": "dup@example.com", "full_name": "Dup", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_with_wrong_password_fails(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "full_name": "W", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "wrong@example.com", "password": "nope12345"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/brochure")
    assert resp.status_code == 401

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    r = await client.post("/auth/register-tenant", json={
        "tenant_name": "TestCo",
        "admin_email": "admin@test.app",
        "admin_password": "secret123",
    })
    assert r.status_code == 201, r.text

    r = await client.post("/auth/login", data={
        "username": "admin@test.app",
        "password": "secret123",
    })
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]


@pytest.mark.asyncio
async def test_login_bad_password(client):
    await client.post("/auth/register-tenant", json={
        "tenant_name": "BadCo",
        "admin_email": "a@bad.app",
        "admin_password": "secret123",
    })
    r = await client.post("/auth/login", data={"username": "a@bad.app", "password": "wrong"})
    assert r.status_code == 401

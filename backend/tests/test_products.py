import pytest


async def _signup_and_token(client) -> str:
    await client.post("/auth/register-tenant", json={
        "tenant_name": "ProdCo",
        "admin_email": "a@prod.app",
        "admin_password": "secret123",
    })
    r = await client.post("/auth/login", data={"username": "a@prod.app", "password": "secret123"})
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_product(client):
    token = await _signup_and_token(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/products", headers=h, json={
        "sku": "TEST-1",
        "name": "Test Item",
        "category": "Misc",
        "unit_price": 99.5,
        "stock": 50,
        "reorder_threshold": 10,
    })
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = await client.get("/products", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert any(p["id"] == pid for p in r.json()["items"])


@pytest.mark.asyncio
async def test_forecast_endpoint(client):
    token = await _signup_and_token(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/products", headers=h, json={
        "sku": "FC-1", "name": "Forecast", "category": "X", "unit_price": 10, "stock": 100,
    })
    pid = r.json()["id"]
    r = await client.get(f"/products/{pid}/forecast", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["product_id"] == pid
    assert len(body["points"]) == 7

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.tenant import Tenant
from app.models.user import User
from app.models.product import Product
from app.services.ai_tools import get_low_stock_products, get_expiring_products
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_get_low_stock_products_filters_by_tenant(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        t = Tenant(name="ToolCo")
        db.add(t)
        await db.flush()
        db.add(User(tenant_id=t.id, email="x@y.z", password_hash="x", role="admin"))
        db.add(Product(tenant_id=t.id, sku="L1", name="Low", category="X", unit_price=10, stock=2, reorder_threshold=10))
        db.add(Product(tenant_id=t.id, sku="OK", name="Ok", category="X", unit_price=10, stock=100, reorder_threshold=10))
        await db.commit()

        out = await get_low_stock_products(db, t.id)
        assert out["count"] == 1
        assert out["products"][0]["sku"] == "L1"


@pytest.mark.asyncio
async def test_get_expiring_products(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as db:
        t = Tenant(name="ExpCo")
        db.add(t)
        await db.flush()
        db.add(Product(tenant_id=t.id, sku="E1", name="Soon", category="X", unit_price=10,
                       stock=5, expiry_date=date.today() + timedelta(days=3)))
        db.add(Product(tenant_id=t.id, sku="E2", name="Later", category="X", unit_price=10,
                       stock=5, expiry_date=date.today() + timedelta(days=90)))
        await db.commit()

        out = await get_expiring_products(db, t.id, days_ahead=14)
        assert out["count"] == 1
        assert out["products"][0]["sku"] == "E1"

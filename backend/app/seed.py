"""Idempotent seed script. Run inside the backend container after alembic upgrade.

Creates:
- 2 tenants (Raj Grocery + Demo Mart) — exercises multi-tenancy
- admin + staff per tenant
- ~20 products spread across categories with realistic stock levels
- 3 suppliers per tenant
- 30 days of stock movements
"""
import asyncio
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.tenant import Tenant
from app.models.user import User

CATALOGUE = [
    ("RICE-5KG", "Basmati Rice 5kg", "Grains", 540.0, 50),
    ("WHEAT-10K", "Wheat Flour 10kg", "Grains", 480.0, 30),
    ("SUGAR-1KG", "White Sugar 1kg", "Pantry", 48.0, 80),
    ("OIL-1L", "Sunflower Oil 1L", "Pantry", 155.0, 60),
    ("SALT-1KG", "Iodised Salt 1kg", "Pantry", 22.0, 120),
    ("MILK-1L", "Toned Milk 1L", "Dairy", 56.0, 45),
    ("BUTTER-500", "Butter 500g", "Dairy", 290.0, 20),
    ("CHEESE-200", "Cheese Slices 200g", "Dairy", 165.0, 18),
    ("BREAD-400", "Brown Bread 400g", "Bakery", 60.0, 25),
    ("BISCUITS-200", "Marie Biscuits 200g", "Snacks", 35.0, 90),
    ("CHIPS-100", "Potato Chips 100g", "Snacks", 30.0, 110),
    ("COLA-1L", "Cola 1L Bottle", "Beverages", 70.0, 70),
    ("WATER-2L", "Mineral Water 2L", "Beverages", 35.0, 200),
    ("DETER-1KG", "Detergent Powder 1kg", "Household", 220.0, 35),
    ("SOAP-100", "Bath Soap 100g", "Personal Care", 45.0, 95),
    ("SHAMPOO-200", "Shampoo 200ml", "Personal Care", 175.0, 28),
    ("EGG-12", "Eggs (12 pack)", "Dairy", 90.0, 60),
    ("TEA-500", "Tea Powder 500g", "Beverages", 285.0, 38),
    ("COFFEE-200", "Instant Coffee 200g", "Beverages", 420.0, 22),
    ("DAL-1KG", "Toor Dal 1kg", "Grains", 175.0, 55),
]


async def _seed_tenant(db, tenant_name: str, admin_email: str, admin_pw: str, staff_email: str, staff_pw: str) -> None:
    existing = (await db.execute(select(Tenant).where(Tenant.name == tenant_name))).scalar_one_or_none()
    if existing:
        print(f"[seed] tenant '{tenant_name}' already exists, skipping")
        return

    tenant = Tenant(name=tenant_name)
    db.add(tenant)
    await db.flush()

    db.add(User(tenant_id=tenant.id, email=admin_email, password_hash=hash_password(admin_pw), role="admin"))
    db.add(User(tenant_id=tenant.id, email=staff_email, password_hash=hash_password(staff_pw), role="staff"))

    suppliers = [
        Supplier(tenant_id=tenant.id, name="Krishna Distributors", email="krishna@example.com",
                 categories=["Grains", "Pantry"], lead_time_days=3),
        Supplier(tenant_id=tenant.id, name="Annapurna Dairy", email="dairy@example.com",
                 categories=["Dairy", "Bakery"], lead_time_days=2),
        Supplier(tenant_id=tenant.id, name="Bharat FMCG", email="bharat@example.com",
                 categories=["Snacks", "Beverages", "Household", "Personal Care"], lead_time_days=5),
    ]
    for s in suppliers:
        db.add(s)
    await db.flush()
    sup_by_cat: dict[str, int] = {}
    for s in suppliers:
        for c in s.categories:
            sup_by_cat.setdefault(c, s.id)

    today = date.today()
    products: list[Product] = []
    for i, (sku, name, cat, price, stock) in enumerate(CATALOGUE):
        # force some low-stock and one expired for visible badges
        if i % 6 == 0:
            stock = max(stock // 6, 0)
        expiry = today + timedelta(days=random.choice([7, 30, 90, 180, 365]))
        if i == 5:
            expiry = today - timedelta(days=2)  # expired
        if i == 8:
            expiry = today + timedelta(days=5)  # near expiry
        p = Product(
            tenant_id=tenant.id, sku=sku, name=name, category=cat,
            stock=stock, unit_price=price, expiry_date=expiry,
            reorder_threshold=max(stock // 3, 5),
            preferred_supplier_id=sup_by_cat.get(cat),
        )
        products.append(p)
        db.add(p)
    await db.flush()

    # 30 days of stock movements — random small outflows + initial receive
    now = datetime.now(timezone.utc)
    for p in products:
        db.add(StockMovement(tenant_id=tenant.id, product_id=p.id, delta=p.stock, source="initial",
                             ts=now - timedelta(days=30)))
        for d in range(30):
            if random.random() < 0.65:
                qty = random.randint(1, max(p.stock // 8, 1))
                db.add(StockMovement(
                    tenant_id=tenant.id, product_id=p.id, delta=-qty, source="sale",
                    ts=now - timedelta(days=30 - d, hours=random.randint(0, 23)),
                ))
    await db.commit()
    print(f"[seed] tenant '{tenant_name}' created: {len(products)} products, {len(suppliers)} suppliers")


async def main() -> None:
    s = get_settings()
    async with AsyncSessionLocal() as db:
        await _seed_tenant(db, s.SEED_TENANT_NAME, s.SEED_ADMIN_EMAIL, s.SEED_ADMIN_PASSWORD,
                           s.SEED_STAFF_EMAIL, s.SEED_STAFF_PASSWORD)
        await _seed_tenant(db, "Demo Mart", "admin2@smartstore.app", "admin123",
                           "staff2@smartstore.app", "staff123")


if __name__ == "__main__":
    asyncio.run(main())

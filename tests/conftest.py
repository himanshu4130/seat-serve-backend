import os
import time

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
# Force-empty regardless of a real project URL sitting in the local .env —
# tests sign their own tokens with the HS256 secret above and must never
# take the JWKS verification path (which would try to reach a real project).
os.environ["SUPABASE_URL"] = ""

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.deps import get_payment_provider
from app.core.db import Base, get_db
from app.main import app
from app.models.billing import Plan, PlanId
from app.services.payments.base import PaymentProvider, ProviderOrder, ProviderRefund

TEST_SECRET = "test-secret"


class FakePaymentProvider(PaymentProvider):
    """Deterministic stand-in for Razorpay so payment flows are testable
    without real credentials or a network call. Signatures are just
    "valid:{order}:{payment}" — verify_payment_signature checks the exact
    shape a real provider would, only the crypto is swapped for a stub."""

    def __init__(self):
        self.created_orders: list[str] = []
        self.refunded_payments: list[str] = []

    async def create_order(self, *, amount: float, currency: str, receipt: str) -> ProviderOrder:
        order_id = f"order_fake_{len(self.created_orders) + 1}"
        self.created_orders.append(order_id)
        return ProviderOrder(
            provider_order_id=order_id, amount_minor=int(amount * 100), currency=currency, key_id="rzp_test_key"
        )

    def verify_payment_signature(self, *, provider_order_id: str, provider_payment_id: str, signature: str) -> bool:
        return signature == f"valid:{provider_order_id}:{provider_payment_id}"

    def verify_webhook_signature(self, *, payload: bytes, signature: str) -> bool:
        return signature == "valid-webhook-signature"

    async def create_refund(self, *, provider_payment_id: str, amount: float) -> ProviderRefund:
        self.refunded_payments.append(provider_payment_id)
        return ProviderRefund(provider_refund_id=f"rfnd_fake_{len(self.refunded_payments)}", status="processed")


@pytest.fixture
def fake_payment_provider():
    provider = FakePaymentProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    try:
        yield provider
    finally:
        app.dependency_overrides.pop(get_payment_provider, None)


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    # `create_all` builds tables from the ORM metadata only — it skips the
    # data seeded by the migration (see 4393992ae154's `plans` bulk_insert).
    # Business creation FKs a Subscription to a Plan, so tests need this too.
    async with session_maker() as seed_session:
        seed_session.add_all(
            [
                Plan(id=PlanId.STARTER, name="Starter", price=999, features=""),
                Plan(id=PlanId.GROWTH, name="Growth", price=2499, features=""),
                Plan(id=PlanId.SCALE, name="Scale", price=4999, features=""),
            ]
        )
        await seed_session.commit()

    async def _override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        async with session_maker() as session:
            yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def make_token(*, sub: str, email: str, name: str = "") -> str:
    payload = {
        "sub": sub,
        "email": email,
        "user_metadata": {"name": name},
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


@pytest.fixture
def auth_headers():
    def _headers(*, sub: str, email: str, name: str = "") -> dict[str, str]:
        token = make_token(sub=sub, email=email, name=name)
        return {"Authorization": f"Bearer {token}"}

    return _headers

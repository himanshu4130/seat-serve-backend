# SeatServe API

FastAPI backend for SeatServe, backed by Supabase Postgres. Kept as a separate repo
from the frontend (`seat-serve-showcase`) on purpose — this is the real implementation
that will eventually sit behind the frontend's `src/services/*.service.ts` layer,
replacing its current in-memory mock repositories.

## Architecture

Clean layering, one direction of dependency:

```
api/        FastAPI routers — thin, no business logic
services/   business rules (e.g. "creating a business also makes you its OWNER")
repositories/  the only layer that talks to the database
models/     SQLAlchemy ORM models
schemas/    Pydantic request/response models
core/       config, DB session, auth (Supabase JWT verification), RBAC
```

**Auth**: Supabase Auth owns signup/login/password-reset. This API only verifies the
JWT Supabase issues (`SUPABASE_JWT_SECRET`) and just-in-time provisions a matching row
in our own `users` table the first time it sees a given Supabase user id. That same
first request also links any pending staff invite for that email (see Staff below).

**RBAC**: enforced here, not via Postgres Row-Level Security — this API is the only
thing with a direct Postgres connection. A user's role is scoped **per business**
(`staff_business_roles`), so someone can be `OWNER` of one business and have no access
to another. Platform staff are a separate `users.is_platform_admin` flag, not a
per-business role — see `app/core/permissions.py` for the full Role/Permission matrix,
which is kept in sync by hand with the frontend's `src/types/staff.ts`.

**Multi-tenancy**: every business-scoped route takes `business_id` in the path and
resolves the caller's role for that specific business via `require_business_permission`
(`app/api/v1/deps.py`) — there is no implicit "current business" on the server side,
matching the frontend's own `businessId`-keyed service/hook layer.

## Domains implemented

Everything the frontend's admin/staff/customer surfaces need, end to end:

- **Identity/tenant/business** — `tenants`, `users`, `businesses`, `staff_business_roles`.
- **Menu** — categories, items, per-item addons (`app/api/v1/menu.py`).
- **Service points & QR** — areas, service points (`SEAT`/`TABLE`/`ROOM`/`CABANA`/`CHAIR`/
  `COUNTER`/`CUSTOM`), and QR codes with a stable public `slug` — the `/v/{tenantSlug}/
  {servicePoint}` routing key the frontend's `QRCode.slug` field anticipates (Phase 4
  there; already the canonical lookup key here via `GET /api/v1/public/qr/{slug}`).
- **Orders** — public (unauthenticated) order placement from a QR scan, with **prices
  always recomputed server-side** from the current menu (the client only ever sends
  item ids/qty/addon names, never a price); staff-side status flow (`NEW → ACCEPTED →
  PREPARING → READY → OUT_FOR_DELIVERY → DELIVERED`, matching the frontend's
  `ORDER_FLOW`) plus `CANCELLED`/`REFUNDED`, which the frontend doesn't have UI for yet
  but a real payments backend needs.
- **Staff & roles** — invite by email (before that person has ever signed in), role
  and status (`ACTIVE`/`INVITED`/`DISABLED`) management, with a guard against ever
  disabling/demoting a business's last active `OWNER`.
- **Payments** — a provider-agnostic interface (`app/services/payments/base.py`) with a
  real Razorpay adapter (`razorpay_provider.py`): order creation, HMAC signature
  verification for both the client-side payment-verify call and inbound webhooks, and
  refunds. **Nothing here fakes a successful payment** — if `RAZORPAY_KEY_ID`/
  `RAZORPAY_KEY_SECRET` aren't set, payment-creating endpoints return `503` rather than
  pretending to succeed. Webhook events are logged and deduplicated
  (`payment_webhook_events`) so a redelivery is a safe no-op.
- **Billing/subscriptions** — a seeded plan catalog (`STARTER`/`GROWTH`/`SCALE`,
  seeded by the migration), a `Subscription` per business (canonical source of truth —
  `Business.subscription_state` is a denormalized read-model column kept in sync, per
  the frontend's own comment on that field), and invoices payable through the same
  Razorpay adapter.
- **Analytics** — real aggregation over actual orders (revenue, average order value,
  top products, hourly breakdown) — no `Math.random()` placeholders like the frontend's
  current `admin.reports.tsx`. `revenue` figures (top-level and hourly) only count
  **paid** orders; `order_count`/top-products reflect all non-cancelled/refunded orders
  regardless of payment timing (kitchen-relevant demand vs. money actually collected).
- **Platform/superadmin** — tenant/business rollups and platform-wide analytics,
  gated on `users.is_platform_admin` (`app/api/v1/platform.py`).

## What's still a real gap

- **Payment provider credentials**: no Razorpay account exists yet. Everything up to
  the actual provider call is real and tested (order lifecycle, signature verification
  logic, webhook idempotency, refund state machine) — only `RAZORPAY_KEY_ID` /
  `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET` are missing. Once they exist, set
  them in `.env` and payments start working with no code change.
- **File/image upload**: the frontend doesn't upload menu photos or business logos
  either (see the audit) — `MenuItem.image`/onboarding logo are plain string fields
  today. Add a storage-backed upload endpoint when the frontend actually needs one.
  Menu images are recorded as the URL string sent from the client, not validated or
  hosted here.
- **Realtime order updates**: the frontend has no polling/websocket wiring yet either
  (see the audit) — the API is request/response only. Wire up polling, SSE, or Supabase
  Realtime once the frontend's order-tracking views need live updates.

## Running locally

Requires [Poetry](https://python-poetry.org/). This repo is configured to create its
virtualenv at `.venv/` (see `poetry.toml`).

```bash
poetry install

cp .env.example .env
# Fill in DATABASE_URL and SUPABASE_JWT_SECRET from your Supabase project settings.
# Leave RAZORPAY_* blank for local dev — payment-creating endpoints return 503
# instead of faking success; everything else works without them.

poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Without a real `.env`, `app/core/config.py` falls back to a local SQLite file and a
clearly-labeled test JWT secret — enough to run `pytest` and boot the app, but **not**
a substitute for testing against your actual Supabase project once credentials exist.
The initial data migration seeds the `plans` table (`STARTER`/`GROWTH`/`SCALE`) — every
business needs one of these to exist for its `Subscription` FK, so always run
`alembic upgrade head` (not just `create_all`) against a fresh database.

## Tests

```bash
poetry run pytest -q
```

Runs entirely against an in-memory SQLite DB (with `PRAGMA foreign_keys=ON`, so FK
violations that only Postgres would normally catch fail loudly here too) and a
locally-signed fake JWT — no network or real Supabase project required. A
`fake_payment_provider` fixture (`tests/conftest.py`) stands in for Razorpay so the
full payment/refund/webhook state machine is exercised without real credentials or
network calls. Covers: JWT verification + just-in-time user provisioning and staff
invite linking, business creation, per-business tenant isolation, the platform-admin
bypass, menu CRUD + permission gating, service points/QR (including that disabling a
QR 404s its public lookup), order creation with server-side price recomputation and
status-transition validation, payment create/verify/refund/webhook-idempotency, the
last-owner-can't-be-disabled guard, billing/subscription, and analytics correctness
(including that revenue only counts paid orders).

## What's NOT verified yet

This sandbox has no Docker/Postgres and no real Supabase or Razorpay credentials were
available while building this. Everything above was verified against SQLite plus the
fake payment provider. Before relying on this in production:

1. Fill in real `DATABASE_URL` / `SUPABASE_JWT_SECRET` in `.env`.
2. Run `alembic upgrade head` against the real Supabase Postgres instance.
3. Get a real access token from your Supabase project (sign in via Supabase Auth) and
   confirm `GET /api/v1/me` works with it.
4. Fill in real `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` / `RAZORPAY_WEBHOOK_SECRET`
   and, in the Razorpay Dashboard, point the webhook URL at
   `POST /api/v1/webhooks/razorpay`. Test one real payment end to end (create order →
   pay via the Razorpay checkout widget with the returned `key_id` → verify) before
   trusting it with real money.
5. Re-run `pytest` — it should still pass unchanged (it doesn't touch the real DB or
   the real Razorpay API).

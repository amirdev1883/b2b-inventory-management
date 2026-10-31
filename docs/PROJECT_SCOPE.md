# Project scope

## Goal

A multi-tenant B2B inventory and order platform for small businesses, retailers, distributors and warehouse teams.

## Implemented MVP

| Requirement | Implementation |
| --- | --- |
| Multi-tenant support | Every business record is scoped to the authenticated user’s tenant; related fields are scoped too |
| Authentication and roles | Business registration, JWT access, rotating HttpOnly refresh cookies, logout, recovery/change-password; Admin/Manager/Staff |
| Product/inventory CRUD | Product and supplier management, archive/reactivation, validated prices, stock adjustment service and immutable API stock ledger |
| Supplier/purchasing | Supplier details and draft purchase orders; atomic full receipt and cancellation |
| Sales/PDF invoicing | Draft editing, stock reservation, shipment, cancellation, payment status and preserved invoice details |
| Low-stock email | Celery hourly scan, tenant-specific admin/manager recipients, 24-hour suppression and replenishment reset |
| Analytics | Shipped revenue before tax, inventory valuation, open orders, low stock, 30 daily UTC buckets |
| Basic React UI | Responsive authenticated workspace for every MVP operation, with loading/error/empty states and role-aware actions |
| Docker development | PostgreSQL, Redis, Django, Vite, Celery worker and a single beat scheduler |
| API documentation | Generated OpenAPI schema, Swagger and ReDoc |
| CI/CD | PostgreSQL business/concurrency tests, frontend tests, Chromium workflows, production image checks; tested tagged GHCR releases |

## Boundaries

- A user belongs to one business. Email addresses are globally unique, case-insensitively.
- One stock balance per product; whole units only.
- One currency per business, fixed at creation; CAD, USD, EUR, GBP and AUD are supported.
- Purchase receipt and sales shipment apply to the full order. Confirmed orders are immutable except payment status and lifecycle actions.
- One tax percentage per order. Rounding is decimal, half-up, to two places.
- No payment gateway, public storefront, returns/refund processing, partial deliveries, FX conversion, mobile app or multilingual UI.

## Operational setup

Configure production PostgreSQL, HTTPS, secrets, Redis and SMTP before deployment. Hosting and external accounts remain operator-managed. SQLite is a development convenience and cannot validate concurrent stock correctness.

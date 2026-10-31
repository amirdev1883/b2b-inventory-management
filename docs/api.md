# API guide

Interactive docs: `/api/docs/`. ReDoc: `/api/redoc/`. OpenAPI schema: `/api/schema/`.

## Authentication

1. `GET /api/auth/csrf/` sets the CSRF cookie and returns `csrfToken`.
2. `POST /api/auth/register/` or `/api/auth/login/` with `X-CSRFToken` returns `{access, user, business}` and an HttpOnly refresh cookie.
3. Send `Authorization: Bearer <access>` to protected API routes.
4. `POST /api/auth/refresh/` uses the refresh cookie plus CSRF header and rotates the session.
5. `POST /api/auth/logout/` blacklists that refresh session and removes the cookie.

Example login body:

```json
{"email":"owner@example.com","password":"your-own-password"}
```

Registration also requires `business_name` and `first_name`; optional `currency` defaults to `CAD`. Never place a refresh token in localStorage or send a tenant identifier to select a business.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/auth/me/` | GET | Current user |
| `/api/auth/password-change/` | POST | Verify `current_password`, set `new_password`, return a new session |
| `/api/auth/password-reset/` | POST | Request reset with `email`; generic response |
| `/api/auth/password-reset/confirm/` | POST | Set `password` with reset `uid` and `token`; links expire in one hour |
| `/api/business/` | GET/PATCH | Business profile; currency cannot be edited |
| `/api/users/` | GET/POST | Team members; admin only |
| `/api/users/{id}/` | GET/PUT/PATCH | Team account; deactivate rather than delete |
| `/api/products/` | GET/POST | Product catalog |
| `/api/products/{id}/` | GET/PUT/PATCH/DELETE | Product details; historical references prevent deletion |
| `/api/products/{id}/adjust/` | POST | `quantity_delta` and mandatory `note` |
| `/api/suppliers/` | GET/POST | Suppliers |
| `/api/suppliers/{id}/` | GET/PUT/PATCH/DELETE | Supplier details; historical references prevent deletion |
| `/api/stock-movements/` | GET | Searchable read-only stock ledger |
| `/api/sales-orders/` | GET/POST | Sales drafts |
| `/api/sales-orders/{id}/` | GET/PUT/PATCH | Draft details/editing |
| `/api/sales-orders/{id}/confirm/` | POST | Reserve all line quantities |
| `/api/sales-orders/{id}/ship/` | POST | Ship all reserved lines |
| `/api/sales-orders/{id}/cancel/` | POST | Cancel before shipment |
| `/api/sales-orders/{id}/payment/` | POST | `payment_status`: `PAID` or `UNPAID` |
| `/api/sales-orders/{id}/invoice/` | GET | Download PDF after confirmation |
| `/api/purchase-orders/` | GET/POST | Purchase drafts |
| `/api/purchase-orders/{id}/` | GET/PUT/PATCH | Draft details/editing |
| `/api/purchase-orders/{id}/receive/` | POST | Receive full order into stock |
| `/api/purchase-orders/{id}/cancel/` | POST | Cancel before receipt |
| `/api/analytics/dashboard/` | GET | Tenant-scoped business metrics |

## Permissions

| Action | Admin | Manager | Staff |
| --- | :---: | :---: | :---: |
| View business/catalog/orders/ledger/analytics | ✓ | ✓ | ✓ |
| Create/edit sales drafts | ✓ | ✓ | ✓ |
| Create/edit/archive products and suppliers | ✓ | ✓ | — |
| Adjust inventory | ✓ | ✓ | — |
| Create/edit/receive/cancel purchases | ✓ | ✓ | — |
| Confirm/ship/cancel sales; record payment | ✓ | ✓ | — |
| Download eligible invoices | ✓ | ✓ | ✓ |
| Change own password | ✓ | ✓ | ✓ |
| Manage team and business details | ✓ | — | — |

## Order bodies

```json
{
  "customer_name": "Cedar Studio",
  "customer_email": "orders@example.com",
  "tax_rate": "13.00",
  "items": [
    {"product": "product-uuid", "quantity": 3, "unit_price": "25.25"}
  ]
}
```

For purchases, replace the customer fields with `supplier: "supplier-uuid"`. Omitted line prices default to the product’s sale/cost price at draft creation. Empty orders, duplicate products, inactive input products, invalid quantities and cross-business relations are rejected. There is a 100-line limit per order and a one-million-unit limit per line.

Use an optional unique `Idempotency-Key` header (8–128 letters, digits, hyphens or underscores) when creating an order. Preserve it for retries of identical content. Lifecycle action bodies are empty objects, except `payment`.

Money is returned as decimal strings; quantities are whole integers. Do not recalculate historical prices from the current product catalog.

## Collections and errors

Lists return `{count, next, previous, results}` with 25 rows by default. `page_size` accepts up to 100. Search uses `search`; supported sort fields are exposed in the schema via `ordering`.

- Products: `is_active`, `category`, `supplier`, `low_stock=true`.
- Suppliers: `is_active`.
- Sales: `status`, `payment_status`.
- Purchases: `status`, `supplier`.
- Stock activity: `kind`, `product`.
- Users: `role`, `is_active`.

Invalid input/transitions return 400. Missing or expired authentication returns 401. Role restrictions and failed CSRF checks return 403. Records outside the current tenant return 404. Protected history, conflicting idempotency keys and database uniqueness races return 409. Rate limits return 429 with `Retry-After`.

Public sign-in/registration share an IP-scoped 30/hour limit; refresh/logout use 300/hour; reset requests use 5/hour. Authenticated API calls default to 1000/hour per user. Production throttling uses Redis. Configure trusted proxy behavior carefully so client IP handling remains accurate.

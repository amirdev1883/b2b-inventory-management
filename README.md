# Stockroom · B2B Inventory & Order Management

An API-first business workspace built with Django REST Framework and React. Each business has its own catalog, suppliers, team, orders and stock ledger.

## What it does

- **Business accounts:** registration, sign-in/out, rotating JWT sessions, password recovery and password changes.
- **Roles:** admins manage the business and team; managers handle inventory and fulfillment; staff prepare sales drafts.
- **Inventory:** products, suppliers, search, filtering, pagination, archived records, opening balances and stock adjustments.
- **Purchasing:** create/edit drafts, receive the full delivery exactly once, or cancel before receipt.
- **Sales:** draft → confirm/reserve → ship; cancel unshipped orders and release reservations.
- **Invoices:** downloadable PDF invoices with preserved product names, prices and seller details.
- **Alerts:** hourly low-stock checks through Celery/Redis, with at most one email per product per 24 hours until replenished.
- **Analytics:** shipped pre-tax revenue, inventory at cost, reserved units, low stock and a 30-day revenue chart.
- **Operations:** PostgreSQL, Docker Compose, Gunicorn/WhiteNoise, OpenAPI/Swagger, CI, browser tests and tagged container releases.

## Run with Docker

Requires Docker Engine with Compose v2. From the repository root:

```bash
docker compose up --build
```

Open **http://localhost:5173** and create a workspace. API documentation is at **http://localhost:8000/api/docs/**. PostgreSQL and Redis stay on the private Compose network. Development email is printed in the worker/backend logs.

Optional sample workspace, with a password you choose:

```bash
docker compose exec backend python manage.py seed_demo --email demo@example.com
```

The command prompts for a password, creates sample suppliers/products/orders, and never changes an existing account. It is disabled with production settings. It does not create a platform superuser.

To stop services while retaining your data:

```bash
docker compose down
```

The database lives in the `postgres_data` volume. Removing that volume deletes the local data.

## Run without Docker

Requires Python 3.12+ and Node 22.12+. SQLite is available for single-user development; use PostgreSQL for concurrent use and production.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python backend/manage.py migrate
python backend/manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The web interface proxies `/api/` to Django; browser requests remain on one origin. For a local PostgreSQL instance, set `DATABASE_URL` before running migrations. Environment variables are read from the process; Django does not automatically load `.env` files. Compose loads its root `.env` overrides.

To enable periodic jobs locally, start Redis and run each command from `backend/` in its own terminal:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

Set `REDIS_URL` when Redis is not at `redis://localhost:6379/0`. Only one beat scheduler should run per environment.

## First business workflow

1. Create a workspace and select its currency. That account becomes the first admin.
2. Add a supplier and products. Use **Adjust stock** for opening quantities, with a reason.
3. Create a purchase order and choose **Receive stock** after the full delivery arrives.
4. Create a sales draft. **Confirm order** reserves its units without reducing on-hand stock.
5. **Ship order** consumes those units and releases their reservation. Download the invoice from the order.
6. Add teammates, update your invoice details in Business settings, and configure SMTP for real email delivery.

## Verify the project

```bash
ruff check backend scripts
ruff format --check backend scripts
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
pytest --cov --cov-report=term-missing --cov-fail-under=85
cd frontend
npm ci
npm run lint
npm run format:check
npm test
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
```

The browser suite starts isolated Django/Vite servers and exercises registration, suppliers, products, purchase receipt, sales confirmation/shipment, PDF download, session restoration, mobile navigation and sign-out. It uses an ignored local test database by default. `E2E_PYTHON` may select your virtualenv interpreter; `E2E_DATABASE_URL` may select a dedicated PostgreSQL test database.

CI runs the backend suite against **PostgreSQL 16**, including concurrent reservations, duplicate receipts, duplicate creation requests and simultaneous admin demotions. Those concurrency tests are explicitly skipped on SQLite. CI also checks schema validation, coverage, frontend formatting/lint/build, real Chromium workflows, Redis/Celery connectivity and the production container.

## Production

The production image serves the compiled React interface, API and static assets from the same origin. Production settings require an explicit strong secret, allowed hosts and a PostgreSQL URL. HTTPS cookies, HSTS, CSRF protection and Redis-backed throttling are enabled.

Follow [the deployment guide](docs/deployment.md) for environment configuration, database migration, HTTPS proxy setup, SMTP, backups and releases. No hosted service, domain or paid resource is provisioned by this repository.

## Documentation

- [Project scope and completion map](docs/PROJECT_SCOPE.md)
- [Architecture and accounting rules](docs/architecture.md)
- [Database schema](docs/database_schema.md)
- [API guide and role matrix](docs/api.md)
- [Deployment and operations](docs/deployment.md)
- [Security boundaries](SECURITY.md)

The MVP uses one warehouse balance per product and full-order receipt/shipment. It does not include payment processing, returns/refund processing, partial fulfillment, foreign-exchange conversion, a public storefront, multilingual UI or a mobile app. Payment status is a record of money handled outside the app.

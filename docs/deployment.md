# Deployment and operations

## Single-origin container deployment

The production stage in `backend/Dockerfile` builds React, packages its assets into Django, installs the pinned runtime requirements, collects static files and runs Gunicorn as an unprivileged user. PostgreSQL and Redis are required. Use a managed PostgreSQL service or a separately managed database instance.

```bash
cp .env.production.example .env.production
# Replace every placeholder in .env.production.
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml run --rm backend python manage.py check --deploy --fail-level WARNING
docker compose -f docker-compose.prod.yml up -d
```

The web container binds to `127.0.0.1:8000`. Put an HTTPS reverse proxy or platform ingress in front of it. The interface, API and static files must share an origin. Do not expose Redis or PostgreSQL publicly. Keep a single beat replica.

If using a prebuilt release image, set `STOCKROOM_IMAGE=ghcr.io/amirdev1883/b2b-inventory-management:v1.0.0` in the Compose shell environment and pull it. Build/deploy a specific immutable version; choose the version tag you have actually published.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` in production |
| `DJANGO_SECRET_KEY` | Unique random secret of 50+ characters; generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated real hostnames, without schemes or wildcard |
| `DATABASE_URL` | PostgreSQL URL; use TLS when crossing untrusted networks |
| `REDIS_URL` | Celery broker; also the default production throttle cache |
| `CACHE_URL` | Optional separate Redis cache database/instance |
| `FRONTEND_URL` | Public HTTPS origin used in password-reset emails |
| `CSRF_TRUSTED_ORIGINS` | Public HTTPS origins, including scheme |
| `TRUST_PROXY_HEADERS` | `true` only behind a proxy that overwrites incoming `X-Forwarded-Proto` |
| `EMAIL_BACKEND` | Set to `django.core.mail.backends.smtp.EmailBackend` for real delivery |
| `EMAIL_HOST`, `EMAIL_PORT` | SMTP host/port |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials supplied through environment/secrets |
| `EMAIL_USE_TLS` | STARTTLS, default `true` |
| `DEFAULT_FROM_EMAIL` | An address verified by your email provider |
| `LOG_LEVEL` | Default `INFO` |

Compose’s `env_file` loads `.env.production`. Plain Python/Gunicorn commands expect those variables to already be exported; no implicit dotenv loader is used. Percent-encode reserved characters in database URL credentials.

Optional platform superuser, for operations only:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Business admins register through the workspace or are added by an existing business admin. They do not receive platform/Django admin access.

## Reverse proxy example

Supply real domain names and certificates in your own ingress configuration. For Nginx behind a properly configured TLS listener, the upstream location should include:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_read_timeout 65s;
    client_max_body_size 2m;
}
```

Configure HTTP-to-HTTPS redirects at the edge. The application enforces HTTPS as well; only the health endpoints are exempt so private container checks can use HTTP. HSTS is enabled in production, including subdomains; deploy it only on a domain whose subdomains support HTTPS.

## Health and scheduling

- `/health/`: lightweight process liveness.
- `/ready/`: database connectivity, HTTP 503 on failure. The container uses this for its healthcheck.
- Redis/Celery health: monitor Redis and worker `inspect ping` separately. `/ready/` does not claim email/queue availability.
- Beat schedules low-stock scans hourly and expired-token cleanup daily. Keep exactly one beat instance. Periodic low-stock messages are suppressed per product for 24 hours until replenishment.
- Development uses console email. Production requires verified SMTP to deliver alerts and recovery links. Test both with a business you control before inviting users.

## CI and releases

`ci.yml` validates PostgreSQL business/concurrency tests, migrations, OpenAPI, coverage, frontend lint/format/unit/build, full Chromium workflows, Celery/Redis connectivity and production image settings. It runs for pull requests and pushes to main/dev/feature branches.

`release.yml` runs the same checks before publishing a tagged image to GitHub Container Registry. A tag such as `v1.0.0` publishes `ghcr.io/amirdev1883/b2b-inventory-management:v1.0.0` using the repository’s GitHub token. It does not deploy to a server or create paid resources. Configure repository Actions/package permissions if your GitHub account requires them.

## Backups, upgrades and recovery

1. Take PostgreSQL backups and test restoring them to a separate database. The database contains accounts, order history, invoice snapshots and the stock ledger.
2. Preserve Redis broker data or use a durable managed Redis service. Redis is not the source of truth for business data.
3. Before upgrading, back up the database and run checks/tests on the new release.
4. Apply migrations once as a release step before starting new web/worker processes. Review backward compatibility before running multiple versions at once.
5. Roll back an image only if its schema remains compatible; otherwise restore the tested database backup deliberately.
6. Rotate exposed secrets. Rotating the Django signing secret invalidates all JWT/password-reset sessions and requires users to sign in again.

Generated invoices are reconstructed from persisted order/seller snapshots, so there is no public media bucket to back up. Keep dependency lockfiles reviewed and update them regularly. Do not publish `.env` files, database dumps or real customer screenshots.

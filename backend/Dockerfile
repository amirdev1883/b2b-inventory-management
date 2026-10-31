FROM node:22-bookworm-slim AS frontend
WORKDIR /site
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS dependencies
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM dependencies AS dev
WORKDIR /app
COPY backend/ ./
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM dependencies AS production
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --chown=app:app backend/ ./
COPY --from=frontend --chown=app:app /site/dist/index.html /app/templates/index.html
COPY --from=frontend --chown=app:app /site/dist/assets/ /app/static/assets/
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
# Static collection only needs base settings; runtime production validation remains mandatory.
RUN DJANGO_SETTINGS_MODULE=config.settings.base python manage.py collectstatic --noinput
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "container_health.py"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]

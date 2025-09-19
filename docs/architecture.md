# 🏗️ Architecture Overview

## Tech Stack
- **Backend:** Django 5 + Django REST Framework
- **Frontend:** React (Vite) + Axios
- **Database:** PostgreSQL (prod), SQLite (dev)
- **Async Tasks:** Celery + Redis (for stock alerts, background jobs)
- **Auth:** JWT (SimpleJWT)
- **Deployment:** Docker + Render/Railway

## Project Structure (Planned)
```plaintext
b2b-inventory-management/
├── backend/
│   └── config/settings/{base.py, dev.py, prod.py}
│   └── apps/{users, inventory, suppliers, orders, analytics}
├── frontend/
│   └── src/{api, components, pages}
├── docs/
└── docker-compose.yml

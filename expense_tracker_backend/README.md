# Expense Tracker Backend (Django REST + JWT)

Purpose
- API for expenses, categories, budgets, recurring rules, reports, and auth (JWT).

Run (local)
- cd expense_tracker_backend
- Ensure Postgres is running on port 5001 (see database container)
- Export env (examples):
  - POSTGRES_HOST=localhost
  - POSTGRES_PORT=5001
  - POSTGRES_DB=myapp
  - POSTGRES_USER=appuser
  - POSTGRES_PASSWORD=dbuser123
  - Alternatively, set DATABASE_URL=postgresql://appuser:dbuser123@localhost:5001/myapp
- pip install -r requirements.txt
  - Note: psycopg2-binary is already included for PostgreSQL.

Start (recommended)
- Use the startup helper which waits for DB, applies migrations, and starts the server:
  - python start_server.py

Diagnostics
- If migrations fail due to DB connection, run:
  - python manage.py db_diagnostics
  This will print resolved DATABASES['default'], relevant env vars, and attempt a direct psycopg connection using the same values to pinpoint issues (e.g., connection refused, auth failed, unknown host).

Start (manual)
- python manage.py wait_for_db --timeout 60
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py runserver 0.0.0.0:3001

Health check
- After starting, verify:
  - curl http://localhost:3001/api/health/  -> {"message":"Server is up!"}

Key endpoints
- /api/health/
- /api/auth/token/ (POST username/password)
- /api/auth/token/refresh/ (POST refresh)
- /api/categories/, /api/expenses/, /api/budgets/, /api/recurring-rules/
- /api/reports/summary, /api/reports/budget-status

CORS/CSRF/Hosts
- CORS allows http://localhost:3000 and http://127.0.0.1:3000 by default (plus the preview host on port 3000).
- CSRF_TRUSTED_ORIGINS includes http://localhost:3000 and http://127.0.0.1:3000.
- Use FRONTEND_ORIGIN env to append an additional origin if needed (e.g., a custom preview URL).
- ALLOWED_HOSTS includes localhost, 127.0.0.1, testserver, and *.kavia.ai preview domains.

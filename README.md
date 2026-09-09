# intelligent-it-support-ticket-triage
AI-based IT support ticket triage and routing system
7th Semester Project

## Local Backend Services

The backend uses PostgreSQL for application data and Redis as the Celery message broker/result backend. Copy `backend/.env.example` to a local environment file and set values appropriate for your machine. Do not commit real credentials.

Redis is expected at:

```text
REDIS_URL=redis://localhost:6379/0
```

Redis must be running separately on `localhost:6379`. Redis is not bundled with this project; install and start a local Windows-compatible Redis distribution before starting a Celery worker.

Start the FastAPI backend from `backend` in Terminal 1:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/it_support"
$env:REDIS_URL = "redis://localhost:6379/0"
\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Start the Celery worker from `backend` in Terminal 2. The `solo` pool is the practical Windows development option:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/it_support"
$env:REDIS_URL = "redis://localhost:6379/0"
\.venv\Scripts\celery.exe -A celery_app:celery_app worker --loglevel=INFO --pool=solo
```

The infrastructure smoke task can be submitted from a Python shell after the worker is running:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/it_support"
\.venv\Scripts\python.exe -c "from tasks.test_task import test_task; result = test_task.delay('hello'); print(result.get(timeout=10))"
```

The expected result is `hello`. This task verifies the backend-side Celery configuration, Redis, a worker, and result retrieval. Ticket creation now stores the ticket first and queues `it_support.process_ticket`; the worker runs the existing AI triage and team-routing services after the HTTP response is returned.

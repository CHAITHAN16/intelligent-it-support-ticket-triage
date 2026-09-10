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

# Intelligent IT Support Ticket Triage and Routing

AI-based IT support ticket triage and routing system.

**7th Semester Project**

---

## 📌 Overview

Intelligent IT Support Ticket Triage and Routing is a full-stack AI-assisted IT service management system designed to automate the initial handling of employee IT support requests.

Employees can submit IT support tickets through a web portal. The system uses machine-learning models to automatically analyze each ticket, predict its category and priority, and route it to the appropriate IT support team.

The system also provides authentication, role-based access, ticket collaboration, status history, asynchronous AI processing, and separate employee and support-agent interfaces.

### Core workflow

```text
Employee
   │
   ▼
IT Support Portal
   │
   ▼
Create Ticket
   │
   ▼
FastAPI Backend
   │
   ├──────────────► PostgreSQL
   │
   ▼
Redis Queue
   │
   ▼
Celery Worker
   │
   ▼
AI Triage
   │
   ├──► Category Prediction
   │
   └──► Priority Prediction
   │
   ▼
Team Routing
   │
   ▼
PostgreSQL
   │
   ├──────────────► Employee Portal
   │
   └──────────────► Agent Dashboard

🏗️ System Architecture
                         ┌─────────────────────┐
                         │      Employee       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Next.js Frontend   │
                         │ React + TypeScript  │
                         └──────────┬──────────┘
                                    │
                              JWT Bearer
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │       Backend       │
                         └──────┬─────────┬────┘
                                │         │
                                │         ▼
                                │   ┌─────────────┐
                                │   │    Redis    │
                                │   │ Message     │
                                │   │ Broker      │
                                │   └──────┬──────┘
                                │          │
                                │          ▼
                                │   ┌─────────────┐
                                │   │   Celery    │
                                │   │   Worker    │
                                │   └──────┬──────┘
                                │          │
                                │          ▼
                                │   ┌─────────────┐
                                │   │  AI Triage  │
                                │   └──────┬──────┘
                                │          │
                                │          ▼
                                │   ┌─────────────┐
                                │   │ Team Routing│
                                │   └──────┬──────┘
                                │          │
                                ▼          ▼
                         ┌─────────────────────┐
                         │     PostgreSQL      │
                         │      Database       │
                         └──────────┬──────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                         ▼                     ▼
                  ┌─────────────┐      ┌─────────────┐
                  │  Employee   │      │    Agent    │
                  │   Portal    │      │  Dashboard  │
                  └─────────────┘      └─────────────┘

✨ Features
👨‍💻 Employee Portal

Employees can:

Register and log in.
Submit IT support tickets.
View their own tickets.
View ticket status.
View AI classification results.
View assigned support team.
View comments.
View status history.
Track tickets while AI processing is in progress.

🧑‍💼 Support Agent Dashboard
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
Support agents can:

Log in using their agent account.
Access their assigned team queues.
View ticket statistics.
Filter tickets by:
Status
Priority
Category
Sort tickets.
Open individual tickets.
Update ticket status.
Update authoritative category and priority.
Add comments.
View AI predictions.
View ticket status history.

🤖 AI Ticket Triage

The system uses machine-learning models to analyze ticket text.

Category model

The category classifier predicts:
🤖 AI Ticket Triage

The system uses machine-learning models to analyze ticket text.

Category model

The category classifier predicts:
Network
Security
Software
Other

The model uses:

Ticket Text
    ↓
TF-IDF
    ↓
Logistic Regression
    ↓
Category
Priority model

The priority classifier predicts:

LOW
MEDIUM
HIGH

Pipeline:

Ticket Text
    ↓
TF-IDF
    ↓
Logistic Regression
    ↓
Priority

The system also records:

AI predicted category
AI predicted priority
AI confidence
AI model version
AI processing timestamp

🔀 Automatic Team Routing

After AI category prediction, the ticket is routed according to the existing routing rules.

AI Category	Support Team
Network	Network Infrastructure
Security	Security Operations
Software	Software Support
Other	General IT Support

The routing decision is persisted in the database through the ticket assignment system.

AI-generated assignments are marked with:

source = AI

⚡ Asynchronous Processing

AI triage and routing are processed asynchronously using:

Redis
Celery

Instead of making the employee wait for the complete AI pipeline:

Employee
   ↓
FastAPI
   ↓
Create Ticket
   ↓
Queue Celery Task
   ↓
Return Response

The background worker then performs:

Celery Worker
   ↓
Load Ticket
   ↓
AI Category Prediction
   ↓
AI Priority Prediction
   ↓
Team Routing
   ↓
Save Results

The frontend polls the ticket endpoint every 2.5 seconds while processing is incomplete.

Polling stops when:

AI category is available
AI priority is available
Assigned team is available
An API error occurs
The 60-second timeout is reached
The page is unmounted

This allows the system to accept tickets without blocking the HTTP request on AI processing.

🔐 Authentication & Authorization

The system implements JWT-based authentication.

Password security

Passwords are hashed using:

Argon2

Plaintext passwords are never stored.

Roles
EMPLOYEE
AGENT
ADMIN
Employee permissions

Employees can:

Create tickets
View their own tickets
View their ticket comments
View their ticket history

Employees cannot:

Access the agent dashboard
Access another employee's tickets
Modify another user's ticket
Impersonate another user
Agent permissions

Agents can:

Access authorized team queues
View authorized tickets
Update tickets they are authorized to work on
Add ticket comments
Update ticket status

The backend remains responsible for authorization. Frontend role checks are only used for navigation and user experience.

💬 Ticket Collaboration

Tickets support comments and collaboration.

Example:

Agent:
"Investigating the VPN configuration."

Agent:
"VPN credentials have been reset. Please try again."

Comments are stored in PostgreSQL and displayed chronologically.

🕒 Ticket Status History

Status changes are recorded in the ticket history.

Example:

NEW
 ↓
IN_PROGRESS
 ↓
RESOLVED

The system preserves:

Previous status
New status
Changed-by information when available
Timestamp

History is only created when the status actually changes.

🗄️ Database

The application uses PostgreSQL.

Main entities include:

users
teams
team_members
tickets
ticket_assignments
ticket_status_history
comments

The database layer uses:

SQLAlchemy
Alembic
PostgreSQL

🧰 Technology Stack
Frontend
Next.js
React
TypeScript
Tailwind CSS
Backend
Python
FastAPI
SQLAlchemy
Pydantic
Uvicorn
Machine Learning
scikit-learn
TF-IDF
Logistic Regression
joblib
Database
PostgreSQL
Alembic
Authentication
JWT
Argon2
pwdlib
Asynchronous Processing
Redis
Celery
Development
Git
GitHub
VS Code
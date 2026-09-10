# Intelligent IT Support Ticket Triage and Routing

AI-based IT support ticket triage and routing system.

**7th Semester Project**

---

## 📌 Overview

Intelligent IT Support Ticket Triage and Routing is a full-stack AI-assisted IT service management system designed to automate the initial handling of employee IT support requests.

Employees can submit IT support tickets through a web portal. The system uses machine-learning models to analyze each ticket, predict its category and priority, and automatically route it to the appropriate IT support team.

The system also provides:

- Employee and support-agent portals
- JWT-based authentication
- Role-based authorization
- AI ticket classification
- Automatic team routing
- Ticket comments
- Status history
- Asynchronous AI processing
- PostgreSQL persistence
- Redis and Celery background processing

---

## 🎯 Problem Statement

In a traditional IT helpdesk environment, incoming support requests often need to be manually reviewed, categorized, prioritized, and assigned to the appropriate support team.

This can result in:

- Delayed ticket assignment
- Incorrect categorization
- Inconsistent priority decisions
- Increased helpdesk workload
- Difficulty handling large numbers of simultaneous requests
- Limited visibility into ticket progress

This project addresses these problems by using machine learning for automated ticket triage and asynchronous processing for scalable ticket handling.

---

## 💡 Objectives

The main objectives are to:

- Automatically classify IT support tickets.
- Predict ticket priority.
- Automatically route tickets to appropriate support teams.
- Reduce manual ticket triage.
- Support multiple employees and support agents.
- Provide secure role-based access.
- Maintain ticket comments and status history.
- Process AI triage asynchronously.
- Provide separate employee and agent interfaces.
- Preserve AI predictions separately from authoritative ticket values.

---

## 🔄 Core Workflow

```text
Employee
   │
   ▼
Next.js IT Support Portal
   │
   ▼
JWT Authentication
   │
   ▼
FastAPI Backend
   │
   ├──────────────► PostgreSQL
   │
   ▼
Create Ticket
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
```

---

## 🏗️ System Architecture

```text
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
                                │   │   Message   │
                                │   │    Broker   │
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
```

---

# ✨ Features

## 👨‍💻 Employee Portal

Employees can:

- Register and log in.
- Submit IT support tickets.
- View their own tickets.
- View ticket status.
- View AI classification results.
- View assigned support team.
- View comments.
- View status history.
- Track tickets while AI processing is in progress.

---

## 🧑‍💼 Support Agent Dashboard

Support agents can:

- Log in using an agent account.
- Access authorized team queues.
- View ticket statistics.
- Filter tickets by status, priority, and category.
- Sort tickets.
- Open individual tickets.
- Update ticket status.
- Update authoritative category and priority.
- Add comments.
- View AI predictions.
- View ticket status history.

---

# 🤖 AI Ticket Triage

The system uses machine-learning models to analyze ticket text.

## Category Classification

The category classifier predicts:

```text
Network
Security
Software
Other
```

Pipeline:

```text
Ticket Text
    ↓
TF-IDF
    ↓
Logistic Regression
    ↓
Category
```

## Priority Classification

The priority classifier predicts:

```text
LOW
MEDIUM
HIGH
```

Pipeline:

```text
Ticket Text
    ↓
TF-IDF
    ↓
Logistic Regression
    ↓
Priority
```

The system records:

- AI predicted category
- AI predicted priority
- AI confidence
- AI model version
- AI processing timestamp

---

# 🔀 Automatic Team Routing

After AI category prediction, the ticket is routed according to the project's routing rules.

| AI Category | Support Team |
|---|---|
| Network | Network Infrastructure |
| Security | Security Operations |
| Software | Software Support |
| Other | General IT Support |

The routing decision is persisted through the ticket assignment system.

AI-generated assignments use:

```text
source = AI
```

---

# ⚡ Asynchronous Processing

AI triage and routing are processed asynchronously using:

- Redis
- Celery

Instead of keeping the HTTP request waiting for the complete AI pipeline:

```text
Employee
   ↓
FastAPI
   ↓
Create Ticket
   ↓
Queue Celery Task
   ↓
Return Response
```

The background worker then performs:

```text
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
```

The Celery task is:

```text
it_support.process_ticket
```

The task receives the ticket ID and creates its own database session.

Ticket processing is transactional, and duplicate processing is handled to prevent duplicate AI assignments.

---

## 🖥️ Frontend Processing

Because AI processing happens asynchronously, the frontend initially displays:

```text
Ticket submitted successfully

AI triage in progress...
```

The frontend polls the ticket endpoint every **2.5 seconds** while processing is incomplete.

Polling stops when:

- AI category is available
- AI priority is available
- Assigned team is available
- An API error occurs
- The 60-second timeout is reached
- The page is unmounted

The frontend never displays fake AI results while processing is incomplete.

---

# 🔐 Authentication & Authorization

The system implements JWT-based authentication.

## Password Security

Passwords are securely hashed using:

```text
Argon2
```

Plaintext passwords are never stored.

## Roles

```text
EMPLOYEE
AGENT
ADMIN
```

## Employee Permissions

Employees can:

- Create tickets.
- View their own tickets.
- View their ticket comments.
- View their ticket history.

Employees cannot:

- Access the agent dashboard.
- Access another employee's tickets.
- Modify unauthorized tickets.
- Impersonate another user.

## Agent Permissions

Agents can:

- Access authorized team queues.
- View authorized tickets.
- Update tickets they are authorized to work on.
- Add comments.
- Update ticket status.

The backend is authoritative for authorization. Frontend role checks are used for navigation and user experience.

---

# 💬 Ticket Collaboration

Tickets support comments between employees and support agents.

Example:

```text
Agent:
"Investigating the VPN configuration."

Agent:
"VPN credentials have been reset. Please try again."
```

Comments are stored in PostgreSQL and displayed chronologically.

---

# 🕒 Ticket Status History

Ticket status changes are recorded in the status history.

Example:

```text
NEW
 ↓
IN_PROGRESS
 ↓
RESOLVED
```

The system preserves:

- Previous status
- New status
- Changed-by information when available
- Timestamp

A history record is created only when the ticket status actually changes.

---

# 🗄️ Database

The application uses PostgreSQL.

Main entities include:

```text
users
teams
team_members
tickets
ticket_assignments
ticket_status_history
comments
```

Database technologies:

- PostgreSQL
- SQLAlchemy
- Alembic

---

# 🧰 Technology Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn

## Machine Learning

- scikit-learn
- TF-IDF
- Logistic Regression
- joblib

## Database

- PostgreSQL
- Alembic

## Authentication

- JWT
- Argon2
- pwdlib

## Asynchronous Processing

- Redis
- Celery

## Development

- Git
- GitHub
- VS Code

---

# 📊 Machine Learning Results

## Category Classification

The current category model was evaluated on a held-out test set.

```text
Accuracy:         97.27%
Macro Precision:  95.32%
Macro Recall:     97.55%
Macro F1:         96.35%
```

## Priority Classification

The current priority model was evaluated on a held-out test set.

```text
Accuracy:         73.05%
Macro Precision:  68.39%
Macro Recall:     70.42%
Macro F1:         69.31%
```

### Important Note

The datasets used for the current experiments are synthetic/curated datasets.

Therefore, these results represent held-out dataset performance and should not be interpreted as guaranteed real-world production accuracy.

---

# 📁 Project Structure

```text
intelligent-it-support-ticket-triage/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── ...
│
├── backend/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   ├── tests/
│   ├── celery_app.py
│   ├── main.py
│   └── requirements.txt
│
├── ml/
│   ├── models/
│   ├── prepare_*.py
│   └── train_*.py
│
├── datasets/
│   ├── raw/
│   └── processed/
│
├── docs/
│   └── ml/
│
├── tests/
│
├── .gitignore
├── README.md
└── ...
```

---

# 🚀 Local Setup

## Prerequisites

Install:

- Python 3.13+
- Node.js
- PostgreSQL
- Docker Desktop
- Git

Redis is used by Celery and can be run through Docker.

---

## 1. Clone the Repository

```powershell
git clone https://github.com/CHAITHAN16/intelligent-it-support-ticket-triage.git

cd intelligent-it-support-ticket-triage
```

---

## 2. Backend Setup

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Copy:

```text
backend/.env.example
```

to your local environment configuration.

Configure PostgreSQL:

```text
DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/it_support
```

Configure Redis:

```text
REDIS_URL=redis://localhost:6379/0
```

Do not commit real credentials.

---

# 🐘 PostgreSQL

Create the PostgreSQL database:

```text
it_support
```

Make sure PostgreSQL is running before starting the backend.

Apply database migrations if required:

```powershell
alembic upgrade head
```

---

# 🔴 Redis

Redis is used as the Celery message broker and result backend.

Docker Desktop must be running.

Start Redis:

```powershell
docker run -d --name it-support-redis -p 6379:6379 redis:7-alpine
```

Check the container:

```powershell
docker ps
```

Test Redis:

```powershell
docker exec it-support-redis redis-cli ping
```

Expected:

```text
PONG
```

If the container already exists:

```powershell
docker start it-support-redis
```

---

# 🚀 Start FastAPI

From the `backend` directory:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:<password>@localhost:5432/it_support"

$env:REDIS_URL = "redis://localhost:6379/0"

.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

# ⚙️ Start Celery Worker

Open another PowerShell terminal:

```powershell
cd intelligent-it-support-ticket-triage\backend

.\.venv\Scripts\Activate.ps1

$env:DATABASE_URL = "postgresql+psycopg://postgres:<password>@localhost:5432/it_support"

$env:REDIS_URL = "redis://localhost:6379/0"

.\.venv\Scripts\celery.exe -A celery_app:celery_app worker --loglevel=INFO --pool=solo
```

The `solo` pool is used for Windows development.

---

# 💻 Start Frontend

Open another terminal:

```powershell
cd intelligent-it-support-ticket-triage\frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm.cmd run dev
```

Frontend:

```text
http://localhost:3000
```

---

# 🔄 Running the Complete System

A typical local development setup uses:

```text
Terminal 1
PostgreSQL

Terminal 2
Redis / Docker

Terminal 3
FastAPI

Terminal 4
Celery Worker

Terminal 5
Next.js Frontend
```

Then open:

```text
http://localhost:3000
```

---

# 🧪 Testing

## Backend

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The backend test suite covers:

- Authentication
- Authorization
- Ticket creation
- AI triage
- Team routing
- Team queues
- Comments
- Status history
- Celery infrastructure
- Background ticket processing

## Frontend

Run lint:

```powershell
npm.cmd run lint
```

Run TypeScript checks:

```powershell
npx.cmd tsc --noEmit
```

Run production build:

```powershell
npm.cmd run build
```

---

# 🔌 API Overview

## Authentication

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

## Tickets

```text
POST  /api/tickets
GET   /api/tickets
GET   /api/tickets/{ticket_id}
PATCH /api/tickets/{ticket_id}
```

## Teams

```text
GET /api/teams
GET /api/teams/{team_id}/tickets
```

## Comments

```text
POST /api/tickets/{ticket_id}/comments
GET  /api/tickets/{ticket_id}/comments
```

## Status History

```text
GET /api/tickets/{ticket_id}/history
```

---

# 🧪 Example Ticket Processing

Employee submits:

```text
Title:
VPN is not connecting

Description:
I cannot connect to the company VPN from my laptop.
```

The system performs:

```text
Ticket Created
      ↓
Celery Task Queued
      ↓
AI Category Prediction
      ↓
Network
      ↓
AI Priority Prediction
      ↓
HIGH / MEDIUM / LOW
      ↓
Team Routing
      ↓
Network Infrastructure
      ↓
Agent Dashboard
```

The employee can monitor the ticket while the support agent handles it.

---

# 🧠 Design Principles

## Separation of Concerns

Machine learning, API logic, routing, database operations, frontend, and background processing are separated into different components.

## Human-in-the-Loop

AI predictions are stored separately from authoritative ticket values so support agents can correct AI decisions when necessary.

## Asynchronous Processing

AI processing is handled by Celery instead of blocking the HTTP request.

## Backend Authorization

The backend determines what each user is allowed to access.

## Transaction Safety

Triage, routing, and assignment operations are handled transactionally.

## Idempotent Processing

Repeated background task execution is designed to avoid duplicate AI ticket assignments.

---

# 📈 Future Improvements

Potential future improvements include:

- Improved multilingual classification
- Larger and more diverse datasets
- Better priority prediction
- Confidence-based human review
- SLA prediction
- Duplicate ticket detection
- Ticket similarity search
- Knowledge-base recommendations
- AI-generated resolution suggestions
- Advanced analytics
- Queue monitoring
- Docker Compose deployment
- Cloud deployment
- Production-grade session management
- Additional automated testing

---

# ⚠️ Current Limitations

- Current ML datasets are synthetic/curated.
- Model performance may differ on real enterprise support tickets.
- Priority classification is less accurate than category classification.
- Redis currently runs separately from the application.
- Celery uses the `solo` pool for Windows development.
- Frontend JWT storage currently uses browser `localStorage` for this academic/demo implementation.
- The ADMIN role exists, but an administrative dashboard has not yet been implemented.
- Live Redis/Celery verification depends on Redis being available locally.

---

# 👨‍🎓 Project Information

**Project:** Intelligent IT Support Ticket Triage and Routing

**Type:** 7th Semester Project

**Domain:**

- Artificial Intelligence
- Machine Learning
- Natural Language Processing
- Full-Stack Development
- IT Service Management
- Distributed Systems

---

# 📜 License

This project is developed as an academic project.
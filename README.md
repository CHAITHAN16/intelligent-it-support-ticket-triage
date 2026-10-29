# Intelligent IT Support Ticket Triage and Routing

An AI-assisted IT service management system for automated support ticket classification, prioritization, team routing, knowledge-base recommendations, and agent-driven resolution.

## 1. Project Overview

Intelligent IT Support Ticket Triage and Routing is a full-stack IT service management application designed to automate the initial processing of employee IT support requests.

Employees can submit support tickets through a web application. The system uses machine-learning models to analyze ticket content, predict the appropriate category and priority, and route the ticket to the corresponding support team.

The system also provides separate employee and support-agent workflows, ticket collaboration, status tracking, knowledge-base recommendations, and resolution management.

The project combines machine learning, natural language processing, web development, asynchronous processing, database management, and role-based authorization.

---

## 2. Problem Statement

Traditional IT helpdesk systems often require support personnel to manually review incoming requests, determine their category and priority, and assign them to the appropriate team.

This manual process can lead to:

- Delayed ticket assignment
- Inconsistent categorization
- Inconsistent priority decisions
- Increased support workload
- Difficulty processing large numbers of tickets
- Limited visibility into ticket progress
- Repeated handling of common troubleshooting issues

This project addresses these challenges by introducing automated machine-learning-based ticket triage and team routing while retaining human involvement for support and resolution.

---

## 3. Objectives

The primary objectives of the system are to:

- Automatically classify IT support tickets
- Predict ticket priority
- Automatically route tickets to appropriate support teams
- Provide employees with visibility into submitted tickets
- Provide support agents with team-based ticket queues
- Provide relevant troubleshooting recommendations
- Maintain ticket comments and collaboration history
- Maintain ticket status history
- Support controlled ticket resolution and closure
- Provide confidence-aware fallback when an automated recommendation is unreliable
- Maintain separation between AI predictions and authoritative ticket values

---

## 4. Key Features

### 4.1 Employee Portal

Employees can:

- Register and authenticate
- Create IT support tickets
- View submitted tickets
- View ticket status
- View AI predictions
- View assigned support teams
- View troubleshooting recommendations
- Add comments
- View collaboration history
- View status history

### 4.2 Support Agent Portal

Support agents can:

- Access authorized team tickets
- View team ticket queues
- Filter tickets by status, priority, and category
- View ticket details
- View AI predictions and confidence
- View knowledge-base recommendations
- Add comments
- Update ticket status
- Reassign tickets between support teams
- Add resolution notes
- Resolve tickets
- Close resolved tickets

### 4.3 AI Ticket Triage

The system automatically predicts:

- Ticket category
- Ticket priority
- Prediction confidence
- Model version

Supported categories:

```text
Network
Security
Software
Other
```

Supported priorities:

```text
LOW
MEDIUM
HIGH
```

The current implementation uses TF-IDF-based machine-learning models with Logistic Regression and stores the AI predictions separately from authoritative ticket fields.

---

## 5. Automatic Team Routing

Tickets are automatically routed based on their predicted category.

The current routing configuration includes:

| Category | Support Team |
|---|---|
| Network | Network Infrastructure |
| Security | Security Operations |
| Software | General IT Support |
| Other | General IT Support |

The system records the routing decision and assigned team.

---

## 6. Knowledge Base and Solution Recommendations

The application includes a curated knowledge base containing troubleshooting information for common IT support issues.

Current knowledge-base topics include:

- Wi-Fi connectivity
- VPN connectivity
- Email synchronization
- Software crashes
- Password and account issues
- Suspicious login activity
- Printer problems
- Laptop hardware issues

When a ticket is processed, the system searches the knowledge base for a relevant article using the ticket's content and predicted category.

Recommendations are retrieved from the curated local knowledge base. Eligible software issues can also use an optional GroqCloud-backed conversation grounded in the matched article; the existing article remains the source of approved troubleshooting guidance.

### Guided AI Resolution and Provider Privacy

AI-guided resolution is available only for software tickets with a classification score at or above `AI_RESOLUTION_CONFIDENCE_THRESHOLD` (default `0.75`) and a separate sufficient knowledge-base match. The ML classification score is a model score, not a calibrated probability. Security-sensitive, hardware-repair, low-confidence, and no-guidance cases stay with the routed human support team. Provider failures also fall back to that team.

The provider integration is server-side. The frontend never receives `GROQ_API_KEY`. For Docker Compose, set `GROQ_API_KEY` and optionally `GROQ_MODEL` in the ignored root `.env` file. `GROQ_DATA_PROCESSING_APPROVED` defaults to `false`; set it to `true` only after confirming GroqCloud is approved for the ticket data processed in your organization. When approval is absent, AI resolution is unavailable and tickets remain with their assigned team. Common email, IP address, password, token, API key, and secret values are redacted before provider submission; this does not replace organization data-classification or provider-approval controls. Use sanitized test data unless the provider is approved for real company data.

An AI response never resolves a ticket by itself. The employee must explicitly confirm that the issue is fixed; otherwise, they can request human support and the ticket remains unresolved.

For local backend development, configure the same variables in `backend/.env` and explicitly set `GROQ_DATA_PROCESSING_APPROVED=true` only when approved. Never put a real provider key in either example file or commit `.env` files.

### Confidence-Based Recommendations

The system uses confidence thresholds to prevent unreliable recommendations from being presented as definitive solutions.

| Confidence | Result |
|---|---|
| 70% or higher | Strong knowledge-base match |
| 40%–69% | Possible troubleshooting starting point |
| Below 40% | No-match fallback |

When confidence is below the minimum threshold, the system does not present the retrieved troubleshooting solution and instead directs the employee to work with the assigned IT team.

---

## 7. Ticket Lifecycle

The supported ticket lifecycle is:

```text
NEW
 |
 +--> ASSIGNED
 |
 +--> IN_PROGRESS
 |
 +--> WAITING_FOR_USER
 |
 +--> RESOLVED
          |
          +--> CLOSED
```

Supported transitions are controlled by the backend.

Resolving a ticket requires a resolution note. The system records the resolution timestamp and adds the resolution information to the ticket history.

Closing a ticket is only permitted after the ticket has been resolved.

---

## 8. Ticket Collaboration

Tickets support comments between employees and support agents.

Comments are stored in PostgreSQL and displayed chronologically within the ticket.

Example workflow:

```text
Employee:
The VPN connection fails when I connect from home.

Agent:
Investigating the VPN configuration.

Agent:
Please try connecting again after restarting the VPN client.
```

The collaboration history remains associated with the ticket.

---

## 9. Status History

Ticket status changes are recorded in the database.

Each status-history record can contain:

- Previous status
- New status
- User responsible for the change
- Timestamp
- Optional note

Example:

```text
NEW
 |
 v
IN_PROGRESS
 |
 v
WAITING_FOR_USER
 |
 v
IN_PROGRESS
 |
 v
RESOLVED
 |
 v
CLOSED
```

The system preserves the ticket lifecycle for auditing and tracking purposes.

---

## 10. Authentication and Authorization

The application uses JWT-based authentication and role-based authorization.

Supported application roles include:

```text
EMPLOYEE
SUPPORT_AGENT
ADMIN
```

Employees and support agents have different application workflows.

Backend authorization is enforced independently of frontend navigation. The frontend role checks are primarily used to provide the appropriate user interface and navigation.

Passwords are securely hashed using the project's existing password-hashing implementation.

---

## 11. System Architecture

```text
                         Employee
                            |
                            v
                    Next.js Frontend
                            |
                            v
                     FastAPI Backend
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
   Authentication      Ticket Service    Authorization
          |                 |
          |                 +----------------------+
          |                                        |
          v                                        v
       JWT Auth                              Ticket Processing
                                                   |
                         +-------------------------+-------------------------+
                         |                         |                         |
                         v                         v                         v
                    ML Triage                Team Routing            Knowledge Base
                         |                         |                         |
                         +-------------------------+-------------------------+
                                                   |
                                                   v
                                              PostgreSQL
                                                   |
                                                   ^
                                                   |
                                              Redis / Celery
                                                   |
                                                   v
                                          Background Processing
```

---

## 12. Technology Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Uvicorn

### Machine Learning

- scikit-learn
- TF-IDF
- Logistic Regression
- joblib

### Database

- PostgreSQL
- SQLAlchemy
- Alembic

### Authentication

- JWT
- Argon2
- pwdlib

### Background Processing

- Redis
- Celery

### Development

- Docker
- Docker Compose
- Git
- GitHub
- VS Code

The project's documented technology stack includes these components. Pasted markdown(20260910-102706)

---

## 13. Project Structure

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
│   ├── scripts/
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
├── docker-compose.yml
├── .env.example
└── README.md
```

The project's documented structure separates the frontend, backend, machine-learning components, datasets, documentation, and tests. Pasted markdown(20260910-102706)

---

## 14. Local Development

### Prerequisites

The development environment requires:

- Python 3.13+
- Node.js
- Docker Desktop
- Git
- PostgreSQL
- Redis through Docker or another local Redis installation

The original project documentation identifies these as the required development tools. Pasted markdown(20260910-102706)

### Clone the Repository

```powershell
git clone https://github.com/CHAITHAN16/intelligent-it-support-ticket-triage.git

cd intelligent-it-support-ticket-triage
```

### Backend Virtual Environment

```powershell
cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

---

## 15. Environment Configuration

Create the required local environment configuration before starting the application.

Example:

```text
DATABASE_URL=postgresql+psycopg://postgres:<password>@postgres:5432/it_support
REDIS_URL=redis://redis:6379/0
APP_ENV=development
JWT_SECRET_KEY=<generate-a-random-secret-of-at-least-32-bytes>
```

Set `JWT_SECRET_KEY` to a private random value before starting the backend. For example, generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, then store it only in your ignored `.env` file or secret manager. Do not commit the generated value. The backend defaults `APP_ENV` to `production` and refuses to start if the secret is missing, shorter than 32 bytes, or an obvious placeholder. Docker Compose explicitly defaults `APP_ENV` to `development` for this local stack; set it to `production` for a production deployment. There is no generated or shared fallback key.

Do not commit real credentials, passwords, API keys, or JWT secrets to source control.

---

## 16. Running the Application with Docker

Build and start the complete development environment:

```powershell
docker compose up --build
```

The primary services are:

| Service | Address |
|---|---|
| Frontend | `http://localhost:3000` |
| Backend | `http://localhost:8000` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

The backend health endpoint is:

```text
http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "IT Support Backend"
}
```

---

## 17. Local Support-Agent Provisioning

A local-development-only utility is provided for creating support-agent accounts:

```text
backend/scripts/create_support_agent.py
```

The utility:

- Accepts an email address
- Accepts an agent name
- Prompts for a password without displaying it
- Uses the project's existing password hashing utility
- Creates the account with the `SUPPORT_AGENT` role
- Optionally adds the agent to an existing team
- Rejects duplicate email addresses
- Does not modify existing employee accounts
- Does not expose password values through command-line arguments

Example:

```powershell
docker compose run --rm --no-deps backend python scripts/create_support_agent.py --email agent.local@example.com --name "Local Support Agent" --team "General IT Support"
```

The password is entered interactively.

This utility is intended for local development and testing rather than public user registration.

---

## 18. Machine Learning Models

The current application requires two pre-trained model artifacts, tracked in Git so a fresh clone has the exact files used by the runtime:

| Runtime artifact | Size | SHA-256 |
|---|---:|---|
| `ml/models/category_model_v1.joblib` | 757,852 bytes | `d4667ca05ac134081b3e947207410a37fd7d96d03050e14c5345bea8d720e2dc` |
| `ml/models/priority_model_v2.joblib` | 1,347,796 bytes | `27a83c7c09010b9b37b0b26ca59c3170117a25af00144d27218ec5173915f47b` |

The backend and Celery worker load these files directly from `ml/models/`. Docker Compose mounts this directory read-only into both services. No model download or training step is required at startup.

The current backend uses:

```text
Category Model:
category_model_v1.joblib

Priority Model:
priority_model_v2.joblib
```

The reported model version is:

```text
category-v1+priority-v2
```

The other model files in `ml/models/` are not loaded by the current triage service: `priority_model.joblib` is an earlier priority model, and `subcategory_model.joblib` is a training output that runtime subcategory prediction does not use. The JSON metadata and confusion-matrix images document evaluation results; they are not needed to serve predictions.

Training scripts are provided for development, but retraining is separate from application setup and may overwrite model outputs. A fresh clone does not contain the raw source datasets because `datasets/raw/` is gitignored, so the presence of those scripts does not make model training reproducible from a fresh clone. The tracked runtime artifacts are the reproducible deployment inputs.

---

## 19. Machine Learning Evaluation

The documented held-out evaluation results are:

### Category Classification

| Metric | Result |
|---|---:|
| Accuracy | 97.27% |
| Macro Precision | 95.32% |
| Macro Recall | 97.55% |
| Macro F1 | 96.35% |

### Priority Classification

| Metric | Result |
|---|---:|
| Accuracy | 73.05% |
| Macro Precision | 68.39% |
| Macro Recall | 70.42% |
| Macro F1 | 69.31% |

These results are based on synthetic/curated datasets and should therefore be interpreted as held-out dataset performance rather than guaranteed real-world production performance. Pasted markdown(20260910-102706)

---

## 20. Testing

The backend contains automated tests covering major application functionality, including:

- Authentication
- Authorization
- Ticket creation
- Ticket validation
- ML triage
- Team routing
- Ticket persistence
- Knowledge-base retrieval
- Confidence-aware recommendations
- Agent ticket queues
- Ticket collaboration
- Status history
- Resolution workflow
- Celery task processing

Run the backend test suite with:

```powershell
python -m pytest
```

For the Docker development environment:

```powershell
docker compose run --rm --no-deps backend sh -c "python -m pip install pytest httpx2 >/dev/null 2>&1 && python -m pytest -q"
```

---

## 21. Design Principles

### Separation of Concerns

Machine learning, API logic, routing, database operations, frontend functionality, and background processing are separated into independent components.

### Human-in-the-Loop

AI predictions are stored separately from authoritative ticket values, allowing support agents to review and correct AI decisions.

### Asynchronous Processing

AI ticket processing is handled through Celery background tasks rather than blocking the ticket creation request.

### Backend Authorization

Authorization is enforced by the backend. Frontend role checks are not treated as a security boundary.

### Transaction Safety

Triage, routing, and assignment operations are performed using transactional database operations.

### Idempotent Processing

Background processing is designed to avoid duplicate processing when tasks are retried or executed more than once.

These principles are part of the project's documented design approach. Pasted text(20261008-144038)

---

## 22. Current Project Status

The current prototype implements the core IT support workflow:

```text
Employee
   |
   v
Create Ticket
   |
   v
AI Classification
   |
   v
Priority Prediction
   |
   v
Team Routing
   |
   v
Knowledge Base Recommendation
   |
   v
Support Agent Queue
   |
   v
Investigation and Collaboration
   |
   v
Resolution Note
   |
   v
RESOLVED
   |
   v
CLOSED
```

The project currently provides both employee and support-agent workflows, automated ticket triage, team routing, knowledge-base recommendations, confidence-aware fallback, collaboration, status management, and resolution handling.

---

## 23. Limitations

The current implementation has several limitations:

- Machine-learning datasets are synthetic/curated.
- Real-world enterprise ticket performance may differ from the reported evaluation results.
- Priority classification is less accurate than category classification.
- Celery uses the `solo` pool for Windows development.
- JWT storage currently uses browser `localStorage` for this academic/demo implementation.
- An administrative dashboard has not yet been implemented.
- The system is intended as an academic prototype and is not production-ready.

These limitations are consistent with the project's existing documentation. Pasted text(20261008-144038)

---

## 24. Future Improvements

Potential future improvements include:

- Larger and more diverse training datasets
- Improved multilingual classification
- Improved priority prediction
- Confidence-based human review workflows
- SLA prediction
- Duplicate ticket detection
- Ticket similarity search
- Advanced knowledge-base retrieval
- LLM-based resolution assistance
- Advanced support analytics
- Queue monitoring
- Production-grade session management
- Cloud deployment
- Expanded automated testing
- Administrative dashboard

The project documentation identifies these areas as potential future improvements. Pasted text(20261008-144038)

---

## 25. Security Considerations

This project is intended for academic and development purposes.

For production deployment, additional security measures would be required, including:

- Secure HTTP-only cookie-based session management
- HTTPS
- Secret management
- CSRF protection where applicable
- Rate limiting
- Production database configuration
- Audit logging
- Stronger account provisioning controls
- Secure deployment configuration
- Comprehensive security testing

Real credentials and secrets must never be committed to the repository.

---

## 26. Project Information

**Project:** Intelligent IT Support Ticket Triage and Routing

**Type:** 7th Semester Academic Project

**Domains:**

- Artificial Intelligence
- Machine Learning
- Natural Language Processing
- Full-Stack Development
- IT Service Management
- Distributed Systems

---

## 27. License

This project is developed as an academic project.

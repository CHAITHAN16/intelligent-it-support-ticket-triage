# Intelligent IT Support Ticket Triage and Routing

An AI-powered IT support system that helps organizations classify support tickets, predict their priority, and route requests to the appropriate support teams.

## Overview

IT support teams often receive large volumes of requests involving software errors, hardware failures, network connectivity, account access, and other technical issues. Manually categorizing and prioritizing these requests can delay resolution.

**Intelligent IT Support Ticket Triage and Routing** aims to streamline this process using machine learning, backend automation, and a web-based support portal.

Users can submit support requests through the frontend, while the backend processes ticket information to support categorization, priority prediction, and team routing.

## Key Features

- **Ticket Management:** Submit and manage IT support requests.
- **AI/ML Classification:** Categorize tickets using natural language processing and machine learning.
- **Priority Prediction:** Predict ticket priority based on ticket information.
- **Team Routing:** Support routing tickets to the appropriate support team.
- **User Authentication:** Backend authentication using JWT and password hashing.
- **REST API:** FastAPI endpoints for application functionality.
- **Background Processing:** Celery and Redis for asynchronous task processing.
- **Database Persistence:** PostgreSQL for storing application data.
- **Modern Web Interface:** Next.js, React, TypeScript, and Tailwind CSS.

*Note: Feature availability depends on the current implementation. See the project code and API documentation for the implemented endpoints and workflows.*

## Tech Stack

| Component | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Machine Learning | Scikit-learn, TF-IDF, Logistic Regression |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| Background Tasks | Celery |
| Message Broker / Cache | Redis |
| Authentication | JWT, Argon2 |
| Containerization | Docker, Docker Compose |

## Architecture

```text
             Employee / Support User
                       |
                       v
             Next.js Web Frontend
                  Port 3000
                       |
                       v
               FastAPI Backend
                  Port 8000
                       |
          +------------+------------+
          |            |            |
          v            v            v
     PostgreSQL      ML Models     Redis
      Database    Classification     |
                                    v
                              Celery Worker
                           Background Tasks
```

The backend provides the API layer, PostgreSQL stores application data, machine-learning models support ticket classification and priority prediction, and Celery workers handle asynchronous tasks through Redis.

## Machine Learning

The project uses a traditional machine-learning pipeline for text-based ticket classification.

### Classification pipeline

1. Receive the ticket description.
2. Convert text into numerical features using TF-IDF.
3. Apply a trained classification model.
4. Produce a predicted category or priority, depending on the model.
5. Use the resulting information to support the triage workflow.

### Current reported model metrics

| Model | Accuracy | Macro F1-score |
|---|---:|---:|
| Ticket category classification | 97.27% | 96.35% |
| Ticket priority prediction | 73.05% | 69.31% |

These are previously reported evaluation results on the project's dataset, not a guarantee of real-world performance. Evaluation on representative, real-world tickets is needed to assess generalization.

## Project Structure

```text
intelligent-it-support-ticket-triage/
├── backend/       # FastAPI application, models, migrations and tests
├── frontend/      # Next.js web application
├── ml/            # Machine-learning training and inference code
├── datasets/      # Datasets used for development and evaluation
├── docs/          # Project documentation
├── tests/         # Automated tests
├── docker-compose.yml
├── .env.example
├── auto-git.ps1
└── README.md
```

## Getting Started

### Prerequisites

Install the following:

- Git
- Docker Desktop with Docker Compose
- Python 3.12 or a compatible version for local development
- Node.js and npm if running the frontend locally outside Docker

### 1. Clone the repository

```bash
git clone https://github.com/CHAITHAN16/intelligent-it-support-ticket-triage.git
cd intelligent-it-support-ticket-triage
```

### 2. Configure environment variables

Create a root `.env` file based on `.env.example`.

```powershell
Copy-Item .env.example .env
```

Configure the required variables using the project's environment template. These include the PostgreSQL credentials and database name, `JWT_SECRET_KEY`, and any Redis or database connection settings required by your Compose configuration.

Use strong, private secrets. Do not commit `.env` or expose credentials in logs, screenshots, or GitHub.

### 3. Start the application

Ensure Docker Desktop is running, then execute:

```bash
docker compose up -d --build
```

Check container status:

```bash
docker compose ps
```

View backend logs:

```bash
docker compose logs --tail=100 backend
```

View frontend logs:

```bash
docker compose logs --tail=100 frontend
```

View Celery logs:

```bash
docker compose logs --tail=100 celery
```

The Compose configuration runs the database migrations during backend startup.

### 4. Access the application

| Service | URL |
|---|---|
| Web application | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API health check | http://localhost:8000/api/health |
| Interactive API documentation | http://localhost:8000/docs |

The health endpoint should return a successful response when the backend is running.

### Local development: provision a support agent

The public registration endpoint creates employee accounts only. For local Agent Dashboard testing, an administrator can provision a support-agent account with this development-only utility from the project root, with `DATABASE_URL` configured for the local database:

```bash
python backend/scripts/create_support_agent.py --email agent@example.test --name "Local Agent"
```

The utility prompts for the password without displaying it. To add the account to an existing team, supply its exact name:

```bash
python backend/scripts/create_support_agent.py --email agent@example.test --name "Local Agent" --team "Network Infrastructure"
```

This is a local development/admin utility, not a production provisioning mechanism. It rejects an email that already exists and does not change that account. Team membership is optional for signing in, but is needed for access to that team's queue. Never put passwords on the command line or in source control.

### 5. Stop the application

```bash
docker compose down
```

This stops and removes the Compose containers and network while preserving named volumes by default. Do not use `docker compose down -v` unless you intentionally want to remove the associated persistent volumes.

## Testing

Run the relevant automated tests from the project root.

For the backend database URL test, for example:

```bash
python -m pytest backend/tests/test_database_url.py -q
```

To run the full backend test suite, inspect the test configuration and dependencies, then execute:

```bash
python -m pytest backend/tests -q
```

The full test suite may require additional environment configuration and running services.

## Security Considerations

- Store credentials and secret keys in environment variables.
- Hash passwords rather than storing plaintext passwords.
- Validate incoming ticket data.
- Restrict access to authenticated and authorized users.
- Apply rate limiting and suitable request-size limits before public deployment.
- Run database migrations deliberately and preserve database backups.
- Run production services with non-root users and appropriately restricted permissions.

## Current Scope and Limitations

This project is a development-stage prototype. Model performance depends on the quality and representativeness of its training data.

Before production deployment, additional validation may be needed for:

- Model performance on real support tickets.
- Authorization and team-level access controls.
- Reliable background-task retries and failure handling.
- API rate limiting, monitoring, and logging.
- End-to-end testing of ticket creation, classification, and routing.
- Production deployment, security hardening, and operational recovery.

## Future Improvements

- Improve model performance using larger and more representative datasets.
- Add semantic search over historical support tickets.
- Provide explainable predictions and confidence scores.
- Build dashboards for ticket trends and resolution analytics.
- Add robust retry policies and task-failure monitoring.
- Improve automated testing and deployment workflows.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes and add relevant tests.
4. Submit a pull request describing the changes.

## License

No license has been specified yet. Add a `LICENSE` file before distributing the project under an open-source license.

---

**Built as an AI/ML and full-stack software engineering project focused on intelligent IT support automation.**
📌 Overview
Intelligent IT Support Ticket Triage and Routing is a full-stack AI-assisted IT service management system designed to automate the initial handling of employee IT support requests.

Employees can submit IT support tickets through a web portal. The system uses machine-learning models to analyze each ticket, predict its category and priority, and automatically route it to the appropriate IT support team.
The system provides
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
- Knowledge-base-based solution recommendations
- Confidence-aware solution fallback
- Agent ticket queue and resolution workflow
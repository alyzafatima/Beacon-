# Beacon — Website & Heartbeat Monitoring SaaS

Beacon is a Django-based monitoring platform designed to monitor websites and heartbeat-based services. It periodically checks configured monitors, records check results, detects failures, creates incidents, and provides an API and dashboard-oriented backend for managing monitoring services.

The project is inspired by monitoring platforms such as UptimeRobot and Healthchecks.io and was developed as a backend-focused internship project.

---

## Features

### Monitor Management

Beacon supports creating and managing monitoring configurations for authenticated users.

Each monitor can contain information such as:

* Monitor name
* Monitor type
* URL
* Expected HTTP status code
* Check interval
* Grace period
* Active/inactive status
* Owner
* Creation timestamp

Two monitoring types are supported:

* HTTP monitoring
* Heartbeat monitoring

---

## HTTP Monitoring

HTTP monitors periodically send requests to the configured URL.

Beacon records information such as:

* HTTP status code
* Response time
* Check timestamp
* Success/failure status

A check is considered successful when the received HTTP status code matches the monitor's configured expected status code.

For example:

```text
Expected status: 200

Website response: 200
        ↓
Successful check
```

If the website returns an unexpected status or the request fails, the check is recorded as unsuccessful.

---

## Heartbeat Monitoring

Heartbeat monitors are designed for scheduled jobs, scripts, background processes, or other services that need to report that they are still running.

Each heartbeat monitor can have a unique heartbeat token.

A monitored service can send a request to its heartbeat endpoint:

```text
GET /ping/<heartbeat-token>/
```

When Beacon receives a valid heartbeat:

1. The heartbeat monitor is identified.
2. A successful `Check` is created.
3. An open heartbeat incident can be resolved.
4. A success response is returned.

Example response:

```json
{
    "status": "ok"
}
```

If a heartbeat does not arrive within the configured interval and grace period, Beacon can identify the monitor as overdue and create a heartbeat incident.

---

## Incident Detection

Beacon keeps track of monitoring failures through incidents.

An incident represents a period during which a monitor is considered to be failing or unavailable.

For HTTP monitoring, repeated failed checks can result in an incident being created.

For heartbeat monitoring, an incident can be created when the expected heartbeat is not received within the allowed time.

When a heartbeat is received again while an incident is open, Beacon can resolve the incident and record its resolution time.

---

## Check History

Every monitoring attempt creates a `Check` record.

A check can contain information such as:

* Monitor
* Timestamp
* Success/failure status
* HTTP status code
* Response time

This allows monitoring history to be stored and reviewed instead of only keeping the current monitor state.

---

## Authentication and User-Owned Monitors

Beacon uses Django authentication and Django REST Framework authentication/permissions.

Authenticated users can manage their own monitors.

The API filters monitors according to the currently authenticated user, so a user does not simply receive every monitor belonging to other users.

Monitor creation automatically associates the new monitor with the authenticated user.

Conceptually:

```text
Logged-in User
      ↓
API request
      ↓
MonitorViewSet
      ↓
get_queryset()
      ↓
Monitor.objects.filter(owner=request.user)
      ↓
Only that user's monitors
```

---

## REST API

Beacon provides API endpoints using Django REST Framework.

The monitor API is available under:

```text
/api/monitors/
```

The monitor API supports operations for managing monitors through the REST framework.

Authentication is required for protected monitor operations.

The API uses:

* Serializers
* ViewSets
* Permissions
* Routers

---

## Heartbeat API

Heartbeat monitors provide a public endpoint because the external service sending the heartbeat does not need to log into the Beacon dashboard.

The endpoint follows this pattern:

```text
/ping/<token>/
```

Example:

```text
https://your-beacon-domain.com/ping/your-heartbeat-token/
```

The heartbeat token identifies the corresponding monitor.

---

## Background Tasks

Beacon uses Celery for background monitoring tasks.

Celery allows monitoring operations to run independently from normal web requests.

The project includes tasks for:

* Dispatching HTTP checks
* Performing HTTP monitor checks
* Sweeping heartbeat monitors

The general architecture is:

```text
Django
   │
   ├── API
   ├── Dashboard
   └── Monitor configuration
          │
          ↓
       Celery
          │
          ↓
      Background Tasks
          │
          ├── HTTP checks
          └── Heartbeat checks
```

---

## Celery Beat

Celery Beat is used for scheduling periodic background tasks.

For example, an HTTP monitoring dispatch task can run periodically and identify active HTTP monitors that need to be checked.

The project uses `django-celery-beat` for managing periodic task schedules.

---

## Redis

Redis is used as the message broker for Celery.

The architecture is:

```text
Django
   ↓
Celery task
   ↓
Redis
   ↓
Celery Worker
   ↓
Monitoring operation
```

Redis allows background tasks to be queued and processed by Celery workers.

---

## Database

The project uses a relational database.

During local development, SQLite can be used.

For deployment, the application is configured to use a PostgreSQL database through the `DATABASE_URL` environment variable.

Database configuration is handled using:

```text
dj-database-url
```

---

## Main Models

### Monitor

Represents a website or heartbeat service being monitored.

Important fields include:

* `owner`
* `name`
* `monitor_type`
* `url`
* `expected_status`
* `interval_seconds`
* `grace_period_seconds`
* `heartbeat_token`
* `is_active`
* `created_at`

---

### Check

Stores the result of a monitoring attempt.

Important information includes:

* Monitor
* Timestamp
* Success status
* HTTP status code
* Response time

---

### Incident

Represents a detected monitoring problem.

An incident can store information such as:

* Monitor
* Cause
* Creation time
* Resolution time

An open incident can later be resolved when the monitored service becomes healthy again.

---

## Technology Stack

### Backend

* Python
* Django
* Django REST Framework

### Background Processing

* Celery
* Celery Beat
* django-celery-beat

### Message Broker

* Redis

### Database

* SQLite for local development
* PostgreSQL for deployment

### HTTP Monitoring

* Requests

### Production Server

* Gunicorn

### Static Files

* WhiteNoise

### Configuration

* python-decouple
* dj-database-url

### Version Control

* Git
* GitHub

### Deployment

* Render

---

## Project Architecture

The overall architecture can be represented as:

```text
                    ┌─────────────────────┐
                    │       User          │
                    └──────────┬──────────┘
                               │
                               ↓
                    ┌─────────────────────┐
                    │ Django + DRF        │
                    │ API / Application   │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ↓                           ↓
        ┌─────────────────┐         ┌─────────────────┐
        │   PostgreSQL    │         │      Redis      │
        │    Database     │         │  Celery Broker  │
        └─────────────────┘         └────────┬────────┘
                                             │
                                             ↓
                                   ┌─────────────────────┐
                                   │   Celery Worker     │
                                   └──────────┬──────────┘
                                              │
                                              ↓
                                   ┌─────────────────────┐
                                   │ Monitoring Tasks    │
                                   │                     │
                                   │ HTTP Checks         │
                                   │ Heartbeat Sweeps   │
                                   └──────────┬──────────┘
                                              │
                                              ↓
                                      External Services
```

---

# Local Development Setup

## 1. Clone the Repository

Clone the repository from GitHub:

```bash
git clone https://github.com/alyzafatima/Beacon-.git
```

Move into the project:

```bash
cd Beacon-
```

---

## 2. Create a Virtual Environment

On Windows:

```powershell
python -m venv venv
```

Activate it:

```powershell
venv\Scripts\activate
```

You should then see:

```text
(venv)
```

in your terminal.

---

## 3. Install Dependencies

Install the required packages:

```powershell
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=your-database-url
REDIS_URL=redis://localhost:6379/0
```

Do not commit the `.env` file to GitHub.

The actual production values should be configured through the deployment platform's environment variables.

---

## 5. Run Migrations

Run:

```powershell
python manage.py migrate
```

---

## 6. Create a Superuser

Create an admin account:

```powershell
python manage.py createsuperuser
```

Follow the prompts to enter:

* Username
* Email
* Password

---

## 7. Start Django

Run:

```powershell
python manage.py runserver
```

The development server will normally be available at:

```text
http://127.0.0.1:8000/
```

---

# Running Celery Locally

Redis should be running before starting Celery.

Start the Celery worker:

```powershell
celery -A beacon worker -l info --pool=solo
```

On Windows, the `--pool=solo` option is useful for local development.

Start Celery Beat in another terminal:

```powershell
celery -A beacon beat -l info
```

The worker processes background tasks while Beat schedules periodic tasks.

---

# Admin Panel

Django's admin panel is available at:

```text
/admin/
```

For local development:

```text
http://127.0.0.1:8000/admin/
```

The admin panel can be used to manage application data such as:

* Users
* Monitors
* Checks
* Incidents
* Periodic tasks

---

# Important Environment Variables

The application uses environment variables instead of hardcoding sensitive configuration.

Common variables include:

```env
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=your-postgresql-url
REDIS_URL=your-redis-url
```

Additional variables can be added when integrating external alerting providers such as email, Slack, or Discord.

Never commit real secrets, passwords, tokens, or API keys to the repository.

---

# Deployment

The project can be deployed using a platform such as Render.

The basic deployment architecture is:

```text
GitHub Repository
       ↓
Render Web Service
       ↓
Django + Gunicorn
       ↓
PostgreSQL
```

For background processing, Celery workers and a Redis broker need to be configured separately in the production environment.

Production environment variables should be configured through the hosting provider rather than committed to GitHub.

---

# Security Notes

The following files and values should not be committed to the repository:

```text
.env
database passwords
API keys
secret keys
private credentials
production tokens
```

The `.gitignore` file should exclude sensitive and local-development files such as:

```text
.env
venv/
__pycache__/
*.pyc
db.sqlite3
```

---

# Future Improvements

Possible future improvements include:

* Email alert integration
* Slack notifications
* Discord notifications
* Alert escalation
* Monitoring graphs
* Public status pages
* Advanced incident history
* Retry mechanisms
* Idempotent task processing
* Stripe-based paid plans
* Improved dashboard analytics
* Production Celery worker and Beat configuration
* Containerized deployment
* Automated testing and CI/CD

---

# Project Status

Beacon is an internship backend project focused on learning and implementing real-world monitoring system architecture using Django, Django REST Framework, Celery, Redis, and PostgreSQL.

The project demonstrates concepts including:

* Django models
* Django authentication
* REST APIs
* User-specific data access
* Background task processing
* Periodic task scheduling
* HTTP monitoring
* Heartbeat monitoring
* Incident detection
* PostgreSQL deployment
* Git/GitHub workflow
* Cloud deployment

---

# Author

**Aliza Fatima**

Bachelor of Science in Software Engineering

GitHub: `alyzafatima`

---

# License

This project is currently intended as an educational and internship project.

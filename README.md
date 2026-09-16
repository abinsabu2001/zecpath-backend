# ZecPath - AI-Powered Recruitment Platform

## Live Project

🌐 **Live API:** https://zecpath-backend-7zoy.onrender.com

📚 **Swagger API Documentation:** https://zecpath-backend-7zoy.onrender.com/api/docs/

---

## Project Overview

ZecPath is an API-driven recruitment platform developed using Python and Django. It provides recruitment functionality for Candidates, Employers, and Administrators.

The backend provides RESTful APIs for authentication, user management, job management, applications, candidate management, recruitment analytics, AI-assisted interviews, subscriptions, payments, and administrative operations.

---

## Key Features

- User registration and authentication
- JWT-based authentication
- Role-based access control
- Candidate profile management
- Employer profile management
- Job creation and management
- Job search and filtering
- Job application management
- Applicant management
- Recruitment analytics
- AI-assisted interview workflow
- AI question generation and answer evaluation
- Resume parsing
- Candidate matching and ranking
- Automatic candidate shortlisting
- Interview scheduling and rescheduling
- Email notifications and reminders
- Subscription management
- Razorpay payment integration
- Payment verification
- Payment history
- Refund management
- Financial audit logging
- Redis caching
- Celery background tasks
- AWS S3 file storage
- Swagger/OpenAPI documentation
- API pagination, filtering, searching, and ordering
- Automated API and security testing

---

## Technology Stack

### Backend
- Python
- Django
- Django REST Framework

### Authentication & Security
- JWT Authentication
- Role-Based Access Control
- Django Authentication
- API throttling

### Database
- SQLite for development
- PostgreSQL-ready architecture

### Caching & Background Processing
- Redis
- Celery

### Cloud & Storage
- AWS S3

### Payment Integration
- Razorpay

### API Documentation
- Swagger
- OpenAPI
- drf-spectacular

### Development & Testing
- Git
- GitHub
- Postman
- Automated API Testing

---

## API Overview

ZecPath provides **61 REST API endpoints** covering major recruitment platform operations.

The APIs include:

- Authentication
- User profiles
- Candidate management
- Employer management
- Job management
- Applications
- Applicant filtering
- Recruitment analytics
- AI interview workflows
- Resume parsing
- Candidate matching
- Interview scheduling
- Notifications
- Subscriptions
- Payments
- Refunds
- Administrative operations

### API Documentation

The complete interactive API documentation is available through Swagger:

**Swagger:** https://zecpath-backend-7zoy.onrender.com/api/docs/

---

## Project Structure

```text
zecpath-backend/
│
├── accounts/
│   ├── migrations/
│   ├── admin.py
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── services.py
│   ├── tasks.py
│   ├── tests.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
│
├── coreapp/
│
├── zecpath_backend/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── API_GUIDE.md
├── bug_resolution_report.txt
├── evaluation_feedback.txt
├── phase_completion_report.txt
├── manage.py
├── requirements.txt
└── README.md

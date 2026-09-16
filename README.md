# ZecPath – AI-Powered Recruitment Platform

## Project Overview

ZecPath is an API-driven recruitment platform developed using Python and Django. It provides recruitment functionality for Candidates, Employers, and Administrators.

The backend provides RESTful APIs for authentication, user management, job management, applications, candidate management, recruitment analytics, AI-assisted interviews, subscriptions, payments, and administrative operations.

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
- Resume parsing
- Candidate matching and automated shortlisting
- AI-assisted interview workflows
- Interview scheduling and rescheduling
- Subscription management
- Razorpay payment integration
- Redis caching
- Celery background task processing
- AWS S3 file storage
- Swagger/OpenAPI documentation

## Technology Stack

- Python
- Django
- Django REST Framework
- SQLite / MySQL
- Redis
- Celery
- JWT Authentication
- AWS S3
- Razorpay
- Swagger/OpenAPI
- Postman
- Git & GitHub

## API Overview

The ZecPath backend contains REST API endpoints for authentication, candidate management, employer management, job management, applications, recruitment analytics, AI interview workflows, subscriptions, payments, and administrative operations.

The project currently includes **61 REST API endpoints** covering the major recruitment workflows.

## Project Structure

```text
zecpath-backend/
│
├── accounts/
├── coreapp/
├── zecpath_backend/
├── .github/
├── API_GUIDE.md
├── bug_resolution_report.txt
├── evaluation_feedback.txt
├── manage.py
├── requirements.txt
└── README.md

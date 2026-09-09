# ZecPath Backend – Project Documentation

## 1. Project Overview

ZecPath is a Django REST Framework based recruitment platform backend.

The backend provides APIs for:

- User authentication
- Candidate management
- Employer management
- Job management
- Job applications
- AI-based interview functionality
- Job analytics
- Subscription management
- Razorpay payment processing
- Resume/file storage using AWS S3
- Administrative operations

## 2. Technology Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- PostgreSQL/SQLite
- AWS S3
- django-storages
- Razorpay
- OpenAI API
- Celery
- Redis
- Gunicorn
- Render
- drf-spectacular / Swagger UI

## 3. Authentication

The API uses JWT authentication.

Users obtain an access token through:

`POST /api/token/`

The access token is then used to access protected API endpoints.

Swagger documentation is available at:

`/api/docs/`

OpenAPI schema is available at:

`/api/schema/`

## 4. API Documentation

The production API documentation is available through Swagger UI.

Production URL:

https://zecpath-backend-7zoy.onrender.com/api/docs/

The OpenAPI schema is available at:

https://zecpath-backend-7zoy.onrender.com/api/schema/

The API documentation includes authentication, candidate, employer, job, application, administrative, analytics, interview, subscription, and payment endpoints.

## 5. AI Interview System

The backend provides AI-assisted interview functionality.

The interview flow includes:

1. Starting an interview
2. Receiving interview questions
3. Submitting candidate answers
4. Evaluating answers
5. Generating evaluation scores

The evaluation includes metrics such as:

- Answer score
- Relevance score
- Completeness score
- Keyword score
- Confidence

## 6. Job and Employer Management

Employers can create and manage job postings.

The backend provides employer-specific permissions to ensure that employer operations are accessible only to authenticated users with the appropriate Employer role.

Job analytics are also available for monitoring application funnels.

## 7. Subscription and Payment System

ZecPath includes subscription plans such as:

- FREE
- PRO
- ENTERPRISE

Paid subscriptions use Razorpay for payment processing.

Payment flow:

1. Select subscription plan
2. Create Razorpay order
3. Open Razorpay checkout
4. Complete test payment
5. Verify Razorpay payment
6. Store transaction status
7. View payment history

The Razorpay integration was tested successfully using Razorpay test mode.

## 8. AWS S3 File Storage

Resume and file storage is configured using AWS S3.

The Django backend uses:

- boto3
- django-storages
- AWS S3

Production storage is configured through environment variables so that credentials are not hard-coded in the source code.

## 9. Production Deployment

The backend is deployed on Render.

Production URL:

https://zecpath-backend-7zoy.onrender.com

The application runs using Gunicorn.

The production deployment was successfully tested and is currently running on Render.

## 10. Production Security

Production configuration includes:

- DEBUG disabled
- HTTPS redirect
- Secure session cookies
- Secure CSRF cookies
- HTTP Strict Transport Security (HSTS)
- Configured production ALLOWED_HOSTS
- Environment-based secrets and credentials

Sensitive credentials are stored as environment variables instead of being committed to source control.

## 11. Testing

The backend was tested using:

- Django deployment checks
- Swagger UI
- API endpoint testing
- JWT authentication testing
- AI interview testing
- Job analytics testing
- Razorpay test payment
- Payment verification
- Payment history
- Render production deployment testing

## 12. Production Status

The ZecPath backend has been deployed successfully to Render.

Current production deployment:

`1da0711 – Enable drf spectacular in production`

Production API documentation is accessible through Swagger UI and the OpenAPI schema endpoint.

## 13. Conclusion

ZecPath provides a production-oriented recruitment backend with authentication, candidate and employer management, job applications, AI interview evaluation, analytics, subscriptions, payment processing, cloud storage, API documentation, and cloud deployment.
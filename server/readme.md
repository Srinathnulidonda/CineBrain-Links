<div align="center">

# 🔗 CinBrainLinks

### **Production-Grade Branded URL Shortener Platform**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

<br />

[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![API Status](https://img.shields.io/badge/API-Stable-success?style=flat-square)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)
[![Maintenance](https://img.shields.io/badge/Maintained-Yes-blue.svg?style=flat-square)]()

<br />

[**🚀 Live Demo**](https://cinbrainlinks.up.railway.app) · [**📖 API Docs**](#-api-reference) · [**🐛 Report Bug**](../../issues) · [**✨ Request Feature**](../../issues)

---

</div>

## 📋 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#-architecture)
- [🛠️ Tech Stack](#-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#-configuration)
- [📡 API Reference](#-api-reference)
- [🗄️ Database Schema](#-database-schema)
- [🚢 Deployment](#-deployment)
- [📊 Monitoring](#-monitoring)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features

<div align="center">

| | | |
|:---:|:---:|:---:|
| 🔐 **Secure Authentication** | 🔗 **URL Shortening** | 📊 **Click Analytics** |
| JWT-based auth with refresh tokens | Custom & auto-generated slugs | Real-time click tracking |
| 📧 **Email Integration** | ⚡ **High Performance** | 🛡️ **Enterprise Security** |
| Brevo SMTP/API support | Redis caching layer | Rate limiting & validation |
| 📱 **QR Code Generation** | ⏰ **Link Expiration** | 🎯 **Custom Slugs** |
| Dynamic QR codes for links | Set expiry dates | Branded short URLs |

</div>

### 🎯 Core Capabilities

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  🔐 AUTHENTICATION           │  🔗 URL MANAGEMENT                   │
│  ├─ User Registration        │  ├─ Create Short Links               │
│  ├─ JWT Access Tokens        │  ├─ Custom Slugs                     │
│  ├─ Refresh Token Rotation   │  ├─ Auto-Generated Slugs             │
│  ├─ Password Reset Flow      │  ├─ Link Expiration                  │
│  └─ Session Management       │  └─ Enable/Disable Links             │
│                              │                                      │
│  ⚡ PERFORMANCE              │  📊 ANALYTICS                        │
│  ├─ Redis Caching            │  ├─ Click Counting                   │
│  ├─ Async Click Tracking     │  ├─ Link Statistics                  │
│  ├─ Connection Pooling       │  └─ User Dashboard Stats             │
│  └─ Optimized Queries        │                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
                                    ┌─────────────────┐
                                    │  React Frontend │
                                    │   (Vercel/etc)  │
                                    └────────┬────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │      Railway Cloud       │
                              │  ┌────────────────────┐  │
                              │  │   Load Balancer    │  │
                              │  └──────────┬─────────┘  │
                              │             │            │
                              │             ▼            │
                              │  ┌────────────────────┐  │
                              │  │  Gunicorn Workers  │  │
                              │  │  ┌──────────────┐  │  │
                              │  │  │  Flask App   │  │  │
                              │  │  │ ┌──────────┐ │  │  │
                              │  │  │ │ Routes   │ │  │  │
                              │  │  │ │ Services │ │  │  │
                              │  │  │ │ Models   │ │  │  │
                              │  │  │ └──────────┘ │  │  │
                              │  │  └──────────────┘  │  │
                              │  └────────┬───────────┘  │
                              │           │              │
                              │     ┌─────┴─────┐        │
                              │     ▼           ▼        │
                              │  ┌──────┐   ┌────────┐   │
                              │  │Redis │   │Postgres│   │
                              │  │Cache │   │   DB   │   │
                              │  └──────┘   └────────┘   │
                              └──────────────────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │       Brevo SMTP         │
                              │    (Email Service)       │
                              └──────────────────────────┘
```

---

## 🛠️ Tech Stack

<div align="center">

### Backend Framework

[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

### Database & Cache

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://sqlalchemy.org)

### Authentication & Security

[![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=json-web-tokens&logoColor=white)](https://jwt.io)
[![Bcrypt](https://img.shields.io/badge/Bcrypt-003A70?style=for-the-badge&logo=letsencrypt&logoColor=white)]()

### Deployment & Infrastructure

[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn&logoColor=white)](https://gunicorn.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

### Email Service

[![Brevo](https://img.shields.io/badge/Brevo-0B1A8A?style=for-the-badge&logo=sendinblue&logoColor=white)](https://brevo.com)

</div>

### 📦 Complete Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.0 | Web framework |
| Flask-RESTful | 0.3.10 | REST API support |
| Flask-JWT-Extended | 4.6.0 | JWT authentication |
| Flask-SQLAlchemy | 3.1.1 | ORM integration |
| Flask-Migrate | 4.0.5 | Database migrations |
| Flask-CORS | 4.0.0 | Cross-origin support |
| Flask-Limiter | 3.5.0 | Rate limiting |
| SQLAlchemy | 2.0.23 | Database ORM |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| redis | 5.0.1 | Redis client |
| gunicorn | 21.2.0 | WSGI server |
| requests | 2.31.0 | HTTP client |
| qrcode | 7.4.2 | QR code generation |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Redis 7+**
- **Brevo Account** (for emails)

### 📥 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cinbrainlinks.git
cd cinbrainlinks/server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### ⚙️ Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit with your configuration
nano .env
```

### 🗄️ Database Setup

```bash
# Initialize migrations
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

### ▶️ Run Development Server

```bash
# Start the development server
python run.py

# Or with Flask CLI
flask run --debug
```

🎉 **Server is running at `http://localhost:5000`**

---

## ⚙️ Configuration

### 🔐 Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key (32+ chars) | `your-super-secret-key...` |
| `JWT_SECRET_KEY` | JWT signing key (32+ chars) | `your-jwt-secret-key...` |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `FRONTEND_URL` | Your frontend URL | `https://yourapp.vercel.app` |
| `BREVO_API_KEY` | Brevo API key | `xkeysib-...` |
| `BREVO_SENDER_EMAIL` | Sender email address | `noreply@yourdomain.com` |

### 📧 Email Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BREVO_API_KEY` | Brevo API key | - |
| `BREVO_SMTP_SERVER` | SMTP server | `smtp-relay.brevo.com` |
| `BREVO_SMTP_PORT` | SMTP port | `587` |
| `BREVO_SMTP_USERNAME` | SMTP username | - |
| `BREVO_SMTP_PASSWORD` | SMTP password | - |
| `BREVO_SENDER_EMAIL` | From email | `noreply@cinbrainlinks.com` |
| `BREVO_SENDER_NAME` | From name | `CinBrainLinks` |
| `REPLY_TO_EMAIL` | Reply-to email | Same as sender |

### 🔧 Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `production` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `*` |
| `RATELIMIT_DEFAULT` | Default rate limit | `200 per hour` |
| `SENTRY_DSN` | Sentry error tracking | - |

### 📁 Project Structure

```
server/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Flask extensions
│   │
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   └── link.py          # Link model
│   │
│   ├── routes/              # API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── links.py         # Link management routes
│   │   └── redirect.py      # URL redirection
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── redis_service.py # Redis caching
│   │   └── email_service.py # Email handling
│   │
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── validators.py    # Input validation
│       └── slug.py          # Slug generation
│
├── migrations/              # Database migrations
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
│
├── run.py                   # Development entry
├── wsgi.py                  # Production entry
├── Procfile                 # Railway process file
├── railway.json             # Railway config
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

---

## 📡 API Reference

### Base URL

| Environment | URL |
|-------------|-----|
| Production | `https://cinbrainlinks.up.railway.app` |
| Development | `http://localhost:5000` |

---

### 🔐 Authentication

#### POST `/api/auth/register` - Register new user

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "name": "John Doe"
}
```

**Response:** `201 Created`

```json
{
  "message": "Registration successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

#### POST `/api/auth/login` - Login user

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`

```json
{
  "message": "Login successful",
  "user": { "..." },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

#### POST `/api/auth/logout` - Logout user

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "message": "Logout successful"
}
```

---

#### POST `/api/auth/refresh` - Refresh access token

**Headers:** `Authorization: Bearer <refresh_token>`

**Response:** `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

#### GET `/api/auth/me` - Get current user

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "created_at": "2024-01-15T10:30:00Z",
    "links_count": 15
  }
}
```

---

#### POST `/api/auth/password/forgot` - Request password reset

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`

```json
{
  "message": "If an account exists with this email, a password reset link will be sent."
}
```

---

#### POST `/api/auth/password/reset` - Reset password

**Request Body:**

```json
{
  "token": "reset-token-from-email",
  "password": "NewSecurePass123!"
}
```

**Response:** `200 OK`

```json
{
  "message": "Password reset successful"
}
```

---

### 🔗 Links Management

#### POST `/api/links` - Create short link

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "url": "https://example.com/very/long/url/path",
  "custom_slug": "my-link",
  "expires_at": "2024-12-31T23:59:59Z",
  "title": "My Awesome Link",
  "description": "Link description"
}
```

**Response:** `201 Created`

```json
{
  "message": "Link created successfully",
  "link": {
    "id": "uuid",
    "slug": "my-link",
    "short_url": "https://cinbrainlinks.up.railway.app/my-link",
    "original_url": "https://example.com/very/long/url/path",
    "clicks": 0,
    "is_active": true,
    "expires_at": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

#### GET `/api/links` - Get all user links

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |
| `is_active` | bool | - | Filter by status |
| `sort` | string | created_at | Sort field |
| `order` | string | desc | Sort order (asc/desc) |

**Response:** `200 OK`

```json
{
  "links": ["..."],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 5,
    "total_items": 100,
    "has_next": true,
    "has_prev": false
  }
}
```

---

#### GET `/api/links/:id` - Get single link

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "link": {
    "id": "uuid",
    "slug": "my-link",
    "short_url": "https://cinbrainlinks.up.railway.app/my-link",
    "original_url": "https://example.com/...",
    "clicks": 42,
    "is_active": true,
    "expires_at": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

#### PUT `/api/links/:id` - Update link

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "is_active": false,
  "expires_at": "2024-06-30T23:59:59Z",
  "title": "Updated Title"
}
```

**Response:** `200 OK`

```json
{
  "message": "Link updated successfully",
  "link": { "..." }
}
```

---

#### DELETE `/api/links/:id` - Delete link

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "message": "Link deleted successfully"
}
```

---

#### POST `/api/links/:id/toggle` - Toggle link status

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "message": "Link enabled successfully",
  "link": { "..." }
}
```

---

#### GET `/api/links/stats` - Get user statistics

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "stats": {
    "total_links": 25,
    "active_links": 20,
    "inactive_links": 5,
    "total_clicks": 1523,
    "expiring_soon": 3
  },
  "top_links": ["..."]
}
```

---

#### GET `/api/links/check-slug?slug=my-link` - Check slug availability

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `200 OK`

```json
{
  "slug": "my-link",
  "available": true
}
```

---

### 🔀 Redirect

#### GET `/:slug` - Redirect to original URL

**Response:** `302 Redirect` to original URL

**Error Responses:**
- `404 Not Found` - Link doesn't exist
- `410 Gone` - Link expired or disabled

---

#### GET `/:slug/preview` - Preview link

**Response:** `200 OK`

```json
{
  "preview": {
    "slug": "my-link",
    "short_url": "https://cinbrainlinks.up.railway.app/my-link",
    "original_url": "https://example.com/...",
    "title": "Link Title",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

#### GET `/:slug/qr` - Get QR code

**Response:** `200 OK`

```json
{
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "short_url": "https://cinbrainlinks.up.railway.app/my-link"
}
```

---

### 🏥 Health Check

#### GET `/health` - Service health status

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "CinBrainLinks",
  "environment": "production",
  "database": "connected",
  "redis": "connected"
}
```

---

## 🗄️ Database Schema

### Users Table

```sql
┌─────────────────────────────────────────────────────────────────┐
│                           USERS                                  │
├─────────────────┬──────────────┬────────────────────────────────┤
│ id              │ UUID         │ PRIMARY KEY                    │
│ email           │ VARCHAR(255) │ UNIQUE, NOT NULL               │
│ password_hash   │ VARCHAR(255) │ NOT NULL                       │
│ is_active       │ BOOLEAN      │ DEFAULT true                   │
│ email_verified  │ BOOLEAN      │ DEFAULT false                  │
│ created_at      │ TIMESTAMP    │ DEFAULT now()                  │
│ updated_at      │ TIMESTAMP    │ DEFAULT now()                  │
└─────────────────┴──────────────┴────────────────────────────────┘
```

### Links Table

```sql
┌─────────────────────────────────────────────────────────────────┐
│                           LINKS                                  │
├─────────────────┬──────────────┬────────────────────────────────┤
│ id              │ UUID         │ PRIMARY KEY                    │
│ user_id         │ UUID         │ FOREIGN KEY → users.id         │
│ slug            │ VARCHAR(50)  │ UNIQUE, NOT NULL               │
│ original_url    │ TEXT         │ NOT NULL                       │
│ clicks          │ BIGINT       │ DEFAULT 0                      │
│ is_active       │ BOOLEAN      │ DEFAULT true                   │
│ expires_at      │ TIMESTAMP    │ NULLABLE                       │
│ title           │ VARCHAR(255) │ NULLABLE                       │
│ description     │ TEXT         │ NULLABLE                       │
│ created_at      │ TIMESTAMP    │ DEFAULT now()                  │
│ updated_at      │ TIMESTAMP    │ DEFAULT now()                  │
└─────────────────┴──────────────┴────────────────────────────────┘
```

---

## 🚢 Deployment

### 🚂 Railway Deployment (Recommended)

#### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/cinbrainlinks)

#### Manual Deployment

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Initialize project
railway init

# 4. Add PostgreSQL
railway add --plugin postgresql

# 5. Add Redis
railway add --plugin redis

# 6. Set environment variables
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set FRONTEND_URL="https://your-frontend.vercel.app"
railway variables set BREVO_API_KEY="xkeysib-your-key"
railway variables set BREVO_SENDER_EMAIL="noreply@yourdomain.com"

# 7. Deploy
railway up

# 8. Get your domain
railway domain
```

---

### 🐳 Docker Deployment

```bash
# Build image
docker build -t cinbrainlinks .

# Run container
docker run -d \
  --name cinbrainlinks \
  -p 5000:5000 \
  --env-file .env \
  cinbrainlinks
```

**Docker Compose:**

```bash
docker-compose up -d
```

---

### 🖥️ Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="your-secret-key"
export DATABASE_URL="postgresql://..."
# ... other variables

# Run with Gunicorn
gunicorn wsgi:app \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 120
```

---

## 📊 Monitoring

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Full health check with DB & Redis status |
| `GET /` | API info and status |

### Logging

Logs are output to stdout for Railway's log aggregation:

```
2024-01-15 10:30:00 - app - INFO - ✅ Database connected
2024-01-15 10:30:01 - app - INFO - ✅ Redis connected
2024-01-15 10:30:02 - app - INFO - ✅ Email service initialized (API)
2024-01-15 10:30:05 - app - INFO - 🔗 Link created: my-link
2024-01-15 10:30:10 - app - INFO - ↗️ Redirect: my-link (cache hit)
```

### Sentry Integration (Optional)

```bash
railway variables set SENTRY_DSN="https://your-sentry-dsn@sentry.io/project"
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── conftest.py          # Test fixtures
├── test_auth.py         # Authentication tests
├── test_links.py        # Link management tests
├── test_redirect.py     # Redirect tests
└── test_validators.py   # Validation tests
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contributing Steps

```bash
# 1. Fork the repository

# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes and commit
git commit -m "feat: add amazing feature"

# 4. Push to branch
git push origin feature/amazing-feature

# 5. Open Pull Request
```

### Commit Convention

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Code style |
| `refactor` | Code refactoring |
| `test` | Tests |
| `chore` | Maintenance |

---

## 📄 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) file for details.

---

<div align="center">

### 💖 Support

If you found this project helpful, please consider:

⭐ **Star this repo** · 🍴 **Fork this repo** · 📢 **Share with others**

---

**Made with ❤️ by the CinBrainLinks Team**

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github)](https://github.com/yourusername)
[![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://twitter.com/yourusername)

</div>

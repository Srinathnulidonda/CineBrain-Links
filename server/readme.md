<div align="center">

# 🔗 Savlink

### **Save Once. Use Forever.**

Your personal link operating system — save, organize, and optionally shorten your important links

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Railway](https://img.shields.io/badge/Railway-Deployed-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

<br />

[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)
[![API](https://img.shields.io/badge/API-v2.0-success?style=flat-square)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

<br />

[**🚀 Live App**](https://savlink.vercel.app) · [**📖 API Docs**](#-api-reference) · [**🐛 Report Bug**](../../issues) · [**✨ Request Feature**](../../issues)

---

</div>

## 🎯 What is Savlink?

**Savlink is NOT just a URL shortener.** It's a personal link management system that lets you:

- 📌 **Save important links** — Build your personal collection of links you use repeatedly
- 📁 **Organize with folders & tags** — Keep everything structured and findable
- 🔗 **Optionally shorten URLs** — Create clean, branded short links when you need them
- 📊 **Track engagement** — See how your shared links perform
- 🔒 **Keep links private** — Your saved links are yours alone

> **Philosophy:** Links are long-term personal assets, not disposable redirects.

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
- [📡 API Reference](#-api-reference)
- [🗄️ Database Schema](#️-database-schema)
- [🚢 Deployment](#-deployment)
- [📊 Monitoring](#-monitoring)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)

---

## ✨ Features

<div align="center">

### Core Features

| | | |
|:---:|:---:|:---:|
| 📌 **Save Links** | 🔗 **Shorten URLs** | 📁 **Folders** |
| Build your personal collection | Optional short links with custom slugs | Organize links into collections |
| 🏷️ **Tags** | 📊 **Analytics** | 🔍 **Search** |
| Flexible categorization | Click tracking & insights | Full-text search across all links |
| 📱 **QR Codes** | 🔒 **Private Sharing** | 🗑️ **Trash & Restore** |
| Dynamic QR generation | Password-protected share links | Soft delete with recovery |
| 🏥 **Health Monitoring** | 📋 **Templates** | 📤 **Import/Export** |
| Automatic broken link detection | Quick-create from templates | Backup & migrate your data |

</div>

### 🔄 Dual Link Types

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  📌 SAVED LINKS                   │  🔗 SHORTENED LINKS             │
│  ─────────────────                │  ──────────────────             │
│  • Private to your account        │  • Public redirect URL          │
│  • No slug required               │  • Custom or auto-generated slug│
│  • Dashboard access only          │  • Click tracking enabled       │
│  • Perfect for bookmarks          │  • Great for sharing            │
│  • Never publicly accessible      │  • Optional expiration          │
│                                   │                                 │
│  Example:                         │  Example:                       │
│  Save your bank login page        │  Share a campaign link          │
│  Save your favorite recipes       │  savlink.vercel.app/my-promo    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 🎯 Complete Feature List

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  🔐 AUTHENTICATION               │  📁 ORGANIZATION                 │
│  ├─ JWT Access/Refresh Tokens    │  ├─ Folders with nesting         │
│  ├─ Password Reset Flow          │  ├─ Tags with colors             │
│  ├─ Session Management           │  ├─ System categories            │
│  └─ Email Verification           │  └─ Pin important links          │
│                                  │                                  │
│  📊 ANALYTICS                    │  🔗 LINK MANAGEMENT              │
│  ├─ Click tracking               │  ├─ Save without shortening      │
│  ├─ Referrer analysis            │  ├─ Shorten with custom slug     │
│  ├─ Device/browser stats         │  ├─ Duplicate detection          │
│  ├─ Geographic data              │  ├─ Version history              │
│  └─ Timeline visualization       │  └─ Bulk operations              │
│                                  │                                  │
│  🔒 PRIVACY & SHARING            │  🛠️ UTILITIES                    │
│  ├─ Private saved links          │  ├─ QR code generation           │
│  ├─ Password-protected shares    │  ├─ Link preview                 │
│  ├─ Expiring share links         │  ├─ Health monitoring            │
│  └─ View limits                  │  ├─ Import/Export                │
│                                  │  └─ Link templates               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
                                    ┌─────────────────┐
                                    │  React Frontend │
                                    │ savlink.vercel  │
                                    └────────┬────────┘
                                             │
                              All short URLs: savlink.vercel.app/<slug>
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │      Railway Cloud       │
                              │  ┌────────────────────┐  │
                              │  │   Gunicorn + Flask │  │
                              │  │                    │  │
                              │  │  ┌──────────────┐  │  │
                              │  │  │   Routes     │  │  │
                              │  │  │  ──────────  │  │  │
                              │  │  │  • auth      │  │  │
                              │  │  │  • links     │  │  │
                              │  │  │  • folders   │  │  │
                              │  │  │  • tags      │  │  │
                              │  │  │  • analytics │  │  │
                              │  │  │  • sharing   │  │  │
                              │  │  │  • search    │  │  │
                              │  │  │  • bulk      │  │  │
                              │  │  │  • health    │  │  │
                              │  │  │  • redirect  │  │  │
                              │  │  └──────────────┘  │  │
                              │  └─────────┬──────────┘  │
                              │            │             │
                              │      ┌─────┴─────┐       │
                              │      ▼           ▼       │
                              │  ┌───────┐  ┌────────┐   │
                              │  │ Redis │  │Postgres│   │
                              │  │(Cache)│  │  (DB)  │   │
                              │  └───────┘  └────────┘   │
                              └──────────────────────────┘
                                          │
                                          ▼
                              ┌──────────────────────────┐
                              │     Brevo (Email)        │
                              └──────────────────────────┘
```

### 🌐 URL Strategy

| URL Type | Domain | Example |
|----------|--------|---------|
| **Frontend App** | `savlink.vercel.app` | `savlink.vercel.app/dashboard` |
| **Short Links** | `savlink.vercel.app` | `savlink.vercel.app/my-link` |
| **Share Links** | `savlink.vercel.app` | `savlink.vercel.app/s/abc123` |
| **Backend API** | `*.railway.app` | Never exposed to users |

> ⚠️ **Important:** The Railway backend URL is never shown to users. All public-facing URLs use `savlink.vercel.app`.

---

## 🛠️ Tech Stack

<div align="center">

### Backend Framework

[![Flask](https://img.shields.io/badge/Flask_3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

### Database & Cache

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)

### Infrastructure

[![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)

</div>

### 📦 Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.0.0 | Web framework |
| Flask-JWT-Extended | 4.6.0 | JWT authentication |
| Flask-SQLAlchemy | 3.1.1 | ORM |
| Flask-Migrate | 4.0.5 | Database migrations |
| Flask-Limiter | 3.5.0 | Rate limiting |
| redis | 5.0.1 | Caching |
| requests | 2.31.0 | HTTP client |
| beautifulsoup4 | 4.12.2 | Metadata extraction |
| user-agents | 2.2.0 | User agent parsing |
| qrcode | 7.4.2 | QR code generation |
| gunicorn | 21.2.0 | Production server |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Brevo Account (optional, for emails)

### 📥 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/savlink.git
cd savlink/server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### ⚙️ Configure Environment

Edit `.env` with your settings:

```bash
# Required
SECRET_KEY=your-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
DATABASE_URL=postgresql://user:pass@localhost:5432/savlink

# Critical URLs
PUBLIC_BASE_URL=https://savlink.vercel.app
FRONTEND_URL=https://savlink.vercel.app

# Optional
REDIS_URL=redis://localhost:6379
BREVO_API_KEY=your-brevo-key
```

### 🗄️ Database Setup

```bash
# Run migrations
flask db upgrade
```

### ▶️ Run Development Server

```bash
python run.py
```

🎉 **API running at `http://localhost:5000`**

---

## ⚙️ Configuration

### 🔐 Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret (32+ chars) | `openssl rand -hex 32` |
| `JWT_SECRET_KEY` | JWT secret (32+ chars) | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql://...` |
| `PUBLIC_BASE_URL` | **Public-facing URL** | `https://savlink.vercel.app` |
| `FRONTEND_URL` | Frontend app URL | `https://savlink.vercel.app` |

### 🌐 URL Configuration (Critical)

| Variable | Purpose | Production Value |
|----------|---------|------------------|
| `PUBLIC_BASE_URL` | Short link URLs, QR codes, emails | `https://savlink.vercel.app` |
| `FRONTEND_URL` | Password reset links, dashboard URLs | `https://savlink.vercel.app` |
| `BASE_URL` | Backend URL (internal only) | `https://your-app.railway.app` |

> ⚠️ **Never expose `BASE_URL` to users.** All user-facing URLs must use `PUBLIC_BASE_URL`.

### 📧 Email Configuration (Optional)

| Variable | Description |
|----------|-------------|
| `BREVO_API_KEY` | Brevo API key |
| `BREVO_SENDER_EMAIL` | From email address |
| `BREVO_SENDER_NAME` | From display name |

### 🔧 Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_LINKS_PER_USER` | 10000 | Link limit per user |
| `CLICK_RETENTION_DAYS` | 365 | Click data retention |
| `ENABLE_WEEKLY_DIGEST` | false | Weekly email digest |
| `ENABLE_BROKEN_LINK_ALERTS` | true | Broken link notifications |

### 📁 Project Structure

```
server/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Configuration
│   ├── extensions.py            # Flask extensions
│   │
│   ├── models/                  # Database models
│   │   ├── user.py              # User model
│   │   ├── link.py              # Link model (dual types)
│   │   ├── folder.py            # Folder model
│   │   ├── tag.py               # Tag model
│   │   ├── link_click.py        # Click analytics
│   │   ├── link_version.py      # Version history
│   │   ├── shared_link.py       # Private sharing
│   │   ├── link_health.py       # Health checks
│   │   ├── category.py          # System categories
│   │   ├── activity_log.py      # Activity feed
│   │   └── link_template.py     # Templates
│   │
│   ├── routes/                  # API endpoints
│   │   ├── auth.py              # Authentication
│   │   ├── links.py             # Link CRUD
│   │   ├── redirect.py          # URL redirection
│   │   ├── folders.py           # Folder management
│   │   ├── tags.py              # Tag management
│   │   ├── analytics.py         # Click analytics
│   │   ├── sharing.py           # Private sharing
│   │   ├── health.py            # Link health
│   │   ├── bulk.py              # Bulk operations
│   │   ├── activity.py          # Activity feed
│   │   ├── templates.py         # Link templates
│   │   ├── categories.py        # Categories
│   │   └── search.py            # Search
│   │
│   ├── services/                # Business logic
│   │   ├── redis_service.py     # Caching
│   │   ├── email_service.py     # Email delivery
│   │   ├── activity_service.py  # Activity logging
│   │   ├── click_service.py     # Click tracking
│   │   ├── health_service.py    # Health monitoring
│   │   ├── metadata_service.py  # OG data extraction
│   │   ├── link_service.py      # Link operations
│   │   └── export_service.py    # Import/Export
│   │
│   └── utils/                   # Utilities
│       ├── validators.py        # Input validation
│       ├── slug.py              # Slug generation
│       ├── base_url.py          # URL helpers
│       └── helpers.py           # Common utilities
│
├── migrations/                  # Database migrations
├── run.py                       # Development entry
├── wsgi.py                      # Production entry
├── requirements.txt             # Dependencies
└── Procfile                     # Railway config
```

---

## 📡 API Reference

### Base URLs

| Environment | URL |
|-------------|-----|
| Production API | `https://your-app.railway.app/api` |
| Short Links | `https://savlink.vercel.app/<slug>` |
| Development | `http://localhost:5000/api` |

### Response Format

```json
// Success
{
  "success": true,
  "message": "Operation completed",
  "data": { }
}

// Error
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE"
  }
}
```

---

### 🔐 Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create new account |
| `/api/auth/login` | POST | Sign in |
| `/api/auth/logout` | POST | Sign out |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/me` | GET | Get current user |
| `/api/auth/password/forgot` | POST | Request password reset |
| `/api/auth/password/reset` | POST | Reset password |
| `/api/auth/password/change` | POST | Change password |

---

### 🔗 Links

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/links` | POST | Create link (saved or shortened) |
| `/api/links` | GET | List user's links with filters |
| `/api/links/:id` | GET | Get single link |
| `/api/links/:id` | PUT | Update link |
| `/api/links/:id` | DELETE | Delete link (soft/permanent) |
| `/api/links/:id/restore` | POST | Restore from trash |
| `/api/links/:id/pin` | POST | Pin link |
| `/api/links/:id/unpin` | POST | Unpin link |
| `/api/links/:id/toggle` | POST | Toggle active status |
| `/api/links/:id/duplicate` | POST | Duplicate link |
| `/api/links/:id/versions` | GET | Get version history |
| `/api/links/stats` | GET | Get statistics |
| `/api/links/trash` | GET | List deleted links |
| `/api/links/trash/empty` | DELETE | Empty trash |
| `/api/links/check-slug` | GET | Check slug availability |
| `/api/links/check-duplicate` | GET | Check if URL exists |

#### Create Link Examples

**Save a link (no shortening):**
```json
POST /api/links
{
  "url": "https://example.com/my-important-page",
  "link_type": "saved",
  "title": "My Important Page",
  "folder_id": "folder-uuid",
  "tag_ids": ["tag-uuid-1", "tag-uuid-2"]
}
```

**Create a shortened link:**
```json
POST /api/links
{
  "url": "https://example.com/very/long/url",
  "link_type": "shortened",
  "custom_slug": "my-promo",
  "title": "Promo Campaign",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

---

### 📁 Folders

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/folders` | POST | Create folder |
| `/api/folders` | GET | List folders |
| `/api/folders/:id` | GET | Get folder |
| `/api/folders/:id` | PUT | Update folder |
| `/api/folders/:id` | DELETE | Delete folder |
| `/api/folders/reorder` | POST | Reorder folders |
| `/api/folders/:id/links` | GET | Get folder's links |

---

### 🏷️ Tags

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tags` | POST | Create tag |
| `/api/tags` | GET | List tags |
| `/api/tags/:id` | GET | Get tag |
| `/api/tags/:id` | PUT | Update tag |
| `/api/tags/:id` | DELETE | Delete tag |
| `/api/tags/:id/links` | GET | Get tagged links |
| `/api/tags/stats` | GET | Tag usage statistics |

---

### 📊 Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/links/:id` | GET | Link analytics |
| `/api/analytics/links/:id/clicks` | GET | Click history |
| `/api/analytics/overview` | GET | User analytics overview |

---

### 🔒 Sharing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/share/links/:id` | POST | Create share link |
| `/api/share/links/:id` | GET | List link's shares |
| `/api/share/:id` | DELETE | Revoke share |
| `/api/share/s/:token` | GET | Access shared link |
| `/api/share/s/:token/verify` | POST | Verify share password |

---

### 🏥 Health Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/links/:id/check` | POST | Check link health |
| `/api/health/links/:id/history` | GET | Health check history |
| `/api/health/broken` | GET | List broken links |
| `/api/health/check-all` | POST | Check all stale links |

---

### 📦 Bulk Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bulk/move` | POST | Move links to folder |
| `/api/bulk/tag` | POST | Add/remove tags |
| `/api/bulk/delete` | POST | Delete multiple links |
| `/api/bulk/restore` | POST | Restore multiple links |
| `/api/bulk/toggle` | POST | Enable/disable links |
| `/api/bulk/export` | POST | Export links |

---

### 🔍 Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Full-text search |
| `/api/search/suggestions` | GET | Search autocomplete |

---

### 🔀 Redirect & Utilities

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/:slug` | GET | Redirect to original URL |
| `/:slug/preview` | GET | Preview link info |
| `/:slug/qr` | GET | Get QR code |

---

### 📋 Other Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/activity` | GET | Activity feed |
| `/api/activity/summary` | GET | Activity summary |
| `/api/templates` | CRUD | Link templates |
| `/api/categories` | GET | System categories |
| `/health` | GET | Service health check |

---

## 🗄️ Database Schema

### Core Tables

```sql
┌─────────────────────────────────────────────────────────────────────┐
│                              LINKS                                   │
├──────────────────────┬──────────────┬───────────────────────────────┤
│ id                   │ UUID         │ PRIMARY KEY                   │
│ user_id              │ UUID         │ FK → users.id                 │
│ link_type            │ ENUM         │ 'saved' | 'shortened'         │
│ slug                 │ VARCHAR(50)  │ UNIQUE, NULLABLE              │
│ original_url         │ TEXT         │ NOT NULL                      │
│ title                │ VARCHAR(255) │                               │
│ notes                │ TEXT         │ Markdown supported            │
│ folder_id            │ UUID         │ FK → folders.id               │
│ category_id          │ UUID         │ FK → categories.id            │
│ is_active            │ BOOLEAN      │ DEFAULT true                  │
│ is_pinned            │ BOOLEAN      │ DEFAULT false                 │
│ is_deleted           │ BOOLEAN      │ DEFAULT false (soft delete)   │
│ is_broken            │ BOOLEAN      │ DEFAULT false                 │
│ clicks               │ BIGINT       │ DEFAULT 0                     │
│ click_tracking       │ BOOLEAN      │ DEFAULT true                  │
│ privacy_level        │ ENUM         │ 'private'|'unlisted'|'public' │
│ expires_at           │ TIMESTAMP    │                               │
│ favicon_url          │ VARCHAR(512) │ Auto-fetched                  │
│ og_title             │ VARCHAR(255) │ Open Graph                    │
│ og_description       │ TEXT         │ Open Graph                    │
│ og_image             │ VARCHAR(512) │ Open Graph                    │
│ custom_metadata      │ JSON         │ Flexible storage              │
│ created_at           │ TIMESTAMP    │                               │
│ updated_at           │ TIMESTAMP    │                               │
└──────────────────────┴──────────────┴───────────────────────────────┘
```

### Organization Tables

```sql
FOLDERS                          TAGS                    LINK_TAGS
├─ id (PK)                       ├─ id (PK)              ├─ link_id (PK, FK)
├─ user_id (FK)                  ├─ user_id (FK)         └─ tag_id (PK, FK)
├─ name                          ├─ name
├─ color                         ├─ color
├─ icon                          └─ created_at
├─ parent_id (FK, self)
└─ sort_order
```

### Analytics Tables

```sql
LINK_CLICKS                      LINK_VERSIONS           LINK_HEALTH_CHECKS
├─ id (PK)                       ├─ id (PK)              ├─ id (PK)
├─ link_id (FK)                  ├─ link_id (FK)         ├─ link_id (FK)
├─ clicked_at                    ├─ previous_url         ├─ status_code
├─ ip_hash                       ├─ previous_slug        ├─ response_time_ms
├─ user_agent                    ├─ previous_title       ├─ is_healthy
├─ referrer_domain               ├─ changed_by           ├─ error_message
├─ device_type                   └─ created_at           └─ checked_at
├─ browser
├─ os
└─ country_code
```

### Sharing & Activity Tables

```sql
SHARED_LINKS                     ACTIVITY_LOGS
├─ id (PK)                       ├─ id (PK)
├─ link_id (FK)                  ├─ user_id (FK)
├─ share_token (UNIQUE)          ├─ activity_type
├─ password_hash                 ├─ resource_type
├─ expires_at                    ├─ resource_id
├─ max_views                     ├─ resource_title
├─ view_count                    ├─ metadata (JSON)
└─ is_active                     └─ created_at
```

---

## 🚢 Deployment

### 🚂 Railway (Recommended)

#### One-Click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/savlink)

#### Manual Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and initialize
railway login
railway init

# Add services
railway add --plugin postgresql
railway add --plugin redis

# Set environment variables
railway variables set SECRET_KEY="$(openssl rand -hex 32)"
railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
railway variables set PUBLIC_BASE_URL="https://savlink.vercel.app"
railway variables set FRONTEND_URL="https://savlink.vercel.app"

# Deploy
railway up
```

### 🐳 Docker

```bash
# Build and run
docker build -t savlink .
docker run -d -p 5000:5000 --env-file .env savlink

# Or with Docker Compose
docker-compose up -d
```

### 📋 Deployment Checklist

- [ ] Set `SECRET_KEY` and `JWT_SECRET_KEY` (production-grade)
- [ ] Configure `DATABASE_URL` (PostgreSQL)
- [ ] Set `PUBLIC_BASE_URL` to `https://savlink.vercel.app`
- [ ] Set `FRONTEND_URL` to `https://savlink.vercel.app`
- [ ] Configure `REDIS_URL` (optional but recommended)
- [ ] Set up Brevo for emails (optional)
- [ ] Run database migrations: `flask db upgrade`
- [ ] Verify `/health` endpoint returns healthy

---

## 📊 Monitoring

### Health Check

```bash
curl https://your-app.railway.app/health
```

```json
{
  "status": "healthy",
  "service": "Savlink",
  "version": "2.0.0",
  "database": "connected",
  "cache": "connected"
}
```

### Logging

Logs are structured and output to stdout:

```
2024-01-15 10:30:00 [INFO] Link created: my-link (shortened) by user abc123
2024-01-15 10:30:05 [INFO] Cache hit for link: my-link
2024-01-15 10:30:10 [WARNING] Broken link detected: xyz789
```

### Sentry Integration

```bash
railway variables set SENTRY_DSN="https://...@sentry.io/..."
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific tests
pytest tests/test_links.py -v
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md).

```bash
# Fork and clone
git clone https://github.com/yourusername/savlink.git

# Create feature branch
git checkout -b feature/amazing-feature

# Commit with conventional commits
git commit -m "feat: add amazing feature"

# Push and create PR
git push origin feature/amazing-feature
```

### Commit Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `refactor` | Code refactoring |
| `test` | Tests |
| `chore` | Maintenance |

---

## 📄 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

### 💖 Support

If you find Savlink useful:

⭐ **Star this repo** · 🍴 **Fork it** · 📢 **Share it**

---

**Made with ❤️ by the Savlink Team**

*Save once. Use forever.*

</div>
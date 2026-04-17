# Deployment Guide

This guide covers deploying TradeCRM to a production environment.

---

## Prerequisites

- Python 3.9+
- Node.js 20+
- PostgreSQL 16 (managed service recommended)
- Redis 7
- A domain with HTTPS configured

---

## Environment Variables

### Backend (`app/backend/.env`)

**Required for all deployments**:

```
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname?ssl=require

# Redis
REDIS_URL=redis://user:password@host:6379/0

# Clerk Authentication
CLERK_SECRET_KEY=sk_live_xxx
CLERK_PUBLISHABLE_KEY=pk_live_xxx
CLERK_JWT_ISSUER=https://your-app.clerk.accounts.dev

# App URLs
FRONTEND_URL=https://app.yourdomain.com
BACKEND_URL=https://api.yourdomain.com

# Token encryption
ENCRYPTION_KEY=your-32-byte-fernet-key
```

**Enrichment pipeline** (required for company enrichment):

```
PERPLEXITY_API_KEY=pplx-xxx
FIRECRAWL_API_KEY=fc-xxx
APOLLO_API_KEY=xxx
GEMINI_API_KEY=xxx
```

**Gmail integration** (required for email features):

```
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/email/callback/gmail
```

**WhatsApp** (required for WhatsApp features):

```
# Direct API mode
GUPSHUP_HSM_USERID=xxx
GUPSHUP_HSM_PASSWORD=xxx
GUPSHUP_TWOWAY_USERID=xxx
GUPSHUP_TWOWAY_PASSWORD=xxx
GUPSHUP_WABA_NUMBER=919876543210
GUPSHUP_API_KEY=xxx
GUPSHUP_APP_ID=xxx
GUPSHUP_WEBHOOK_URL=https://api.yourdomain.com/webhooks/gupshup
GUPSHUP_WEBHOOK_SECRET=xxx
```

**Email delivery** (required for campaign emails):

```
SENDGRID_API_KEY=SG.xxx
```

**Billing** (optional):

```
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_STARTER_PRICE_ID=price_xxx
STRIPE_GROWTH_PRICE_ID=price_xxx
STRIPE_PRO_PRICE_ID=price_xxx
```

### Frontend (`app/frontend/.env.local`)

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_xxx
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/login
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/signup
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/onboarding
```

---

## Database Setup

### Option A: Neon (Recommended)

1. Create a project at https://neon.tech
2. Create a database (e.g., `tradecrm`)
3. Copy the connection string (use the pooled connection URL)
4. Set `DATABASE_URL` with the `postgresql+asyncpg://` prefix and `?ssl=require` suffix

### Option B: Supabase

1. Create a project at https://supabase.com
2. Go to Settings > Database > Connection String
3. Use the "URI" format, replacing `postgres://` with `postgresql+asyncpg://`
4. Add `?ssl=require` to the connection string

### Option C: Self-Hosted PostgreSQL

1. Install PostgreSQL 16
2. Create a database and user:
   ```sql
   CREATE USER tradecrm WITH PASSWORD 'your-password';
   CREATE DATABASE tradecrm OWNER tradecrm;
   ```
3. Set `DATABASE_URL=postgresql+asyncpg://tradecrm:your-password@localhost:5432/tradecrm`

### Running Migrations

```bash
cd app/backend
pip install -e .
alembic upgrade head
```

Run this after every deployment that includes schema changes.

---

## Redis Setup

### Managed Redis

Use a managed Redis service (Upstash, Redis Cloud, AWS ElastiCache, etc.):

```
REDIS_URL=rediss://user:password@host:6379/0
```

Note: Use `rediss://` (with double s) for TLS connections.

### Self-Hosted Redis

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

```
REDIS_URL=redis://localhost:6379/0
```

---

## Backend Deployment

### Build

```bash
cd app/backend
pip install -e .
```

### Run with Uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

For production, use Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker

Create a `Dockerfile` in `app/backend/`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Celery Worker

Start a Celery worker for background task processing:

```bash
celery -A app.tasks.worker worker --loglevel=info --concurrency=4
```

---

## Frontend Deployment

### Build

```bash
cd app/frontend
npm install
npm run build
```

### Run

```bash
npm start
```

The frontend listens on port 3000 by default. Use the `PORT` env var to change it.

### Vercel (Recommended)

1. Connect your repository to Vercel
2. Set the root directory to `app/frontend`
3. Add all `NEXT_PUBLIC_*` environment variables
4. Deploy

### Docker

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next .next
COPY --from=builder /app/node_modules node_modules
COPY --from=builder /app/package.json .
EXPOSE 3000
CMD ["npm", "start"]
```

---

## Reverse Proxy

### Nginx Configuration

```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 443 ssl;
    server_name app.yourdomain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Webhook Configuration

After deployment, configure webhook URLs in each service:

| Service | Webhook URL |
|---------|------------|
| Clerk | `https://api.yourdomain.com/webhooks/clerk` |
| GupShup | `https://api.yourdomain.com/webhooks/gupshup` |
| SendGrid | `https://api.yourdomain.com/webhooks/sendgrid` |
| Stripe | `https://api.yourdomain.com/webhooks/stripe` |

---

## Monitoring

### Health Check

The backend provides a health endpoint at the root or `/health` (check your `main.py`). Use this for load balancer health checks.

### Logging

The backend uses structured logging via `app/logging_config.py`. Logs include tenant ID, user ID, and operation context. Route logs to your preferred aggregation service (Datadog, CloudWatch, etc.).

### Key Metrics to Monitor

| Metric | Source |
|--------|--------|
| API response times | Backend access logs |
| Enrichment success rate | `agent_tasks` table (completed vs failed) |
| Message delivery rate | `messages` table (delivered vs failed) |
| Credit consumption | `GET /billing/usage` |
| Database connection pool | asyncpg pool stats |
| Redis memory usage | Redis INFO command |

---

## Security Checklist

- [ ] All API keys stored as environment variables, never in code
- [ ] HTTPS enabled for both frontend and backend domains
- [ ] `ENCRYPTION_KEY` set to a strong Fernet key for OAuth token encryption
- [ ] Clerk webhook signature verification enabled
- [ ] GupShup webhook secret configured
- [ ] Database SSL required (`?ssl=require` in connection string)
- [ ] Redis TLS enabled for managed services (`rediss://`)
- [ ] CORS configured to allow only your frontend domain
- [ ] `DEV_MODE` set to `false` in production

# TradeCRM

**The open-source CRM for cross-border commodity traders.**

TradeCRM is a full-stack CRM and sales intelligence platform purpose-built for commodity exporters and importers. It replaces the fragmented workflow of Excel buyer lists, WhatsApp conversations, shipment research tools, and email outreach spreadsheets with a single system that handles company profiling, contact discovery, multi-channel outreach, pipeline management, and trade analytics -- all powered by AI agents that automate the heavy lifting.

Built with FastAPI, Next.js 16, and PostgreSQL. Designed for multi-tenant SaaS deployment.

---

## Features

### Company Management
Full company profiles with trade-specific fields: commodities, preferred incoterms, payment terms, destination ports, import volumes, certifications, bank details, and trade references. Soft-delete, search, and filtering by country, commodity, and enrichment status.

### Contact Management
Contact records linked to companies with role tracking, decision-maker flagging, opt-in status for email and WhatsApp, and custom fields. CSV import with automatic deduplication by email and phone. Contact lists for campaign targeting.

### AI-Powered Enrichment
A four-step enrichment pipeline that transforms a company name into a full profile:
1. **Perplexity** -- web search for website, LinkedIn, description, industry
2. **Firecrawl** (parallel with Apollo Org) -- site mapping, page scraping, and markdown extraction
3. **Gemini** -- structured parsing of website content into company data, products, certifications, and personnel
4. **Apollo** -- conditional contact discovery with three scenarios: skip if website provided contacts (A), enrich known names (B), or full discovery (C)

Outputs a confidence score (0.0-1.0) and auto-creates Contact records for discovered decision makers.

### Multi-Channel Outreach
- **Email**: Gmail OAuth integration for reading, sending, replying, drafting, and label management. SendGrid for transactional delivery with warmup scheduling.
- **WhatsApp**: GupShup integration supporting both Partner API (multi-tenant, per-customer WABA) and Direct API modes. Template messages, session messages within the 24-hour window, and inbound message handling via webhooks.

### Campaign Automation
Multi-step campaign builder with email and WhatsApp channels. Steps support delay-based scheduling and conditional triggers (no reply, no open, always). Campaign lifecycle: draft, activate, pause, resume, cancel. Per-campaign analytics: delivery rate, open rate, reply rate, bounces, and failures.

### Pipeline and Deals
Kanban-style pipeline with seven default stages (New Lead through Closed Won/Lost). Opportunities track commodity, quantity, target/our/competitor pricing, incoterms, payment terms, container details, shipment dates, sample status, and probability. Auto-generated display IDs (e.g., TRAD-0001). Activity logging on stage changes.

### Shipment Intelligence
Company-level shipment analytics: 12-month totals, monthly volume series, top trade partners, top lanes, top commodities, and catalog match ratios. Raw shipment record browsing with filters by direction, commodity, and catalog match. Extensible integration point for real shipment data APIs.

### AI Agents
- **Research Agent** -- buyer discovery using shipment databases and web research
- **Composer Agent** -- AI-powered message composition
- **Reply Agent** -- inbound message classification and reply suggestions with approve/reject workflow
- **Reply Drafter** -- context-aware draft replies using catalog, pricing, and lead preferences
- **Insights Agent** -- actionable intelligence for companies, contacts, opportunities, and leads (24h cached)
- **Interest Inference Agent** -- discovers product-port buying interests from company data
- **Template Author Agent** -- generates and refines outreach templates
- **Lead Classifier** -- classifies inbound emails as leads vs. non-leads
- **Analytics Agent** -- campaign performance analysis

All agents use a shared task infrastructure with step tracking, progress updates, and credit consumption.

### Trade Interest Mapping
Product-port interest records linking companies/contacts to specific products, varieties, grades, origin/destination ports. Supports manual creation, AI inference from shipment data, and bulk accept/reject of suggestions with confidence scoring.

### Inbound Lead Management
Gmail sync with AI-powered lead classification. Extracts sender info, products mentioned, quantities, pricing, delivery terms, destination, and urgency. Auto-matches to existing contacts and companies. One-click pipeline conversion that creates Company, Contact, and Opportunity records. AI draft replies using catalog context, FOB pricing, and configurable preferences.

### Product Catalog
Hierarchical product management: Product > Variety > Grade. FOB price tracking per grade/port/date. Freight rate management per lane and container type. CFR price calculator (FOB + freight). CSV import/export. Commodity reference data for autocomplete.

### Multi-Tenancy
Every database table includes a `tenant_id` column. Middleware extracts tenant context from Clerk JWT tokens and enforces isolation on every query. Tenant-level settings for WhatsApp, catalog defaults, lead preferences, and billing.

### Credit System
Plan-based usage limits (Free Trial, Starter, Growth, Pro) tracking messages sent and enrichments consumed per billing period. Credit balance API with real-time usage stats. Stripe integration placeholder for checkout and customer portal.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, Radix UI, Framer Motion, Zustand, Recharts |
| Backend | FastAPI, SQLAlchemy 2 (async), Pydantic 2, Alembic |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7, Celery |
| Auth | Clerk (JWT-based multi-tenant) |
| AI / LLM | Gemini (structured output), Perplexity (web search), Google AI |
| Enrichment | Perplexity, Firecrawl, Apollo, Gemini |
| Email | Gmail OAuth, SendGrid |
| WhatsApp | GupShup (Partner API + Direct API) |
| Billing | Stripe (placeholder) |

---

## Architecture

```
                    +-------------------+
                    |   Next.js 16      |
                    |   Frontend        |
                    |   (port 3000)     |
                    +--------+----------+
                             |
                         REST API
                             |
                    +--------+----------+
                    |   FastAPI         |
                    |   Backend         |
                    |   (port 8000)     |
                    +---+-----+----+---+
                        |     |    |
              +---------+  +--+--+ +--------+
              |            |     |          |
        +-----+----+ +----+---+ +---+----+ +----------+
        | Postgres  | | Redis  | | Celery | | External |
        | (data)    | | (cache)| | (tasks)| | APIs     |
        +-----------+ +--------+ +--------+ +----------+
                                               |
                                    +----------+----------+
                                    | Perplexity | Apollo  |
                                    | Firecrawl  | Gemini  |
                                    | GupShup    | Gmail   |
                                    | SendGrid   | Stripe  |
                                    +---------------------+
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/tradecrm.git
cd tradecrm

# 2. Copy environment files
cp app/backend/.env.example app/backend/.env
cp app/frontend/.env.example app/frontend/.env.local

# 3. Start infrastructure (PostgreSQL + Redis)
cd app/backend
docker compose up -d

# 4. Run database migrations
pip install -e ".[dev]"
alembic upgrade head

# 5. Start the backend
uvicorn app.main:app --reload --port 8000

# 6. Start the frontend (in a new terminal)
cd app/frontend
npm install
npm run dev

# 7. Open http://localhost:3000
```

---

## Manual Setup

### Backend

```bash
cd app/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your database URL, Clerk keys, and API keys

# Start PostgreSQL and Redis
docker compose up -d

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd app/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your Clerk publishable key and backend URL

# Start development server
npm run dev
```

---

## Project Structure

```
tradecrm/
  app/
    backend/
      alembic/              # Database migrations
      app/
        agents/             # AI agent implementations
          base.py            # Task runner, step tracking
          research_agent.py  # Buyer discovery
          composer_agent.py  # Message composition
          reply_agent.py     # Reply classification
          reply_drafter.py   # Lead reply drafting
          insights_agent.py  # Entity insights generation
          interest_inference_agent.py
          template_author_agent.py
          lead_classifier.py
          analytics_agent.py
        api/                # FastAPI route handlers
          auth.py            # Authentication and tenant management
          companies.py       # Company CRUD
          contacts.py        # Contact CRUD and CSV import
          campaigns.py       # Campaign builder and execution
          pipeline.py        # Deal pipeline (Kanban)
          enrichment.py      # AI enrichment triggers
          agents.py          # Agent task management
          inbox.py           # Unified conversations
          email.py           # Gmail OAuth and email operations
          whatsapp.py        # WhatsApp onboarding and messaging
          shipments.py       # Shipment intelligence
          interests.py       # Trade interest mapping
          leads.py           # Inbound lead management
          templates.py       # Message template CRUD and AI generation
          catalog.py         # Product catalog, pricing, freight, CFR
          discover.py        # AI buyer discovery
          dashboard.py       # Dashboard stats and activity feed
          billing.py         # Credits, usage, Stripe
          webhooks.py        # GupShup, SendGrid, Stripe webhooks
          admin.py           # Admin operations
          clerk_webhook.py   # Clerk auth webhooks
        integrations/       # External service connectors
          gmail_service.py   # Gmail OAuth + API
          sendgrid_service.py# SendGrid email delivery
          gupshup.py         # GupShup Partner API (multi-tenant)
          gupshup_direct.py  # GupShup Direct API
          tradyon_shipments.py # Shipment data client
        middleware/          # Auth and tenant middleware
        models/             # SQLAlchemy models
        schemas/            # Pydantic request/response schemas
        services/           # Business logic
          enrichment_service.py  # 4-step enrichment pipeline
          campaign_executor.py   # Campaign message sending
          lead_processor.py      # Email sync and classification
          shipment_aggregator.py # Shipment summary computation
          template_variables.py  # Variable detection
        tasks/              # Celery async tasks
        utils/              # Shared utilities
        websocket/          # WebSocket event system
        config.py           # Settings (env vars)
        database.py         # Async DB session
        main.py             # FastAPI app entry point
      docker-compose.yml    # PostgreSQL + Redis
      pyproject.toml        # Python dependencies
    frontend/
      src/
        app/                # Next.js App Router pages
          dashboard/         # Dashboard
          companies/         # Company list and detail
          contacts/          # Contact list, detail, lists
          campaigns/         # Campaign list, detail, builder
          pipeline/          # Kanban pipeline
          inbox/             # Unified inbox
          leads/             # Inbound leads
          discover/          # Buyer discovery
          catalog/           # Product catalog management
          opportunities/     # Opportunity detail
          settings/          # Workspace, team, billing, integrations, templates
          (auth)/            # Login, signup, onboarding
        components/         # React components
          agentic/           # Agent progress UI
          campaign/          # Campaign builder components
          entities/          # Company/contact cards
          inbox/             # Conversation thread UI
          layout/            # Shell, sidebar, nav
          shared/            # Reusable components
          ui/                # Base UI primitives
        hooks/              # Custom React hooks
        lib/                # API client, utilities
        stores/             # Zustand state management
        types/              # TypeScript type definitions
      package.json
  docs/                     # Documentation
```

---

## API Overview

All endpoints require authentication via Clerk JWT (except webhooks and public catalog lookups). Tenant context is extracted from the token automatically.

| Domain | Prefix | Key Endpoints |
|--------|--------|--------------|
| Auth | `/auth` | Login, signup, current user, tenant settings |
| Tenants | `/tenants` | Tenant CRUD, member management, invite |
| Companies | `/companies` | CRUD, search, notes |
| Contacts | `/contacts` | CRUD, CSV import, search |
| Contact Lists | `/contact-lists` | Create, list, add/remove members |
| Enrichment | `/companies/{id}/enrich` | Trigger enrichment, status polling, contact discovery |
| Campaigns | `/campaigns` | CRUD, steps, activate, pause, cancel, analytics |
| Pipeline | `/pipeline` | Stages, opportunities CRUD, move, stats |
| Inbox | `/inbox` | Conversations, thread, reply, AI suggestions |
| Email | `/email` | Gmail OAuth, accounts, send, reply, drafts, labels |
| WhatsApp | `/whatsapp` | Onboarding, templates, send template/session, 24h window |
| Shipments | `/companies/{id}/shipments` | Summary, raw records, partners, commodities, refresh |
| Interests | `/interests` | CRUD, bulk accept/reject, AI inference |
| Leads | `/leads` | List, detail, sync, move-to-pipeline, dismiss, draft-reply, send-reply |
| Templates | `/templates` | CRUD, duplicate, AI generate, refine, variables |
| Catalog | `/catalog` | Products, varieties, grades, FOB prices, freight, CFR calculator, ports |
| Agents | `/agents` | Run task, list tasks, task detail |
| Insights | `/insights` | Get/refresh insights for company, contact, opportunity, lead |
| Discovery | `/discover` | AI buyer search, save company |
| Dashboard | `/dashboard` | Stats, activity feed, pending approvals |
| Billing | `/billing` | Credits, usage, Stripe checkout/portal |
| Webhooks | `/webhooks` | GupShup, SendGrid, Stripe inbound |

---

## Connectors

TradeCRM integrates with the following external services:

| Connector | Purpose |
|-----------|---------|
| **Clerk** | Authentication, JWT tokens, user/org management |
| **Gmail OAuth** | Read inbox, send/reply/draft emails, label management |
| **SendGrid** | Transactional email delivery with warmup scheduling |
| **GupShup** | WhatsApp Business API (Partner + Direct modes) |
| **Perplexity** | AI web search for company research |
| **Firecrawl** | Website mapping and page scraping |
| **Apollo** | Company metadata and contact/people discovery |
| **Gemini** | Structured data extraction, reply drafting, template generation |
| **Stripe** | Subscription billing (placeholder) |
| **Tradyon Shipments** | Trade shipment intelligence data |

See [docs/connectors.md](docs/connectors.md) for setup instructions.

---

## Documentation

- [Architecture](docs/architecture.md) -- system design, data model, enrichment pipeline, auth flow
- [Connectors](docs/connectors.md) -- integration setup and configuration
- [Enrichment Pipeline](docs/enrichment.md) -- how AI enrichment works
- [Deployment](docs/deployment.md) -- production deployment guide
- [Contributing](CONTRIBUTING.md) -- development setup and guidelines
- [Security](SECURITY.md) -- vulnerability disclosure policy
- [Changelog](CHANGELOG.md) -- release history

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

---

## License

Licensed under the [Apache License 2.0](LICENSE).

---

## Built With

- [FastAPI](https://fastapi.tiangolo.com/) -- async Python web framework
- [Next.js](https://nextjs.org/) -- React framework for production
- [PostgreSQL](https://www.postgresql.org/) -- relational database
- [Redis](https://redis.io/) -- caching and task queues
- [Clerk](https://clerk.com/) -- authentication and user management
- [Tailwind CSS](https://tailwindcss.com/) -- utility-first CSS
- [Radix UI](https://www.radix-ui.com/) -- accessible component primitives
- [Framer Motion](https://www.framer.com/motion/) -- animation library
- [SQLAlchemy](https://www.sqlalchemy.org/) -- Python ORM
- [Alembic](https://alembic.sqlalchemy.org/) -- database migrations

---

## Star History

<!-- Star history chart placeholder -->
<!-- Replace with: [![Star History Chart](https://api.star-history.com/svg?repos=your-org/tradecrm&type=Date)](https://star-history.com/#your-org/tradecrm&Date) -->

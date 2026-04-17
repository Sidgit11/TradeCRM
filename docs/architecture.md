# Architecture

## System Overview

TradeCRM is a multi-tenant SaaS application with a clear separation between frontend and backend. The system consists of six primary components:

```
+------------------+     +------------------+     +------------------+
|   Next.js 16     |     |   FastAPI        |     |   PostgreSQL 16  |
|   Frontend       +---->+   Backend        +---->+   Database       |
|   (React 19)     |     |   (async)        |     |   (asyncpg)      |
+------------------+     +--------+---------+     +------------------+
                                  |
                    +-------------+-------------+
                    |             |              |
              +-----+----+ +----+----+  +------+-------+
              |  Redis 7  | |  Celery |  | External APIs|
              |  (cache)  | |  (tasks)|  | (AI, email,  |
              +-----------+ +---------+  |  WhatsApp)   |
                                         +--------------+
```

### Frontend
- **Framework**: Next.js 16 with App Router
- **UI**: React 19, Tailwind CSS 4, Radix UI primitives, Framer Motion
- **State**: Zustand stores, React hooks
- **Auth**: Clerk SDK (`@clerk/nextjs`) handles session management and JWT issuance
- **Charts**: Recharts for analytics dashboards

### Backend
- **Framework**: FastAPI with async request handling
- **ORM**: SQLAlchemy 2 with asyncpg driver
- **Migrations**: Alembic
- **Validation**: Pydantic 2 for request/response schemas
- **Background tasks**: FastAPI BackgroundTasks for enrichment, Celery for scheduled work

### Database
- **Engine**: PostgreSQL 16
- **Driver**: asyncpg (async, non-blocking)
- **Schema management**: Alembic migrations in `app/backend/alembic/versions/`
- **Production**: Neon or Supabase recommended

### Cache and Task Queue
- **Redis**: Session cache, rate limiting, task broker
- **Celery**: Background task execution for campaign scheduling and data sync

### External APIs
Enrichment, messaging, and AI services. See [connectors.md](connectors.md) for details.

---

## Multi-Tenancy Model

TradeCRM implements row-level multi-tenancy. Every business data table includes a `tenant_id` UUID column that references the `tenants` table.

### Enforcement

1. **Clerk JWT**: Each authenticated request includes a JWT issued by Clerk containing the user's `org_id`
2. **Tenant middleware** (`app/middleware/tenant.py`): Extracts the `tenant_id` from the JWT, resolves the Tenant record, and injects it as a FastAPI dependency (`CurrentTenantId`)
3. **Query scoping**: Every database query in every API endpoint includes a `WHERE tenant_id = :tenant_id` clause
4. **No cross-tenant access**: There is no admin override or tenant-switching mechanism in the API layer

### Tenant Data Model

```
Tenant
  - id (UUID, PK)
  - company_name
  - plan (free_trial | starter | growth | pro)
  - commodities (JSONB)
  - whatsapp_status, whatsapp_phone
  - gupshup_app_id, gupshup_app_name, gupshup_app_token
  - stripe_customer_id
  - created_at, updated_at
```

Every tenant has:
- One or more Users (admin or member roles)
- Isolated data for companies, contacts, campaigns, messages, pipeline, leads, catalog, etc.
- Tenant-level configuration for WhatsApp, catalog defaults, and lead preferences

---

## Authentication Flow

```
Browser                   Clerk                    Backend
  |                         |                         |
  |-- Sign in/up ---------->|                         |
  |<-- Session + JWT -------|                         |
  |                         |                         |
  |-- API request (Bearer JWT) ---------------------->|
  |                         |                  Verify JWT signature
  |                         |                  Extract org_id
  |                         |                  Resolve tenant_id
  |                         |                  Inject CurrentTenantId
  |                         |                  Inject CurrentUser
  |<-- Response ----------------------------------------|
```

1. User authenticates via Clerk on the frontend (login, signup, or SSO)
2. Clerk issues a JWT with the user's ID and organization ID
3. Frontend sends the JWT as a Bearer token on every API request
4. Backend middleware verifies the JWT signature against `CLERK_JWT_ISSUER`
5. The `org_id` claim maps to a Tenant record; the user's ID maps to a User record
6. Both are injected as dependencies into route handlers via `CurrentTenantId` and `CurrentUser`

### Clerk Webhook

A webhook endpoint (`/webhooks/clerk`) receives events from Clerk for user creation, organization creation, and membership changes. This keeps the local User and Tenant tables in sync with Clerk's state.

### Dev Mode

Setting `DEV_MODE=true` in the backend `.env` bypasses JWT verification and uses a hardcoded test user/tenant. This is intended for local development only.

---

## Data Model Overview

### Core Entities

| Entity | Table | Key Fields |
|--------|-------|-----------|
| Tenant | `tenants` | company_name, plan, commodities, whatsapp config |
| User | `users` | email, name, role (admin/member), clerk_user_id |
| Company | `companies` | name, country, commodities, enrichment_status, confidence_score, trade fields |
| Contact | `contacts` | name, email, phone, whatsapp_number, company_id, is_decision_maker, source |
| ContactList | `contact_lists` | name, description |
| ContactListMember | `contact_list_members` | contact_list_id, contact_id |

### Campaign and Messaging

| Entity | Table | Key Fields |
|--------|-------|-----------|
| Campaign | `campaigns` | name, type (email/whatsapp/multi), status, contact_list_id |
| CampaignStep | `campaign_steps` | step_number, channel, delay_days, condition, template_content |
| Message | `messages` | contact_id, channel, direction, status, sent/delivered/opened timestamps |
| MessageEvent | `message_events` | message_id, event_type, event_data |
| MessageTemplate | `message_templates` | name, channel, category, subject, body, variables, ai_generated |
| Sequence | `sequences` | campaign_id, contact_id, current_step, next_action_at |

### Pipeline

| Entity | Table | Key Fields |
|--------|-------|-----------|
| PipelineStage | `pipeline_stages` | name, slug, order, color, is_default |
| PipelineOpportunity | `pipeline_opportunities` | display_id, company_id, contact_id, stage_id, commodity, quantity_mt, pricing fields, sample status |

### Shipment Intelligence

| Entity | Table | Key Fields |
|--------|-------|-----------|
| Shipment | `shipments` | company_id, direction, commodity_text, hs_code, ports, volume, pricing, trade_partner |
| CompanyShipmentSummary | `company_shipment_summaries` | totals, monthly_series, top_partners, top_lanes, top_commodities |

### Trade Interests

| Entity | Table | Key Fields |
|--------|-------|-----------|
| ProductPortInterest | `product_port_interests` | company_id, product_id, variety_id, grade_id, ports, role, source, confidence, status |

### Catalog

| Entity | Table | Key Fields |
|--------|-------|-----------|
| Product | `products` | name, origin_country, hs_code, capacities |
| ProductVariety | `product_varieties` | product_id, name |
| ProductGrade | `product_grades` | variety_id, name, specifications, packaging |
| FobPrice | `fob_prices` | grade_id, origin_port_id, price_date, price_usd_per_kg/mt |
| FreightRate | `freight_rates` | origin_port_id, destination_port_id, container_type, rate_usd |
| Port | `ports` | name, code, city, country |

### Leads

| Entity | Table | Key Fields |
|--------|-------|-----------|
| InboundLead | `inbound_leads` | classification, sender info, products_mentioned, quantities, urgency, draft_reply |
| LeadPreferences | `lead_preferences` | reply_tone, include_fob_price, high_value_threshold |

### Activity and Agents

| Entity | Table | Key Fields |
|--------|-------|-----------|
| AgentTask | `agent_tasks` | task_type, status, steps (JSONB), input/output_data, credits_consumed |
| ActivityLog | `activity_logs` | actor_type (user/agent/system), action, entity_type, entity_id, detail |
| CreditTransaction | `credit_transactions` | action_type, credits, balance_after |
| ReplySuggestion | `reply_suggestions` | message_id, classification, suggested_reply_text, confidence, status |

### Relationships

```
Tenant --< User
Tenant --< Company --< Contact
Tenant --< ContactList --< ContactListMember >-- Contact
Company --< Shipment
Company --< CompanyShipmentSummary
Company --< PipelineOpportunity >-- Contact
Company --< ProductPortInterest >-- Product
Tenant --< Campaign --< CampaignStep
Campaign --< Sequence >-- Contact
Contact --< Message --< MessageEvent
Message --< ReplySuggestion
Tenant --< AgentTask
Tenant --< ActivityLog
Product --< ProductVariety --< ProductGrade --< FobPrice
```

---

## Enrichment Pipeline Architecture

The enrichment pipeline is the core intelligence feature. It takes a company name and transforms it into a comprehensive company profile with discovered contacts.

### Flow

```
Trigger (API or UI)
       |
       v
  +---------+     +------------------+     +------------------+
  |  Step 1 |     |  Step 2          |     |  Step 3          |
  |Perplexity+--->+  Firecrawl MAP   +--->+  Gemini Parse     |
  | (web    |     |  + SCRAPE        |     |  (structured     |
  | search) |     |  (parallel with  |     |   extraction)    |
  +---------+     |  Apollo Org)     |     +--------+---------+
                  +------------------+              |
                                                    v
                                           +--------+---------+
                                           |  Step 4          |
                                           |  Apollo People   |
                                           |  (conditional    |
                                           |   A/B/C logic)   |
                                           +--------+---------+
                                                    |
                                                    v
                                           +--------+---------+
                                           |  Step 5          |
                                           |  Merge + Save    |
                                           |  (Company +      |
                                           |   Contacts)      |
                                           +------------------+
```

### Step Details

1. **Perplexity Lookup**: Searches the web for the company. Returns website URL, LinkedIn page, description, industry, country, and year established.

2. **Parallel Firecrawl + Apollo Org**: Runs concurrently.
   - Firecrawl MAPs the website to discover routes, filters for relevant pages (about, contact, team, products), and scrapes up to 6 pages into markdown.
   - Apollo searches for the organization by domain or name, returning metadata (logo, employee count, revenue, phone).

3. **Gemini Parse**: Sends the concatenated markdown to Gemini with structured JSON output. Extracts description, products, target industries, contact info, certifications, social media, and personnel.

4. **Apollo People (Conditional)**:
   - **Scenario A**: Website already provided people with contact details (email/phone). Skip Apollo.
   - **Scenario B**: Website provided names but no contact details. Fuzzy-match against Apollo stubs, bulk-enrich matched + additional people.
   - **Scenario C**: No people from website. Full Apollo discovery for decision makers.

5. **Merge and Save**: Updates the Company record with all enriched fields. Calculates a confidence score (0.0-1.0) based on data completeness. Creates Contact records for each discovered person with deduplication by name within the company.

### Execution Model

- Triggered via `POST /companies/{id}/enrich`
- Runs as a FastAPI BackgroundTask with its own database session
- Progress tracked via an AgentTask record with step-level status updates
- Consumes 1 enrichment credit per run
- Plan-based monthly limits enforced before execution

See [enrichment.md](enrichment.md) for the complete reference.

---

## AI Agent Architecture

### Agent Types

| Agent | Task Type | Purpose |
|-------|-----------|---------|
| Research Agent | `buyer_discovery` | Find potential buyers via shipment data and web research |
| Enrichment Service | `company_research` | Full company profiling (4-step pipeline) |
| Contact Enrichment | `contact_enrichment` | Verify and enrich individual contacts |
| Composer Agent | `message_compose` | Generate outreach messages |
| Reply Agent | `reply_suggest` | Classify inbound messages and suggest replies |
| Analytics Agent | `campaign_analytics` | Analyze campaign performance |

### Task Lifecycle

```
Created (pending)
     |
     v
Running -----> Failed
     |
     v
Completed
```

1. **Created**: API endpoint creates an `AgentTask` record with `pending` status and defined steps
2. **Running**: Task executor picks up the task, updates status to `running`, and processes each step
3. **Step tracking**: Each step has its own status (pending, running, completed, failed, skipped) with timestamps and detail messages
4. **Completed/Failed**: Final status set with output_data or error, credits consumed, and completion timestamp

### Infrastructure

- `AgentStepTracker` (base.py): Tracks progress through named steps with callbacks for WebSocket emission
- `AgentTask` model: Persistent task record with JSONB `steps` array, `input_data`, `output_data`
- `ActivityLog`: Records agent actions for the activity feed
- `CreditTransaction`: Tracks credit consumption per task

### Step Update Pattern

```python
# Start step
await tracker.start_step("Searching the web...")

# Do work
result = await some_api_call()

# Complete step
await tracker.complete_step(f"Found {len(result)} results")
```

---

## Real-Time Updates

### WebSocket

The backend includes a WebSocket module (`app/websocket/`) for pushing real-time updates to the frontend:
- Agent task progress (step completions, narrative updates)
- New inbound messages
- Campaign execution results

### Polling Fallback

For environments where WebSocket is not available, the frontend can poll:
- `GET /agents/tasks/{task_id}` for agent progress
- `GET /companies/{id}/enrich/status` for enrichment status

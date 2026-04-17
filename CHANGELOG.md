# Changelog

All notable changes to TradeCRM are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.1.0] - 2026-04-17

Initial release of TradeCRM.

### Added

**Company Management**
- Full CRUD for companies with trade-specific fields (commodities, incoterms, payment terms, ports, certifications)
- Search and filtering by name, country, commodity, and enrichment status
- Soft-delete with restoration support
- Company notes

**Contact Management**
- Full CRUD for contacts linked to companies
- CSV import with automatic deduplication by email and phone
- Contact lists with member management
- Decision-maker flagging and opt-in tracking (email, WhatsApp)
- Custom fields and tagging

**AI-Powered Enrichment**
- Four-step enrichment pipeline: Perplexity web search, Firecrawl site scraping, Gemini structured parsing, Apollo contact discovery
- Three conditional Apollo people scenarios (A/B/C)
- Confidence scoring (0.0-1.0) based on data completeness
- Automatic Contact record creation for discovered personnel
- Plan-based monthly enrichment limits with credit tracking
- Background execution with step-by-step progress tracking

**Multi-Channel Outreach**
- Gmail OAuth integration: inbox reading, send, reply, drafts, labels, archive
- SendGrid email delivery with warmup scheduling
- GupShup WhatsApp integration (Partner API and Direct API modes)
- WhatsApp onboarding flow with embedded signup
- Template messages and session messages with 24-hour window enforcement
- Inbound message handling via webhooks

**Campaign Automation**
- Multi-step campaign builder with email and WhatsApp channels
- Step conditions: no reply, no open, always
- Campaign lifecycle: draft, active, paused, completed, cancelled
- Campaign activation with immediate step-1 execution
- Per-campaign analytics: delivery, open, reply rates, bounces, failures

**Pipeline and Deals**
- Kanban pipeline with seven default stages
- Opportunity CRUD with trade-specific fields (commodity, quantity, pricing, containers, samples)
- Stage movement with activity logging
- Auto-generated display IDs per tenant
- Pipeline statistics endpoint

**Shipment Intelligence**
- Company-level shipment summaries with 12-month totals and monthly series
- Top trade partners, lanes, and commodities aggregation
- Raw shipment record browsing with filters
- Catalog match ratio tracking
- Force-refresh capability

**AI Agents**
- Research agent for buyer discovery
- Composer agent for message generation
- Reply agent for inbound message classification and reply suggestions
- Reply drafter with catalog and pricing context
- Insights agent for entity-level actionable intelligence (24h cache)
- Interest inference agent for product-port discovery
- Template author agent for AI generation and refinement
- Lead classifier for email triage
- Analytics agent for campaign analysis
- Shared agent infrastructure: task runner, step tracking, activity logging

**Trade Interest Mapping**
- Product-port interest CRUD
- AI inference from company data
- Bulk accept/reject of suggestions
- Confidence scoring and evidence tracking

**Inbound Lead Management**
- Gmail sync with AI-powered lead classification
- Structured extraction: sender, products, quantities, pricing, delivery terms, urgency
- Auto-matching to existing contacts and companies
- One-click pipeline conversion (creates Company, Contact, Opportunity)
- AI draft replies with catalog, pricing, and preference context
- Send reply via connected Gmail account
- Configurable lead preferences (reply tone, pricing inclusion, thresholds)

**Product Catalog**
- Hierarchical product management (Product > Variety > Grade)
- FOB price tracking per grade, port, and date
- Bulk FOB price creation
- Freight rate management per lane and container type
- CFR price calculator (FOB + freight per MT)
- CSV template download and bulk import
- Commodity reference data for autocomplete
- Tenant defaults for origin port, currency, container type, payment terms

**Message Templates**
- CRUD for email and WhatsApp templates
- Auto-detection of template variables
- Variable registry for frontend
- AI template generation and refinement
- Template duplication
- Category support: introduction, price update, follow-up, sample offer, and more

**Unified Inbox**
- Conversations grouped by contact with last message preview
- Multi-channel thread view (email + WhatsApp, chronological)
- Reply composition
- AI reply suggestions with approve/reject workflow
- Unread count tracking
- Conversation classification

**Dashboard**
- Daily stats: messages sent, replies received, pending approvals, follow-ups due
- Activity feed (user and agent actions)
- Pending approval queue

**Multi-Tenancy**
- Row-level tenant isolation on every table
- Clerk JWT-based tenant resolution
- Tenant middleware enforcement on all queries
- Dev mode for local development without auth

**Billing and Credits**
- Plan-based limits: Free Trial, Starter ($199/mo), Growth ($499/mo), Pro ($999/mo)
- Monthly usage tracking for messages and enrichments
- Credit balance API
- Stripe integration placeholder (checkout, portal, webhooks)

**Infrastructure**
- FastAPI backend with async SQLAlchemy and asyncpg
- Next.js 16 frontend with React 19 and Tailwind CSS 4
- Alembic database migrations
- Docker Compose for local PostgreSQL and Redis
- Structured logging with tenant context
- WebSocket support for real-time updates
- Clerk webhook sync for users and organizations

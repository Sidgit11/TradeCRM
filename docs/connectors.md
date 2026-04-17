# Connectors

TradeCRM integrates with external services for authentication, messaging, enrichment, and billing. Each connector is implemented as a standalone module in `app/backend/app/integrations/` or accessed via standard SDK.

---

## Clerk (Authentication)

**What it does**: Provides user authentication, organization (tenant) management, and JWT issuance. The backend verifies Clerk JWTs to extract user and tenant context.

**Required env vars**:
```
CLERK_SECRET_KEY=sk_test_xxx
CLERK_PUBLISHABLE_KEY=pk_test_xxx
CLERK_JWT_ISSUER=https://your-app.clerk.accounts.dev
```

**Setup**:
1. Create a Clerk application at https://dashboard.clerk.com
2. Enable Organizations in Clerk dashboard
3. Copy the Secret Key, Publishable Key, and JWT Issuer URL
4. Configure the webhook endpoint in Clerk: `https://your-domain.com/webhooks/clerk`

**API endpoints powered**:
- All authenticated endpoints (JWT verification via middleware)
- `POST /webhooks/clerk` -- user/org sync events

---

## Email Providers (Pluggable)

**What it does**: Sends campaign and transactional emails through your preferred provider. TradeCRM supports multiple email providers out of the box -- set one env var to switch.

**Implementation**: `app/integrations/email_provider.py`

**Supported providers**:

| Provider | `EMAIL_PROVIDER` | Required env var | Best for |
|----------|-----------------|------------------|----------|
| SendGrid | `sendgrid` | `SENDGRID_API_KEY` | High-volume transactional email |
| Resend | `resend` | `RESEND_API_KEY` | Fast setup, modern API |
| Amazon SES | `ses` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Cost efficiency at scale |
| Any SMTP | `smtp` | `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | Gmail, Outlook, Zoho, Mailgun, etc. |
| Log (dev) | `log` | (none) | Local development -- prints to console |

**Setup** (example with Resend -- takes under 2 minutes):
1. Sign up at https://resend.com and get an API key
2. Add to your `.env`:
   ```
   EMAIL_PROVIDER=resend
   RESEND_API_KEY=re_xxx
   ```
3. Restart the backend. Campaign emails now send via Resend.

**Adding a custom provider**:
1. Create a class in `email_provider.py` that extends `EmailProvider`
2. Implement `name`, `is_configured`, and `send()`
3. Register it in `PROVIDER_REGISTRY` at the bottom of the file

**API endpoints powered**:
- Campaign email delivery (via campaign executor)
- `POST /webhooks/sendgrid` -- delivery status webhooks (SendGrid-specific)

---

## Gmail OAuth (Email Integration)

**What it does**: Connects user Gmail accounts for reading inbox, sending/replying to emails, managing drafts, and label operations. Supports multiple connected accounts per tenant.

**Implementation**: `app/integrations/gmail_service.py`

**Required env vars**:
```
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=http://localhost:8000/email/callback/gmail
```

**Setup**:
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Web Application type)
4. Add authorized redirect URI: `https://your-domain.com/email/callback/gmail`
5. Request the following scopes: `gmail.readonly`, `gmail.compose`, `gmail.send`, `gmail.modify`, `gmail.labels`

**API endpoints powered**:
- `GET /email/connect/gmail` -- start OAuth flow
- `GET /email/callback/gmail` -- handle OAuth callback
- `GET /email/accounts` -- list connected accounts
- `GET /email/accounts/{id}/messages` -- read inbox
- `POST /email/accounts/{id}/send` -- send email
- `POST /email/accounts/{id}/reply` -- reply to email
- `POST /email/accounts/{id}/drafts` -- create draft
- `GET /email/accounts/{id}/labels` -- list labels
- `POST /leads/{id}/send-reply` -- reply to inbound leads

---

## GupShup (WhatsApp Business API)

**What it does**: Enables WhatsApp messaging via two modes:

- **Partner API**: Multi-tenant mode where each customer gets their own WhatsApp Business Account (WABA) with their own phone number. Supports embedded signup.
- **Direct API**: Single-WABA mode using your own number. Simpler setup, suitable for smaller deployments.

**Implementation**: `app/integrations/gupshup.py` (Partner), `app/integrations/gupshup_direct.py` (Direct)

**Required env vars (Partner API)**:
```
GUPSHUP_PARTNER_EMAIL=partner@company.com
GUPSHUP_PARTNER_SECRET=xxx
```

**Required env vars (Direct API)**:
```
GUPSHUP_HSM_USERID=xxx
GUPSHUP_HSM_PASSWORD=xxx
GUPSHUP_TWOWAY_USERID=xxx
GUPSHUP_TWOWAY_PASSWORD=xxx
GUPSHUP_WABA_NUMBER=919876543210
GUPSHUP_API_KEY=xxx
GUPSHUP_APP_ID=xxx
```

**Webhook**:
```
GUPSHUP_WEBHOOK_URL=https://your-domain.com/webhooks/gupshup
GUPSHUP_WEBHOOK_SECRET=xxx
```

**Setup**:
1. Create a GupShup account at https://www.gupshup.io
2. For Partner API: Apply for partner access, obtain partner credentials
3. For Direct API: Create a WhatsApp app, get the WABA number and API credentials
4. Configure the webhook URL in GupShup dashboard
5. Create and get approval for WhatsApp message templates in GupShup

**API endpoints powered**:
- `POST /whatsapp/onboarding/start` -- connect WhatsApp
- `POST /whatsapp/onboarding/complete` -- finalize setup
- `GET /whatsapp/status` -- connection status
- `GET /whatsapp/templates` -- list approved templates
- `POST /whatsapp/send/template` -- send template message
- `POST /whatsapp/send/session` -- send session message (24h window)
- `GET /whatsapp/window/{contact_id}` -- check 24h window status
- `POST /webhooks/gupshup` -- inbound messages and delivery status

---

## Perplexity (AI Web Search)

**What it does**: Searches the web for company information during enrichment. Returns structured data about a company's website, LinkedIn, description, industry, country, and founding year.

**Required env vars**:
```
PERPLEXITY_API_KEY=pplx-xxx
```

**Setup**:
1. Create an account at https://perplexity.ai
2. Generate an API key
3. Uses the `sonar` model via the chat completions API

**API endpoints powered**:
- `POST /companies/{id}/enrich` -- step 1 of enrichment pipeline

---

## Firecrawl (Web Scraping)

**What it does**: Maps website URLs to discover pages, then scrapes relevant pages (about, contact, team, products) into clean markdown for AI analysis.

**Required env vars**:
```
FIRECRAWL_API_KEY=fc-xxx
```

**Setup**:
1. Create an account at https://firecrawl.dev
2. Generate an API key
3. Uses the v2 Map and Scrape endpoints

**API endpoints powered**:
- `POST /companies/{id}/enrich` -- step 2 of enrichment pipeline (parallel with Apollo Org)

---

## Apollo (Contact Intelligence)

**What it does**: Provides company metadata and contact/people discovery. Used in two phases of enrichment:
1. Organization search for company details (employee count, revenue, logo, LinkedIn)
2. People search and bulk enrichment for decision makers with verified emails

**Required env vars**:
```
APOLLO_API_KEY=xxx
```

**Setup**:
1. Create an account at https://apollo.io
2. Generate an API key
3. Uses Mixed Companies Search, Mixed People Search, and Bulk Match endpoints

**API endpoints powered**:
- `POST /companies/{id}/enrich` -- steps 2 and 4 of enrichment pipeline

---

## Gemini (AI Structured Extraction)

**What it does**: Parses scraped website markdown into structured company data using Google's Gemini model with JSON output mode. Also powers reply drafting, template generation, lead classification, and insights.

**Required env vars**:
```
GEMINI_API_KEY=xxx
```

**Setup**:
1. Create a Google AI Studio project at https://ai.google.dev
2. Generate an API key
3. Uses the `gemini-2.5-flash` model via the REST generateContent endpoint

**API endpoints powered**:
- `POST /companies/{id}/enrich` -- step 3 of enrichment pipeline
- `POST /leads/{id}/draft-reply` -- AI reply drafting
- `POST /templates/generate` -- AI template generation
- `POST /templates/refine` -- template refinement
- `GET /insights/{type}/{id}` -- entity insights generation

---

## Stripe (Billing) -- Placeholder

**What it does**: Manages subscription billing, plan upgrades, and payment processing. Currently implemented as a placeholder with hardcoded plan limits.

**Required env vars**:
```
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_STARTER_PRICE_ID=price_xxx
STRIPE_GROWTH_PRICE_ID=price_xxx
STRIPE_PRO_PRICE_ID=price_xxx
```

**Setup**:
1. Create a Stripe account at https://stripe.com
2. Create subscription products for Starter ($199/mo), Growth ($499/mo), and Pro ($999/mo)
3. Configure the webhook endpoint: `https://your-domain.com/webhooks/stripe`

**API endpoints powered**:
- `POST /billing/create-checkout` -- Stripe Checkout session
- `POST /billing/create-portal` -- customer portal session
- `POST /webhooks/stripe` -- subscription events

---

## Shipment Data API

**What it does**: Provides trade shipment intelligence data (import/export records, volumes, pricing, trade partners). Currently uses local database data with a stub client designed to be swapped for any shipment data provider (Panjiva, ImportGenius, Volza, etc.).

**Implementation**: `app/integrations/tradyon_shipments.py`

**Required env vars** (for future real API):
```
SHIPMENTS_API_URL=https://api.your-provider.com/v1/shipments
SHIPMENTS_API_KEY=xxx
```

**Setup**:
The current implementation uses locally seeded shipment data. When a real shipment data API is available, update the `ShipmentClient` class methods without changing any calling code.

**API endpoints powered**:
- `GET /companies/{id}/shipments/summary` -- aggregated shipment analytics
- `GET /companies/{id}/shipments` -- raw shipment records
- `GET /companies/{id}/shipments/partners` -- trade partner breakdown
- `GET /companies/{id}/shipments/commodities` -- commodity breakdown
- `POST /companies/{id}/shipments/refresh` -- force recompute summary

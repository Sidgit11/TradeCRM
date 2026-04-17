# Enrichment Pipeline

The enrichment pipeline is TradeCRM's core intelligence feature. Given a company name and optional metadata (country, website), it produces a comprehensive company profile and discovers decision-maker contacts -- fully automated.

**Implementation**: `app/backend/app/services/enrichment_service.py`

---

## Overview

The pipeline runs five steps in sequence (with step 2 running two tasks in parallel):

```
Step 1: Perplexity web search
Step 2: Firecrawl site scrape + Apollo org search (parallel)
Step 3: Gemini structured parsing
Step 4: Apollo people discovery (conditional)
Step 5: Merge and save to database
```

Total time: typically 15-45 seconds depending on website size and API response times.

---

## Step-by-Step Flow

### Step 1: Perplexity Web Search

**Input**: Company name, country

**What it does**: Sends a structured prompt to Perplexity's `sonar` model asking for:
- Website URL
- LinkedIn company page URL
- 1-2 sentence description
- Industry category
- Country (HQ location)
- Year established

**Output**: JSON object with the above fields (null for any field not found with confidence).

**Why this step matters**: Establishes the website URL needed for Firecrawl and a domain for Apollo. Without a website, later steps still work but produce less data.

---

### Step 2: Firecrawl + Apollo Org (Parallel)

These two tasks run concurrently to save time.

#### 2a: Firecrawl Site Scrape

**Input**: Website URL from step 1

**What it does**:
1. **MAP**: Calls Firecrawl's Map endpoint to discover all routes on the website
2. **Filter**: Selects up to 6 relevant pages based on URL path keywords: `about`, `contact`, `team`, `people`, `leadership`, `company`, `products`, `services`
3. **SCRAPE**: Scrapes each page in parallel, extracting main content as clean markdown

**Output**: Concatenated markdown from all scraped pages (up to ~50,000 characters passed to Gemini).

#### 2b: Apollo Organization Search

**Input**: Domain extracted from website URL, or company name as fallback

**What it does**: Searches Apollo's Mixed Companies endpoint for the organization.

**Output**: Organization metadata including:
- Apollo org ID (used in step 4)
- LinkedIn URL, logo URL
- Industry, employee count, founding year
- City, country, primary phone
- Annual revenue, website URL

---

### Step 3: Gemini Structured Parsing

**Input**: Concatenated markdown from Firecrawl

**What it does**: Sends the website content to Gemini (`gemini-2.5-flash`) with `responseMimeType: application/json` for structured output. The prompt instructs extraction of:

| Field | Description |
|-------|-----------|
| description | 1-2 sentence company summary |
| products | List of products/services offered |
| target_industries | Customer industry categories |
| company_email | General contact email |
| company_phone | Contact phone number |
| address | Physical address |
| certifications | Quality/trade certs (ISO, BRC, HACCP, Kosher, etc.) |
| year_established | Founding year |
| social_media | Twitter, Facebook, Instagram, YouTube URLs |
| people | Key personnel with name, designation, email, phone, LinkedIn |

**Output**: `CompanyParsedData` Pydantic model with all fields above.

---

### Step 4: Apollo People Discovery (Conditional)

This step implements three scenarios based on what the website provided:

#### Scenario A: Website provided people WITH contact details

**Condition**: Website gave names AND at least one person has an email or phone number.

**Action**: Skip Apollo entirely. Mark each person's `is_decision_maker` flag based on title matching.

**Rationale**: No need to spend Apollo credits when the website already provides quality contact data.

#### Scenario B: Website provided names but NO contact details

**Condition**: Website gave names but none have email or phone.

**Action**:
1. Search Apollo for people at the organization
2. Fuzzy-match Apollo stubs against website names (75% threshold using `SequenceMatcher`)
3. Collect Apollo IDs for matched people (to enrich with contact details) plus unmatched people (additional contacts)
4. Bulk-enrich all collected IDs via Apollo Bulk Match
5. Merge enriched data back into website people (fill in email, phone, LinkedIn)
6. Add any unmatched Apollo people as new contacts

**Rationale**: Website personnel pages often list names and titles but not emails. Apollo fills in the contact details.

#### Scenario C: No people from website

**Condition**: Gemini found zero people on the website.

**Action**:
1. Search Apollo for decision makers at the organization (filtered by title keywords)
2. Filter to people with verified emails
3. Bulk-enrich via Apollo Bulk Match
4. Return normalized contact list

**Decision maker title keywords**:
```
founder, co-founder, ceo, cto, coo, cfo, director, head of, owner,
president, managing director, vp, vice president, general manager,
partner, head of sales, sales director, sales manager,
head of procurement, procurement director, procurement manager,
purchasing director, purchasing manager, commodity manager,
trade manager, trading director, business development,
commercial director, commercial manager
```

---

### Step 5: Merge and Save

**What it does**:
1. Updates the Company record with all enriched fields (description, website, LinkedIn, industry, year, phone, email, address, social media, certifications, commodities/products, employee count, logo)
2. Calculates a confidence score
3. Stores full enrichment metadata in `enrichment_data` JSONB
4. Sets `enrichment_status` to `enriched`, `partially_enriched`, or keeps as-is
5. Creates or updates Contact records for each discovered person (deduplicated by name within company)
6. Finalizes the AgentTask record with completion status and output summary

---

## Confidence Score

The confidence score (0.0-1.0) measures data completeness after enrichment:

| Field | Weight |
|-------|--------|
| website | 0.15 |
| description | 0.15 |
| people (at least 1) | 0.15 |
| linkedin | 0.10 |
| industry | 0.10 |
| company_email | 0.10 |
| company_phone | 0.05 |
| address | 0.05 |
| year_established | 0.05 |
| logo_url | 0.05 |
| number_of_employees | 0.05 |

A score of 1.0 means all fields were successfully populated.

---

## Credit Consumption

Each enrichment run consumes **1 enrichment credit** from the tenant's monthly allowance:

| Plan | Monthly Enrichment Limit |
|------|------------------------|
| Free Trial | 10 |
| Starter | 100 |
| Growth | 500 |
| Pro | Unlimited |

The credit check happens before the pipeline starts. If the limit is reached, the API returns `402 Payment Required`.

---

## How to Trigger

### Via API

```
POST /companies/{company_id}/enrich
Authorization: Bearer <clerk-jwt>
```

Returns immediately with:
```json
{
  "agent_task_id": "uuid",
  "company_id": "uuid",
  "status": "enriching",
  "steps": [...],
  "enrichments_remaining": 9
}
```

### Via UI

Click the "Enrich" button on any company detail page. The UI shows a step-by-step progress indicator that polls `GET /companies/{id}/enrich/status`.

### Polling for Progress

```
GET /companies/{company_id}/enrich/status
Authorization: Bearer <clerk-jwt>
```

Returns the current enrichment status, agent task details, step progress, and any errors.

---

## Enrichment Status Values

| Status | Meaning |
|--------|---------|
| `not_enriched` | Company has never been enriched |
| `enriching` | Pipeline is currently running |
| `partially_enriched` | Pipeline completed but some data is missing |
| `enriched` | Pipeline completed with essential data populated |

A company is marked `enriched` when it has essential data (website, description, or industry) AND at least one discovered contact. It is marked `partially_enriched` when it has some but not all of these.

---

## Error Handling

- **Missing API keys**: Returns `503 Service Unavailable` before starting
- **Already enriching**: Returns `409 Conflict` to prevent duplicate runs
- **API rate limits**: Automatic retry with exponential backoff (10s, 20s) on HTTP 429
- **Pipeline failure**: AgentTask marked as `failed` with error message; company status reverted to `not_enriched`
- **Partial data**: Pipeline continues even if individual steps return empty results; the merge step uses whatever data is available

---

## Data Fields Populated

After a successful enrichment, the following Company fields may be updated:

| Field | Source |
|-------|--------|
| description | Perplexity, Gemini |
| website | Perplexity |
| linkedin_url | Perplexity, Apollo Org |
| industry | Perplexity, Apollo Org |
| year_established | Perplexity, Apollo Org, Gemini |
| logo_url | Apollo Org |
| phone | Apollo Org, Gemini |
| email | Gemini |
| address | Gemini |
| social_media | Gemini |
| commodities (products) | Gemini |
| target_industries | Gemini |
| certifications_required | Gemini |
| number_of_employees | Apollo Org |
| confidence_score | Calculated |
| enrichment_data | All sources (metadata) |

Contact records created include: name, email, phone, LinkedIn URL, title/designation, is_decision_maker flag, country, city, and enrichment source.

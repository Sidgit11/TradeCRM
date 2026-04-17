"""
Company Enrichment Service
---------------------------
Async adaptation of the enrichment-poc pipeline.

Pipeline per company:
  1. Perplexity  -> website, linkedin, description, industry, country, year_established
  2. IN PARALLEL:
     - Firecrawl MAP -> discover routes -> parallel SCRAPE relevant pages -> markdown
     - Apollo ORG search -> company metadata
  3. Gemini      -> parse markdown into structured company data
  4. Apollo PEOPLE (conditional):
     - Scenario A: website gave people WITH contacts -> skip Apollo
     - Scenario B: website gave names but NO contacts -> enrich known + find additional
     - Scenario C: no people from website -> full Apollo discovery
  5. Merge all sources -> update Company + create Contacts
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.logging_config import get_logger
from app.models.activity import AgentTask
from app.models.company import Company
from app.models.contact import Contact
from app.models.enums import (
    AgentTaskStatus,
    ContactEnrichmentStatus,
    ContactSource,
    EnrichmentStatus,
)

logger = get_logger("services.enrichment")

# ---------------------------------------------------------------------------
# Pydantic models for Gemini structured output
# ---------------------------------------------------------------------------

class PersonData(BaseModel):
    name: Optional[str] = None
    designation: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    linkedin_url: Optional[str] = None


class SocialMediaData(BaseModel):
    twitter: Optional[str] = None
    facebook: Optional[str] = None
    instagram: Optional[str] = None
    youtube: Optional[str] = None


class CompanyParsedData(BaseModel):
    description: Optional[str] = None
    products: Optional[list[str]] = None
    target_industries: Optional[list[str]] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    address: Optional[str] = None
    certifications: Optional[list[str]] = None
    year_established: Optional[int] = None
    social_media: Optional[SocialMediaData] = None
    people: Optional[list[PersonData]] = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RELEVANT_PATH_KEYWORDS = [
    "about", "contact", "team", "people", "leadership",
    "who-we-are", "our-team", "staff", "management",
    "company", "products", "services",
]

DECISION_MAKER_TITLES = [
    "founder", "co-founder", "ceo", "cto", "coo", "cfo",
    "director", "head of", "owner", "president", "managing director",
    "vp", "vice president", "general manager", "partner",
    "head of sales", "sales director", "sales manager",
    "head of procurement", "procurement director", "procurement manager",
    "purchasing director", "purchasing manager",
    "commodity manager", "trade manager", "trading director",
    "business development", "commercial director", "commercial manager",
]

HTTP_TIMEOUT = 60.0
GEMINI_MODEL = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _domain_from_url(url: str) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    return urlparse(url).netloc.replace("www.", "")


def _fuzzy_match(name1: str, name2: str, threshold: float = 0.75) -> bool:
    if not name1 or not name2:
        return False
    return SequenceMatcher(None, name1.lower().strip(), name2.lower().strip()).ratio() >= threshold


def _is_decision_maker(title: str) -> bool:
    title_lower = (title or "").lower()
    return any(t in title_lower for t in DECISION_MAKER_TITLES)


def _normalise_apollo_person(person: dict, domain: str = "") -> dict:
    email = person.get("email") or ""
    email_status = person.get("email_status") or ""
    phones = person.get("phone_numbers") or []
    phone = phones[0].get("sanitized_number") if phones else ""
    title = person.get("title") or ""
    return {
        "source": "apollo",
        "apollo_id": person.get("id") or "",
        "name": person.get("name") or "",
        "designation": title,
        "email": email,
        "email_verified": email_status == "verified",
        "mobile": phone,
        "linkedin_url": person.get("linkedin_url") or "",
        "company_domain": (person.get("organization") or {}).get("primary_domain") or domain,
        "city": person.get("city") or "",
        "country": person.get("country") or "",
        "is_decision_maker": _is_decision_maker(title),
    }


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    payload: dict,
    retries: int = 2,
) -> dict:
    """Async HTTP POST with retry on 429."""
    for attempt in range(retries + 1):
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code == 429 and attempt < retries:
                wait = 10 * (attempt + 1)
                logger.warning("Rate-limited on %s, waiting %ds", url, wait)
                await asyncio.sleep(wait)
                continue
            try:
                err_body = exc.response.json()
            except Exception:
                err_body = {"raw": exc.response.text}
            logger.error("POST %s failed %s: %s", url, code, err_body)
            return {}
        except Exception as exc:
            logger.error("POST %s error: %s", url, exc)
            return {}
    return {}


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

async def _update_step(
    db: AsyncSession,
    task: AgentTask,
    step_index: int,
    status: str,
    detail: Optional[str] = None,
) -> None:
    """Update a step's status in the AgentTask.steps JSON array."""
    steps = list(task.steps)  # make a mutable copy
    now = datetime.now(timezone.utc).isoformat()

    if step_index < len(steps):
        steps[step_index]["status"] = status
        if detail:
            steps[step_index]["detail"] = detail
        if status == "running" and not steps[step_index].get("started_at"):
            steps[step_index]["started_at"] = now
        if status in ("completed", "failed", "skipped"):
            steps[step_index]["completed_at"] = now

    task.steps = steps
    task.current_step_index = step_index
    if status == "running":
        task.status = AgentTaskStatus.running
    await db.commit()


# ---------------------------------------------------------------------------
# Step 1: Perplexity lookup
# ---------------------------------------------------------------------------

async def _perplexity_lookup(
    client: httpx.AsyncClient,
    company_name: str,
    country: str,
) -> dict:
    prompt = (
        f'Find information about the company "{company_name}" based in {country}.\n'
        "Return a JSON object with these keys:\n"
        '- "website": official website URL (null if not found)\n'
        '- "linkedin": LinkedIn company page URL (null if not found)\n'
        '- "description": 1-2 sentence description of what the company does (null if unknown)\n'
        '- "industry": primary industry category (null if unknown)\n'
        '- "country": country where the company HQ is located (null if unknown)\n'
        '- "year_established": year the company was founded as an integer (null if unknown)\n'
        "\nReturn ONLY the JSON object. No markdown formatting, no extra text. "
        "Use null for any field you cannot determine with confidence."
    )
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    data = await _post_json(client, "https://api.perplexity.ai/chat/completions", headers, payload)
    try:
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as exc:
        logger.warning("Perplexity parse error: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Step 2a: Firecrawl pipeline
# ---------------------------------------------------------------------------

async def _firecrawl_map(client: httpx.AsyncClient, website_url: str) -> list[str]:
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": website_url,
        "search": "about contact team leadership products services",
        "limit": 50,
    }
    data = await _post_json(client, "https://api.firecrawl.dev/v2/map", headers, payload)
    links = data.get("links") or []
    return [
        (l.get("url") if isinstance(l, dict) else l)
        for l in links if l
    ]


def _filter_relevant_urls(urls: list[str], website_url: str) -> list[str]:
    base_domain = urlparse(website_url).netloc.replace("www.", "")
    relevant = set()
    relevant.add(website_url.rstrip("/"))

    for url in urls:
        if not url:
            continue
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        if domain != base_domain:
            continue
        path = parsed.path.lower().strip("/")
        if not path:
            relevant.add(url)
            continue
        if any(kw in path for kw in RELEVANT_PATH_KEYWORDS):
            relevant.add(url)

    return list(relevant)[:6]


async def _firecrawl_scrape_page(client: httpx.AsyncClient, url: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }
    data = await _post_json(client, "https://api.firecrawl.dev/v2/scrape", headers, payload)
    md = (data.get("data") or {}).get("markdown") or ""
    return f"<!-- PAGE: {url} -->\n{md}" if md else ""


async def _firecrawl_pipeline(client: httpx.AsyncClient, website_url: str) -> str:
    if not website_url:
        return ""

    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    logger.info("Firecrawl: mapping site %s", website_url)
    all_urls = await _firecrawl_map(client, website_url)
    relevant = _filter_relevant_urls(all_urls, website_url)

    if not relevant:
        relevant = [website_url]

    logger.info("Firecrawl: scraping %d pages", len(relevant))
    tasks = [_firecrawl_scrape_page(client, url) for url in relevant]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    pages = []
    for r in results:
        if isinstance(r, str) and r:
            pages.append(r)
        elif isinstance(r, Exception):
            logger.warning("Firecrawl scrape error: %s", r)

    return "\n\n---\n\n".join(pages)


# ---------------------------------------------------------------------------
# Step 2b: Apollo org search
# ---------------------------------------------------------------------------

async def _apollo_search_org(
    client: httpx.AsyncClient,
    domain: str,
    company_name: str,
) -> dict:
    headers = {
        "x-api-key": settings.APOLLO_API_KEY,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload: dict[str, Any] = {"per_page": 1, "page": 1}
    if domain:
        payload["q_organization_domains_list"] = [domain]
    elif company_name:
        payload["q_organization_name"] = company_name
    else:
        return {}

    data = await _post_json(
        client, "https://api.apollo.io/api/v1/mixed_companies/search", headers, payload,
    )
    orgs = data.get("organizations") or []
    if not orgs:
        return {}

    org = orgs[0]
    phone_obj = org.get("primary_phone") or {}
    return {
        "org_id": org.get("id"),
        "name": org.get("name"),
        "linkedin_url": org.get("linkedin_url"),
        "logo_url": org.get("logo_url"),
        "industry": org.get("industry"),
        "estimated_num_employees": org.get("estimated_num_employees"),
        "founded_year": org.get("founded_year"),
        "city": org.get("city"),
        "country": org.get("country"),
        "primary_phone": phone_obj.get("number") if isinstance(phone_obj, dict) else None,
        "website_url": org.get("website_url"),
        "annual_revenue": org.get("annual_revenue"),
    }


# ---------------------------------------------------------------------------
# Step 3: Gemini parse
# ---------------------------------------------------------------------------

async def _gemini_parse_company(client: httpx.AsyncClient, markdown: str) -> CompanyParsedData:
    if not markdown.strip():
        return CompanyParsedData()

    prompt = (
        "You are a data extraction assistant. From the website content below, extract:\n"
        "- description: 1-2 sentence summary of what the company does\n"
        "- products: list of products or services offered\n"
        "- target_industries: industries their customers/buyers belong to "
        '(e.g. "Food & Beverage", "Retail", "Industrial/Grinding", "Foodservice")\n'
        "- company_email: general contact/info email address\n"
        "- company_phone: general contact phone number\n"
        "- address: full physical address if available\n"
        "- certifications: quality/trade certifications "
        "(e.g. ISO, BRC, FSSC, Organic, Fair Trade, HACCP, Kosher, Halal)\n"
        "- year_established: year founded (integer)\n"
        "- social_media: object with keys: twitter, facebook, instagram, youtube (URL values)\n"
        "- people: key personnel with name, designation/title, email, mobile/phone, linkedin_url\n\n"
        "Only include information explicitly stated on the website. "
        "Return null for fields not found.\n\n"
        f"WEBSITE CONTENT:\n{markdown[:50000]}"
    )

    # Use Gemini via the REST API (generateContent endpoint)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0,
        },
    }
    params = {"key": settings.GEMINI_API_KEY}

    try:
        resp = await client.post(url, headers=headers, json=payload, params=params, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return CompanyParsedData.model_validate_json(text)
    except Exception as exc:
        logger.warning("Gemini parse error: %s", exc)
        return CompanyParsedData()


# ---------------------------------------------------------------------------
# Step 4: Apollo people (conditional)
# ---------------------------------------------------------------------------

async def _apollo_search_people(
    client: httpx.AsyncClient,
    org_id: Optional[str],
    domain: str,
) -> list[dict]:
    headers = {
        "x-api-key": settings.APOLLO_API_KEY,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload: dict[str, Any] = {
        "per_page": 10,
        "page": 1,
        "person_titles": DECISION_MAKER_TITLES,
        "contact_email_status": ["verified"],
    }
    if org_id:
        payload["organization_ids"] = [org_id]
    elif domain:
        payload["q_organization_domains_list"] = [domain]
    else:
        return []

    data = await _post_json(
        client, "https://api.apollo.io/api/v1/mixed_people/api_search", headers, payload,
    )
    return data.get("people") or []


async def _apollo_bulk_enrich(client: httpx.AsyncClient, apollo_ids: list[str]) -> list[dict]:
    if not apollo_ids:
        return []
    headers = {
        "x-api-key": settings.APOLLO_API_KEY,
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }
    payload = {
        "details": [{"id": aid} for aid in apollo_ids[:10]],
        "reveal_personal_emails": True,
        "reveal_phone_number": False,
    }
    data = await _post_json(
        client, "https://api.apollo.io/api/v1/people/bulk_match", headers, payload,
    )
    return data.get("matches") or []


async def _apollo_people_pipeline(
    client: httpx.AsyncClient,
    org_id: Optional[str],
    domain: str,
    company_name: str,
    website_people: list[dict],
) -> list[dict]:
    """Conditional Apollo people enrichment (scenarios A/B/C from POC)."""
    has_people = len(website_people) > 0
    has_contacts = any(
        (p.get("email") or "").strip() or (p.get("mobile") or "").strip()
        for p in website_people
    )

    # Scenario A: website gave people WITH contacts
    if has_people and has_contacts:
        logger.info("Apollo people: skipped (website provided contacts)")
        for p in website_people:
            p["is_decision_maker"] = _is_decision_maker(p.get("designation", ""))
        return website_people

    if not org_id and not domain:
        logger.info("Apollo people: skipped (no org_id or domain)")
        return website_people

    logger.info("Apollo: searching people (org_id=%s)", org_id)
    stubs = await _apollo_search_people(client, org_id, domain)

    if not stubs:
        logger.info("Apollo: no people found")
        return website_people

    # Scenario B: website gave names but NO contacts
    if has_people and not has_contacts:
        logger.info("Scenario B: %d known people without contacts", len(website_people))

        matched_ids = []
        unmatched_stubs = []
        for stub in stubs:
            stub_name = stub.get("name") or ""
            if not stub_name:
                fn = stub.get("first_name") or ""
                ln = stub.get("last_name") or ""
                stub_name = f"{fn} {ln}".strip()

            matched = False
            for wp in website_people:
                if _fuzzy_match(wp.get("name", ""), stub_name):
                    sid = stub.get("id")
                    if sid and (stub.get("has_email") or stub.get("has_direct_phone") == "Yes"):
                        matched_ids.append(sid)
                    matched = True
                    break
            if not matched:
                unmatched_stubs.append(stub)

        additional_ids = [
            s["id"] for s in unmatched_stubs
            if s.get("id") and (s.get("has_email") or s.get("has_direct_phone") == "Yes")
        ]

        all_ids = matched_ids + additional_ids
        if not all_ids:
            return website_people

        logger.info("Apollo: enriching %d matched + %d additional", len(matched_ids), len(additional_ids))
        enriched_raw = await _apollo_bulk_enrich(client, all_ids)

        for ap in enriched_raw:
            ap_name = ap.get("name") or ""
            merged = False
            for wp in website_people:
                if _fuzzy_match(wp.get("name", ""), ap_name):
                    if not (wp.get("email") or "").strip():
                        wp["email"] = ap.get("email") or ""
                        wp["email_verified"] = (ap.get("email_status") or "") == "verified"
                    if not (wp.get("mobile") or "").strip():
                        phones = ap.get("phone_numbers") or []
                        wp["mobile"] = phones[0].get("sanitized_number") if phones else ""
                    if not wp.get("linkedin_url"):
                        wp["linkedin_url"] = ap.get("linkedin_url") or ""
                    if not wp.get("designation"):
                        wp["designation"] = ap.get("title") or ""
                    wp["apollo_id"] = ap.get("id") or ""
                    wp["source"] = "website+apollo"
                    wp["is_decision_maker"] = _is_decision_maker(wp.get("designation", ""))
                    merged = True
                    break
            if not merged:
                website_people.append(_normalise_apollo_person(ap, domain))

        return website_people

    # Scenario C: no people from website
    logger.info("Scenario C: full discovery — %d stubs found", len(stubs))
    enrichable = [
        p for p in stubs
        if p.get("has_email") or p.get("has_direct_phone") == "Yes"
    ]
    if not enrichable:
        return []

    apollo_ids = [p["id"] for p in enrichable if p.get("id")]
    enriched_raw = await _apollo_bulk_enrich(client, apollo_ids)
    return [_normalise_apollo_person(p, domain) for p in enriched_raw]


# ---------------------------------------------------------------------------
# Confidence score calculation
# ---------------------------------------------------------------------------

def _calculate_confidence(result: dict) -> float:
    """Calculate a 0.0-1.0 confidence score based on data completeness."""
    fields = [
        ("website", 0.15),
        ("description", 0.15),
        ("linkedin", 0.10),
        ("industry", 0.10),
        ("company_email", 0.10),
        ("company_phone", 0.05),
        ("address", 0.05),
        ("year_established", 0.05),
        ("logo_url", 0.05),
        ("number_of_employees", 0.05),
        ("people", 0.15),
    ]
    score = 0.0
    for field, weight in fields:
        val = result.get(field)
        if field == "people":
            if val and len(val) > 0:
                score += weight
        elif val:
            score += weight
    return round(min(score, 1.0), 2)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_enrichment_pipeline(
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    """
    Run the full enrichment pipeline for a company.
    This runs as a background task with its own DB session.
    """
    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline_inner(db, company_id, task_id, tenant_id)
        except Exception as exc:
            logger.error("Enrichment pipeline failed: company=%s error=%s", company_id, exc, exc_info=True)
            # Mark task as failed
            try:
                task = (await db.execute(
                    select(AgentTask).where(AgentTask.id == task_id)
                )).scalar_one_or_none()
                if task:
                    task.status = AgentTaskStatus.failed
                    task.error = str(exc)
                    task.completed_at = datetime.now(timezone.utc)
                    await db.commit()

                company = (await db.execute(
                    select(Company).where(Company.id == company_id)
                )).scalar_one_or_none()
                if company:
                    company.enrichment_status = EnrichmentStatus.not_enriched
                    await db.commit()
            except Exception:
                logger.error("Failed to update task/company status after error", exc_info=True)


async def _run_pipeline_inner(
    db: AsyncSession,
    company_id: uuid.UUID,
    task_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    # Load task and company
    task = (await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )).scalar_one_or_none()
    if not task:
        logger.error("AgentTask %s not found", task_id)
        return

    company = (await db.execute(
        select(Company).where(Company.id == company_id)
    )).scalar_one_or_none()
    if not company:
        logger.error("Company %s not found", company_id)
        task.status = AgentTaskStatus.failed
        task.error = "Company not found"
        await db.commit()
        return

    company_name = company.name
    country = company.country or ""

    result: dict[str, Any] = {
        "name": company_name,
        "country": country,
        "description": None,
        "website": company.website or "",
        "linkedin": None,
        "industry": None,
        "year_established": None,
        "number_of_employees": None,
        "logo_url": None,
        "products": [],
        "target_industries": [],
        "company_email": None,
        "company_phone": None,
        "address": None,
        "certifications": [],
        "social_media": None,
        "people": [],
    }

    async with httpx.AsyncClient() as client:
        # ------------------------------------------------------------------
        # Step 1: Perplexity lookup
        # ------------------------------------------------------------------
        await _update_step(db, task, 0, "running", "Searching the web...")
        logger.info("[1] Perplexity lookup: %s", company_name)

        pplx = await _perplexity_lookup(client, company_name, country)

        result["website"] = pplx.get("website") or result["website"] or ""
        result["linkedin"] = pplx.get("linkedin") or ""
        result["description"] = pplx.get("description") or None
        result["industry"] = pplx.get("industry") or None
        result["year_established"] = pplx.get("year_established")
        if pplx.get("country"):
            result["country"] = pplx["country"]

        await _update_step(db, task, 0, "completed", f"Found website: {result['website'] or 'none'}")

        domain = _domain_from_url(result["website"])

        # ------------------------------------------------------------------
        # Step 2: Parallel Firecrawl + Apollo org
        # ------------------------------------------------------------------
        await _update_step(db, task, 1, "running", "Scraping website and checking directories...")
        logger.info("[2] Parallel: Firecrawl + Apollo org for %s", company_name)

        fc_task = _firecrawl_pipeline(client, result["website"])
        ao_task = _apollo_search_org(client, domain, company_name)
        markdown, apollo_org = await asyncio.gather(fc_task, ao_task)

        org_id = apollo_org.get("org_id") if apollo_org else None
        if apollo_org:
            result["linkedin"] = result["linkedin"] or apollo_org.get("linkedin_url") or ""
            result["logo_url"] = apollo_org.get("logo_url")
            result["industry"] = result["industry"] or apollo_org.get("industry")
            result["number_of_employees"] = apollo_org.get("estimated_num_employees")
            result["year_established"] = result["year_established"] or apollo_org.get("founded_year")
            result["country"] = result["country"] or apollo_org.get("country") or country
            result["company_phone"] = apollo_org.get("primary_phone")

        detail_parts = []
        if markdown:
            detail_parts.append("Website scraped")
        if apollo_org:
            detail_parts.append("Trade directory match found")
        await _update_step(db, task, 1, "completed", "; ".join(detail_parts) or "No data found")

        # ------------------------------------------------------------------
        # Step 3: Gemini parse
        # ------------------------------------------------------------------
        await _update_step(db, task, 2, "running", "Analyzing company data...")
        logger.info("[3] Gemini parse for %s", company_name)

        company_data = CompanyParsedData()
        if markdown:
            company_data = await _gemini_parse_company(client, markdown)

        # Merge Gemini data
        result["description"] = company_data.description or result["description"]
        result["products"] = company_data.products or []
        result["target_industries"] = company_data.target_industries or []
        result["company_email"] = company_data.company_email or result.get("company_email")
        result["company_phone"] = company_data.company_phone or result["company_phone"]
        result["address"] = company_data.address
        result["certifications"] = company_data.certifications or []
        result["year_established"] = company_data.year_established or result["year_established"]
        sm = company_data.social_media
        result["social_media"] = sm.model_dump(exclude_none=True) if sm else None

        website_people = [p.model_dump(exclude_none=False) for p in (company_data.people or [])]

        detail = f"Extracted {len(result['products'])} products, {len(website_people)} people"
        await _update_step(db, task, 2, "completed", detail)

        # ------------------------------------------------------------------
        # Step 4: Apollo people (conditional)
        # ------------------------------------------------------------------
        await _update_step(db, task, 3, "running", "Discovering decision makers...")
        logger.info("[4] Apollo people for %s", company_name)

        result["people"] = await _apollo_people_pipeline(
            client, org_id, domain, company_name, website_people,
        )

        people_count = len(result["people"])
        await _update_step(db, task, 3, "completed", f"Found {people_count} contacts")

    # ------------------------------------------------------------------
    # Step 5: Finalize — update Company + create Contacts
    # ------------------------------------------------------------------
    await _update_step(db, task, 4, "running", "Saving enriched profile...")
    logger.info("[5] Finalizing enrichment for %s", company_name)

    # Reload company to avoid stale state
    company = (await db.execute(
        select(Company).where(Company.id == company_id)
    )).scalar_one()

    # Update Company fields
    company.description = result["description"] or company.description
    company.website = result["website"] or company.website
    company.linkedin_url = result["linkedin"] or company.linkedin_url
    company.industry = result["industry"] or company.industry
    company.year_established = result["year_established"] or company.year_established
    company.logo_url = result["logo_url"] or company.logo_url
    company.phone = result["company_phone"] or company.phone
    company.email = result["company_email"] or company.email
    company.address = result["address"] or company.address
    company.social_media = result["social_media"] or company.social_media
    company.target_industries = result["target_industries"] or company.target_industries
    company.certifications_required = result["certifications"] or company.certifications_required
    company.commodities = result["products"] or company.commodities

    if result["number_of_employees"] is not None:
        # Convert integer to range string as expected by schema
        emp = result["number_of_employees"]
        if isinstance(emp, int):
            if emp <= 10:
                company.number_of_employees = "1-10"
            elif emp <= 50:
                company.number_of_employees = "11-50"
            elif emp <= 200:
                company.number_of_employees = "51-200"
            elif emp <= 500:
                company.number_of_employees = "201-500"
            else:
                company.number_of_employees = "500+"
        else:
            company.number_of_employees = str(emp)

    # Calculate confidence
    confidence = _calculate_confidence(result)
    company.confidence_score = confidence

    # Store full enrichment data
    company.enrichment_data = {
        "products": result["products"],
        "certifications": result["certifications"],
        "social_media": result["social_media"],
        "people_count": len(result["people"]),
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    # Determine enrichment status
    has_essential = bool(result["website"] or result["description"] or result["industry"])
    has_contacts = len(result["people"]) > 0
    if has_essential and has_contacts:
        company.enrichment_status = EnrichmentStatus.enriched
    elif has_essential or has_contacts:
        company.enrichment_status = EnrichmentStatus.partially_enriched
    else:
        company.enrichment_status = EnrichmentStatus.partially_enriched

    await db.flush()

    # Create Contact records for discovered people
    contacts_created = 0
    for person in result["people"]:
        person_name = (person.get("name") or "").strip()
        if not person_name:
            continue

        # Check for existing contact with same name+company
        existing = (await db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id,
                Contact.company_id == company_id,
                Contact.name == person_name,
                Contact.is_deleted.is_(False),
            )
        )).scalar_one_or_none()

        if existing:
            # Update existing contact with new data
            if not existing.email and person.get("email"):
                existing.email = person["email"]
            if not existing.phone and person.get("mobile"):
                existing.phone = person["mobile"]
            if not existing.linkedin_url and person.get("linkedin_url"):
                existing.linkedin_url = person["linkedin_url"]
            if not existing.title and person.get("designation"):
                existing.title = person["designation"]
            existing.is_decision_maker = person.get("is_decision_maker", False)
            existing.enrichment_status = ContactEnrichmentStatus.enriched
        else:
            contact = Contact(
                tenant_id=tenant_id,
                company_id=company_id,
                company_name=company_name,
                name=person_name,
                email=person.get("email") or None,
                phone=person.get("mobile") or None,
                linkedin_url=person.get("linkedin_url") or None,
                title=person.get("designation") or None,
                is_decision_maker=person.get("is_decision_maker", False),
                country=person.get("country") or company.country,
                city=person.get("city") or company.city,
                source=ContactSource.enrichment,
                enrichment_status=ContactEnrichmentStatus.enriched,
            )
            db.add(contact)
            contacts_created += 1

    # Finalize the AgentTask
    task = (await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )).scalar_one()

    task.status = AgentTaskStatus.completed
    task.completed_at = datetime.now(timezone.utc)
    task.credits_consumed = 1
    task.output_data = {
        "company_id": str(company_id),
        "confidence_score": confidence,
        "people_found": len(result["people"]),
        "contacts_created": contacts_created,
        "fields_enriched": [
            k for k, v in {
                "website": result["website"],
                "description": result["description"],
                "linkedin": result["linkedin"],
                "industry": result["industry"],
                "email": result["company_email"],
                "phone": result["company_phone"],
                "address": result["address"],
            }.items() if v
        ],
    }

    await _update_step(db, task, 4, "completed", f"Profile saved. {contacts_created} contacts created.")
    await db.commit()

    logger.info(
        "Enrichment complete: company=%s confidence=%.2f people=%d contacts_created=%d",
        company_name, confidence, len(result["people"]), contacts_created,
    )

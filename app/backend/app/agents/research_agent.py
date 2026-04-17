"""Research Agent — Trade Intelligence Researcher.

Finds information about companies: web presence, shipment data, key people,
competitor suppliers, risk signals, news, and certifications.
"""
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("agents.research")


class ResearchAgent:
    """Researches a company and produces a structured intelligence profile."""

    TIMEOUT = 90  # seconds

    def __init__(self):
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._http

    async def run(
        self,
        company_name: str,
        country: Optional[str] = None,
        website: Optional[str] = None,
        on_step: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute the full research pipeline. Returns structured profile."""
        logger.info("Research started: company=%s country=%s", company_name, country)
        result = {
            "company_overview": {},
            "trade_intelligence": {},
            "key_people": [],
            "competitor_suppliers": [],
            "risk_signals": [],
            "news": [],
            "certifications": [],
            "sources": [],
        }

        # Step 1: Web search
        if on_step:
            await on_step("Searching the web for company information...")
        web_results = await self._web_search(company_name, country)
        result["sources"].append({"name": "Web Search", "count": len(web_results)})

        # Step 2: Website scraping
        if on_step:
            await on_step("Analyzing company website...")
        if website:
            site_data = await self._scrape_website(website)
            result["company_overview"] = {
                "name": company_name,
                "country": country,
                "website": website,
                "about": site_data.get("about", ""),
                "products": site_data.get("products", []),
                "source": website,
                "confidence": 0.8,
            }
            result["sources"].append({"name": website, "count": 1})
        else:
            result["company_overview"] = {
                "name": company_name,
                "country": country,
                "website": None,
                "about": "",
                "products": [],
                "source": "web_search",
                "confidence": 0.5,
            }

        # Step 3: Trade intelligence (shipment data)
        if on_step:
            await on_step("Analyzing shipment and trade data...")
        result["trade_intelligence"] = await self._get_trade_intelligence(company_name, country)
        result["sources"].append({"name": "Trade Data", "count": 1})

        # Step 4: Key people
        if on_step:
            await on_step("Identifying key decision makers...")
        result["key_people"] = await self._find_key_people(company_name, web_results)

        # Step 5: Synthesis
        if on_step:
            await on_step("Synthesizing research findings...")
        result["risk_signals"] = self._analyze_risks(result)
        result["confidence_score"] = self._calculate_confidence(result)

        logger.info(
            "Research completed: company=%s sources=%d confidence=%.2f",
            company_name, len(result["sources"]), result["confidence_score"],
        )
        return result

    async def _web_search(self, query: str, country: Optional[str] = None) -> List[Dict]:
        """Search the web using Brave Search API."""
        if not settings.BRAVE_SEARCH_API_KEY:
            logger.debug("Brave Search not configured, returning mock results")
            return [
                {"title": f"{query} - Company Profile", "url": f"https://example.com/{query.lower().replace(' ', '-')}"},
                {"title": f"{query} import records", "url": "https://tradedatabase.example.com"},
            ]

        try:
            http = await self._get_http()
            search_query = f"{query} {country} importer buyer" if country else f"{query} importer buyer"
            response = await http.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": search_query, "count": 10},
                headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY},
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    {"title": r.get("title", ""), "url": r.get("url", ""), "description": r.get("description", "")}
                    for r in data.get("web", {}).get("results", [])
                ]
        except Exception as e:
            logger.error("Web search failed: %s", str(e))

        return []

    async def _scrape_website(self, url: str) -> Dict[str, Any]:
        """Scrape a company website for basic info."""
        try:
            http = await self._get_http()
            response = await http.get(url)
            if response.status_code != 200:
                return {}

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract meta description as "about"
            meta_desc = soup.find("meta", attrs={"name": "description"})
            about = meta_desc["content"] if meta_desc and meta_desc.get("content") else ""

            # Extract title
            title = soup.title.string if soup.title else ""

            return {
                "about": about,
                "title": title,
                "products": [],
            }
        except Exception as e:
            logger.warning("Website scrape failed for %s: %s", url, str(e))
            return {}

    async def _get_trade_intelligence(self, company_name: str, country: Optional[str]) -> Dict[str, Any]:
        """Get trade/shipment intelligence. Placeholder — wire to TradeGenie/internal DB."""
        return {
            "import_volume_estimate": None,
            "commodities_traded": [],
            "top_origin_countries": [],
            "shipment_frequency": None,
            "last_known_shipment": None,
            "source": "pending_integration",
            "confidence": 0.3,
        }

    async def _find_key_people(self, company_name: str, web_results: List[Dict]) -> List[Dict]:
        """Find key people at a company. Placeholder — wire to LinkedIn/contact APIs."""
        return []

    def _analyze_risks(self, profile: Dict) -> List[Dict]:
        """Analyze research data for risk signals."""
        risks = []
        trade = profile.get("trade_intelligence", {})

        if trade.get("shipment_frequency") == "declining":
            risks.append({
                "signal": "Declining shipment frequency",
                "severity": "medium",
                "detail": "Import volume appears to be decreasing",
            })

        if not profile.get("company_overview", {}).get("website"):
            risks.append({
                "signal": "No website found",
                "severity": "low",
                "detail": "Could not find a company website",
            })

        return risks

    def _calculate_confidence(self, profile: Dict) -> float:
        """Calculate overall confidence score based on data completeness."""
        score = 0.0
        weights = {
            "has_overview": 0.2,
            "has_website": 0.15,
            "has_trade_data": 0.25,
            "has_people": 0.15,
            "has_about": 0.1,
            "has_commodities": 0.15,
        }

        overview = profile.get("company_overview", {})
        trade = profile.get("trade_intelligence", {})

        if overview.get("name"):
            score += weights["has_overview"]
        if overview.get("website"):
            score += weights["has_website"]
        if trade.get("commodities_traded"):
            score += weights["has_trade_data"]
        if profile.get("key_people"):
            score += weights["has_people"]
        if overview.get("about"):
            score += weights["has_about"]
        if trade.get("commodities_traded"):
            score += weights["has_commodities"]

        return round(min(score, 1.0), 2)

    async def close(self):
        if self._http:
            await self._http.aclose()
            self._http = None


research_agent = ResearchAgent()

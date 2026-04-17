"""TradeCRM Shipment Integration Client — extensible interface for shipment data.

V1: Returns data from local DB (seeded mock data).
Future: Swap implementation to call real shipment API
without changing any callers.
"""
from datetime import date
from typing import Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger("integrations.shipments")


class ShipmentClient:
    """Client for fetching shipment data from the trade intelligence platform.

    V1 implementation uses local DB as source.
    To integrate with real API, replace the fetch_* methods.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.api_url = api_url or "https://api.tradecrm.example/v1/shipments"
        self.api_key = api_key
        self._initialized = True

    async def fetch_company_shipments(
        self,
        company_name: str,
        country: Optional[str] = None,
        limit: int = 100,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict]:
        """Fetch shipment records for a company.

        V1: This is a stub — real data comes from the local DB via the
        shipment aggregator service. This client exists as the integration
        point for when the real shipment API is available.

        Returns:
            List of shipment dicts with keys:
            - source_id, shipment_date, direction, commodity_text, hs_code
            - origin_country, destination_country, origin_port, destination_port
            - volume_mt, unit_price_usd_per_mt, value_usd
            - trade_partner_name, trade_partner_country
        """
        logger.info("fetch_company_shipments: company=%s (V1 stub — using local DB)", company_name)
        # V1: return empty — data is already in local DB from seed
        # When real API is ready, implement HTTP call here:
        #
        # async with httpx.AsyncClient(timeout=30) as client:
        #     resp = await client.get(
        #         f"{self.api_url}/search",
        #         params={"company": company_name, "country": country, "limit": limit},
        #         headers={"Authorization": f"Bearer {self.api_key}"},
        #     )
        #     resp.raise_for_status()
        #     return resp.json()["shipments"]
        return []

    async def health_check(self) -> bool:
        """Check if the shipment API is available."""
        # V1: always true (using local DB)
        return True


# Singleton instance
shipment_client = ShipmentClient()

"""Catalog Matcher — fuzzy-matches free-text commodity strings to tenant's product catalog."""
from typing import List, Optional, Tuple

from app.logging_config import get_logger

logger = get_logger("services.catalog_matcher")


def match_commodity_to_catalog(
    commodity_text: str,
    products: list,
) -> Tuple[Optional[str], float]:
    """Match a free-text commodity string to a catalog product.

    Priority:
    1. Exact match to Product.name (case-insensitive)
    2. Exact match to any value in Product.aliases
    3. HS code prefix match (6-digit)
    4. Fuzzy match (token_set_ratio >= 85)

    Args:
        commodity_text: Free-text commodity string (e.g. "Black Pepper ASTA 550GL")
        products: List of Product model instances with name, aliases, hs_code

    Returns:
        (product_id_str, confidence) or (None, 0.0)
    """
    if not commodity_text or not products:
        return None, 0.0

    text_lower = commodity_text.lower().strip()

    # 1. Exact name match
    for p in products:
        if p.name.lower() == text_lower:
            return str(p.id), 1.0

    # 2. Alias match
    for p in products:
        aliases = p.aliases or []
        for alias in aliases:
            if isinstance(alias, str) and alias.lower() == text_lower:
                return str(p.id), 0.95

    # 3. Partial name match (commodity text contains product name or vice versa)
    for p in products:
        pname = p.name.lower()
        if pname in text_lower or text_lower in pname:
            return str(p.id), 0.85

    # 4. HS code prefix match
    # Extract HS-like codes from commodity text
    import re
    hs_in_text = re.findall(r'\b(\d{6})\b', commodity_text)
    if hs_in_text:
        for p in products:
            if p.hs_code:
                p_hs_prefix = p.hs_code.replace(".", "")[:6]
                for hs in hs_in_text:
                    if hs[:6] == p_hs_prefix[:6]:
                        return str(p.id), 0.8

    # 5. Token overlap (simple fuzzy without external dependency)
    best_score = 0.0
    best_product = None
    text_tokens = set(text_lower.split())

    for p in products:
        name_tokens = set(p.name.lower().split())
        all_tokens = name_tokens.copy()
        for alias in (p.aliases or []):
            if isinstance(alias, str):
                all_tokens.update(alias.lower().split())

        if not all_tokens:
            continue

        overlap = len(text_tokens & all_tokens)
        total = len(text_tokens | all_tokens)
        score = overlap / total if total > 0 else 0

        if score > best_score:
            best_score = score
            best_product = p

    if best_score >= 0.4 and best_product:
        confidence = min(0.7, 0.5 + best_score * 0.4)
        return str(best_product.id), confidence

    return None, 0.0


def match_commodities_batch(
    commodity_texts: List[str],
    products: list,
) -> List[Tuple[str, Optional[str], float]]:
    """Match multiple commodity strings to catalog products.

    Returns list of (commodity_text, product_id_or_none, confidence).
    """
    results = []
    for text in commodity_texts:
        pid, conf = match_commodity_to_catalog(text, products)
        results.append((text, pid, conf))
    return results

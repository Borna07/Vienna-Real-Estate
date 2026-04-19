"""Willhaben apartment listings scraper module."""

import math
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin, urlparse, parse_qs, urlunparse

from playwright.sync_api import sync_playwright


@dataclass
class Listing:
    """Represents a single apartment listing."""
    ad_id: str
    title: str
    price: str
    price_value: Optional[int]
    location: str
    rooms: str
    size_sqm: str
    size_sqm_value: Optional[float]
    price_per_sqm: Optional[float]
    url: str


# Base URL for building listing URLs
WILLHABEN_BASE_URL = "https://www.willhaben.at/iad/"


def build_page_url(base_url: str, page: int) -> str:
    """Build URL for a specific page of results."""
    if page <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def attributes_to_dict(attributes: Dict[str, object]) -> Dict[str, str]:
    """Convert Willhaben attributes list to a dict."""
    values: Dict[str, str] = {}
    for entry in attributes.get("attribute", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        vals = entry.get("values") or []
        if name and vals:
            values[name] = vals[0]
    return values


def parse_price_value(price_str: str) -> Optional[int]:
    """
    Parse Willhaben price strings to whole EUR.

    Handles Austrian formatting: sale totals like '€ 448.400' (thousand dots),
    and rents like '€ 1.610,43' (comma decimals) or '€ 1.695'.
    """
    if not price_str:
        return None
    s = price_str.replace("€", "").strip()
    low = s.lower()
    for suf in ("/monat", "/ month", "pro monat", "p.m.", "p. m."):
        if suf in low:
            s = s[: low.index(suf)].strip()
            low = s.lower()
            break
    s = s.replace(" ", "")
    if not s:
        return None

    # Comma as decimal separator (e.g. 1.610,43)
    if "," in s:
        left, right = s.rsplit(",", 1)
        left = left.replace(".", "")
        right = right.strip()
        if right.isdigit() and len(right) <= 2:
            try:
                return int(round(float(f"{left}.{right}")))
            except ValueError:
                return None
        digits = "".join(c for c in s if c.isdigit())
        return int(digits) if digits else None

    # Dots: thousands (448.400) or decimal (12.5)
    if "." in s:
        parts = s.split(".")
        if all(p.isdigit() for p in parts) and len(parts[-1]) == 3:
            return int("".join(parts))
        try:
            return int(round(float(s.replace(",", "."))))
        except ValueError:
            pass
        digits = "".join(c for c in s if c.isdigit())
        return int(digits) if digits else None

    digits = "".join(c for c in s if c.isdigit())
    return int(digits) if digits else None


def parse_size_value(size_str: str) -> Optional[float]:
    """Extract numeric size value from string like '80' or '80.5'."""
    if not size_str:
        return None
    try:
        return float(size_str.replace(",", "."))
    except ValueError:
        return None


def extract_listings_from_search_result(
    search_result: Dict[str, object], base_url: str
) -> List[Listing]:
    """Extract listings from Willhaben search result data."""
    results: List[Listing] = []
    summary_list = search_result.get("advertSummaryList", {})
    
    for item in summary_list.get("advertSummary", []):
        ad_id = str(item.get("id", ""))
        attrs = attributes_to_dict(item.get("attributes", {}))
        
        title = attrs.get("HEADING") or attrs.get("UNIT_TITLE") or ""
        price_display = attrs.get("PRICE_FOR_DISPLAY") or ""
        price_raw = attrs.get("PRICE") or ""
        location = attrs.get("LOCATION") or attrs.get("ADDRESS") or ""
        rooms = attrs.get("NUMBER_OF_ROOMS") or attrs.get("ROOMS") or ""
        size = attrs.get("ESTATE_SIZE") or attrs.get("LIVING_AREA") or ""
        seo_url = attrs.get("SEO_URL") or ""
        
        # Parse numeric values
        price_value = parse_price_value(price_raw) or parse_price_value(price_display)
        size_value = parse_size_value(size)
        
        # Calculate price per sqm
        price_per_sqm = None
        if price_value and size_value and size_value > 0:
            price_per_sqm = round(price_value / size_value, 2)
        
        # Build proper URL using the Willhaben base URL
        listing_url = ""
        if seo_url:
            listing_url = urljoin(WILLHABEN_BASE_URL, seo_url)
        
        results.append(
            Listing(
                ad_id=ad_id,
                title=title,
                price=price_display or price_raw,
                price_value=price_value,
                location=location,
                rooms=rooms,
                size_sqm=size,
                size_sqm_value=size_value,
                price_per_sqm=price_per_sqm,
                url=listing_url,
            )
        )
    return results


def scrape_listings(
    base_url: str,
    max_pages: Optional[int] = None,
    headless: bool = True,
    rows: int = 30,
) -> List[Listing]:
    """
    Scrape all apartment listings from Willhaben search results.
    
    Args:
        base_url: The Willhaben search URL
        max_pages: Maximum pages to scrape (None for all)
        headless: Run browser in headless mode
        rows: Expected rows per page
        
    Returns:
        List of Listing objects
    """
    all_listings: List[Listing] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.set_default_timeout(120000)

        page_index = 1
        total_pages: Optional[int] = None

        while True:
            if max_pages is not None and page_index > max_pages:
                break

            page_url = build_page_url(base_url, page_index)
            try:
                page.goto(page_url, wait_until="domcontentloaded", timeout=120000)
            except Exception:
                page.goto(page_url, wait_until="load", timeout=120000)
            
            page.wait_for_function(
                "window.__NEXT_DATA__ && window.__NEXT_DATA__.props && "
                "window.__NEXT_DATA__.props.pageProps && "
                "window.__NEXT_DATA__.props.pageProps.searchResult"
            )
            time.sleep(1.5)

            search_result = page.evaluate(
                "window.__NEXT_DATA__.props.pageProps.searchResult"
            )
            if not search_result:
                break

            if total_pages is None:
                rows_found = int(search_result.get("rowsFound", 0))
                rows_requested = int(search_result.get("rowsRequested", rows))
                total_pages = math.ceil(rows_found / rows_requested) if rows_requested else 0

            listings = extract_listings_from_search_result(search_result, base_url)
            if not listings:
                break

            all_listings.extend(listings)
            print(f"Page {page_index}: {len(listings)} listings")

            page_index += 1
            if total_pages and page_index > total_pages:
                break

        browser.close()

    return all_listings

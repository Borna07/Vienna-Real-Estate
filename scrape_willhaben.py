import argparse
import csv
import math
import time
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin, urlparse, parse_qs, urlunparse

from playwright.sync_api import sync_playwright


@dataclass
class Listing:
    title: str
    price: str
    location: str
    rooms: str
    size_sqm: str
    url: str


def build_page_url(base_url: str, page: int) -> str:
    if page <= 1:
        return base_url
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def attributes_to_dict(attributes: Dict[str, object]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for entry in attributes.get("attribute", []):
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        vals = entry.get("values") or []
        if name and vals:
            values[name] = vals[0]
    return values


def extract_listings_from_search_result(
    search_result: Dict[str, object], base_url: str
) -> List[Listing]:
    results: List[Listing] = []
    summary_list = search_result.get("advertSummaryList", {})
    for item in summary_list.get("advertSummary", []):
        attrs = attributes_to_dict(item.get("attributes", {}))
        title = attrs.get("HEADING") or attrs.get("UNIT_TITLE") or ""
        price = attrs.get("PRICE_FOR_DISPLAY") or attrs.get("PRICE") or ""
        location = attrs.get("LOCATION") or attrs.get("ADDRESS") or ""
        rooms = attrs.get("NUMBER_OF_ROOMS") or attrs.get("ROOMS") or ""
        size = attrs.get("ESTATE_SIZE") or attrs.get("LIVING_AREA") or ""
        seo_url = attrs.get("SEO_URL") or ""

        results.append(
            Listing(
                title=title,
                price=price,
                location=location,
                rooms=rooms,
                size_sqm=size,
                url=urljoin(base_url, seo_url),
            )
        )
    return results


def write_csv(path: str, listings: Iterable[Listing]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["title", "price", "location", "rooms", "size_sqm", "url"]
        )
        writer.writeheader()
        for listing in listings:
            writer.writerow(asdict(listing))


def scrape(
    base_url: str,
    max_pages: Optional[int],
    output_csv: str,
    headless: bool,
    rows: int,
) -> None:
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

    write_csv(output_csv, all_listings)
    print(f"Saved {len(all_listings)} listings to {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Willhaben apartment listings.")
    parser.add_argument("--url", required=True, help="Search results URL.")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--rows", type=int, default=30)
    parser.add_argument("--out", default="willhaben_listings.csv")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    scrape(args.url, args.max_pages, args.out, headless=not args.headed, rows=args.rows)


if __name__ == "__main__":
    main()

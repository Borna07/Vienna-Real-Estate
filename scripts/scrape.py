"""
Scheduled scraper entrypoint for Vienna Apartment Price Tracker.

Run with: python -m scripts.scrape
Optional: python -m scripts.scrape --market sale|rent|all
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_scrape_url, get_scrape_url_rent
from src.db import (
    MARKET_RENT,
    MARKET_SALE,
    init_db,
    get_connection,
    get_or_create_listing,
    insert_snapshot,
    get_open_listing_ad_ids,
    mark_listings_closed,
    start_scrape_run,
    complete_scrape_run,
    fail_scrape_run,
)
from src.scraper import scrape_listings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "scrape.log"),
    ],
)
logger = logging.getLogger(__name__)


def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)


def run_scrape_for_market(market: str, scrape_url: str) -> None:
    """Execute one scrape cycle for a single market segment."""
    if not scrape_url.strip():
        logger.info("Skipping %s: empty URL", market)
        return

    logger.info("Starting scrape run [%s]...", market)
    logger.info("Scraping URL: %s", scrape_url)

    with get_connection() as conn:
        run_id = start_scrape_run(conn, market)
        conn.commit()

        try:
            open_ad_ids_before = set(get_open_listing_ad_ids(conn, market))
            logger.info("Open listings before scrape [%s]: %s", market, len(open_ad_ids_before))

            listings = scrape_listings(scrape_url, headless=True)
            logger.info("Scraped %s listings [%s]", len(listings), market)

            scraped_at = datetime.utcnow()
            new_count = 0
            scraped_ad_ids = set()

            for listing in listings:
                if not listing.ad_id:
                    continue
                if listing.ad_id in scraped_ad_ids:
                    continue
                scraped_ad_ids.add(listing.ad_id)

                is_new = listing.ad_id not in open_ad_ids_before
                listing_id = get_or_create_listing(conn, listing.ad_id, listing.url, market)

                if is_new:
                    new_count += 1

                insert_snapshot(
                    conn,
                    listing_id=listing_id,
                    scraped_at=scraped_at,
                    title=listing.title,
                    price=listing.price,
                    price_value=listing.price_value,
                    location=listing.location,
                    rooms=listing.rooms,
                    size_sqm=listing.size_sqm,
                    size_sqm_value=listing.size_sqm_value,
                    price_per_sqm=listing.price_per_sqm,
                )

            closed_ad_ids = list(open_ad_ids_before - scraped_ad_ids)
            closed_count = 0
            if closed_ad_ids:
                closed_count = mark_listings_closed(
                    conn, closed_ad_ids, scraped_at, market
                )
                logger.info("Marked %s listings as closed [%s]", closed_count, market)

            complete_scrape_run(
                conn,
                run_id,
                listings_found=len(listings),
                new_listings=new_count,
                closed_listings=closed_count,
            )
            conn.commit()

            logger.info(
                "Scrape completed [%s]: %s found, %s new, %s closed",
                market,
                len(listings),
                new_count,
                closed_count,
            )

        except Exception as e:
            logger.exception("Scrape failed [%s]", market)
            fail_scrape_run(conn, run_id, str(e))
            conn.commit()
            raise


def run_scrape(market_filter: str = "all") -> None:
    """Run configured scrape jobs. market_filter: sale | rent | all"""
    ensure_log_dir()
    init_db()

    tasks: list[tuple[str, str]] = []
    sale_url = get_scrape_url().strip()
    if sale_url:
        tasks.append((MARKET_SALE, sale_url))
    rent_url = get_scrape_url_rent()
    if rent_url:
        tasks.append((MARKET_RENT, rent_url))

    if market_filter == "sale":
        tasks = [t for t in tasks if t[0] == MARKET_SALE]
    elif market_filter == "rent":
        tasks = [t for t in tasks if t[0] == MARKET_RENT]

    if not tasks:
        logger.warning(
            "No scrape tasks (check SCRAPE_URL / SCRAPE_URL_RENT and --market)."
        )
        return

    for market, url in tasks:
        run_scrape_for_market(market, url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Willhaben listings into the DB.")
    parser.add_argument(
        "--market",
        choices=("sale", "rent", "all"),
        default="all",
        help="Which segment to scrape (default: all configured URLs).",
    )
    args = parser.parse_args()
    run_scrape(market_filter=args.market)

"""
Scheduled scraper entrypoint for Vienna Apartment Price Tracker.

Run with: python -m scripts.scrape
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_scrape_url
from src.db import (
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
    ]
)
logger = logging.getLogger(__name__)


def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)


def run_scrape():
    """Execute a full scrape cycle with status tracking."""
    ensure_log_dir()
    
    logger.info("Starting scrape run...")
    
    # Initialize database
    init_db()
    
    scrape_url = get_scrape_url()
    logger.info(f"Scraping URL: {scrape_url}")
    
    with get_connection() as conn:
        # Start tracking this run
        run_id = start_scrape_run(conn)
        conn.commit()
        
        try:
            # Get currently open listings before scraping
            open_ad_ids_before = set(get_open_listing_ad_ids(conn))
            logger.info(f"Open listings before scrape: {len(open_ad_ids_before)}")
            
            # Scrape all listings
            listings = scrape_listings(scrape_url, headless=True)
            logger.info(f"Scraped {len(listings)} listings")
            
            # Process each listing
            scraped_at = datetime.utcnow()
            new_count = 0
            scraped_ad_ids = set()
            
            for listing in listings:
                if not listing.ad_id:
                    continue
                
                scraped_ad_ids.add(listing.ad_id)
                
                # Get or create listing record
                is_new = listing.ad_id not in open_ad_ids_before
                listing_id = get_or_create_listing(conn, listing.ad_id, listing.url)
                
                if is_new:
                    new_count += 1
                
                # Insert snapshot
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
            
            # Find listings that were open but not in current scrape (closed)
            closed_ad_ids = list(open_ad_ids_before - scraped_ad_ids)
            closed_count = 0
            if closed_ad_ids:
                closed_count = mark_listings_closed(conn, closed_ad_ids, scraped_at)
                logger.info(f"Marked {closed_count} listings as closed")
            
            # Complete the run
            complete_scrape_run(
                conn, 
                run_id, 
                listings_found=len(listings),
                new_listings=new_count,
                closed_listings=closed_count,
            )
            conn.commit()
            
            logger.info(
                f"Scrape completed: {len(listings)} found, "
                f"{new_count} new, {closed_count} closed"
            )
            
        except Exception as e:
            logger.exception("Scrape failed")
            fail_scrape_run(conn, run_id, str(e))
            conn.commit()
            raise


if __name__ == "__main__":
    run_scrape()

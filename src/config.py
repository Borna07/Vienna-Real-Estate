"""Configuration management for Vienna Apartment Price Tracker."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_database_path() -> Path:
    """Get the SQLite database file path."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///data/listings.db")
    # Extract path from sqlite:///path format
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
    else:
        db_path = db_url
    
    full_path = PROJECT_ROOT / db_path
    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path


def get_scrape_url() -> str:
    """Get the Willhaben search URL to scrape."""
    return os.getenv(
        "SCRAPE_URL",
        "https://www.willhaben.at/iad/immobilien/eigentumswohnung/eigentumswohnung-angebote"
    )


def get_scrape_interval_days() -> int:
    """Get scrape interval in days."""
    return int(os.getenv("SCRAPE_INTERVAL_DAYS", "3"))

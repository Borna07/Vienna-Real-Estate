"""Database layer for Vienna Apartment Price Tracker."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from .config import get_database_path


SCHEMA = """
-- Listings table: immutable ad identity
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Snapshots table: point-in-time data for each listing
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    price TEXT,
    price_value INTEGER,
    location TEXT,
    rooms TEXT,
    size_sqm TEXT,
    size_sqm_value REAL,
    price_per_sqm REAL,
    UNIQUE(listing_id, scraped_at)
);

-- Listing status table: track open/closed state
CREATE TABLE IF NOT EXISTS listing_status (
    listing_id INTEGER PRIMARY KEY REFERENCES listings(id),
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed')),
    closed_at TIMESTAMP
);

-- Scrape runs log
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    listings_found INTEGER,
    new_listings INTEGER,
    closed_listings INTEGER,
    status TEXT DEFAULT 'running'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_snapshots_listing_id ON snapshots(listing_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_scraped_at ON snapshots(scraped_at);
CREATE INDEX IF NOT EXISTS idx_listing_status_status ON listing_status(status);
"""


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with row factory."""
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def get_or_create_listing(conn: sqlite3.Connection, ad_id: str, url: str) -> int:
    """Get existing listing ID or create new one. Returns listing_id."""
    cursor = conn.execute(
        "SELECT id FROM listings WHERE ad_id = ?", (ad_id,)
    )
    row = cursor.fetchone()
    
    if row:
        return row["id"]
    
    cursor = conn.execute(
        "INSERT INTO listings (ad_id, url, first_seen_at) VALUES (?, ?, ?)",
        (ad_id, url, datetime.utcnow())
    )
    listing_id = cursor.lastrowid
    
    # Initialize status as open
    conn.execute(
        "INSERT INTO listing_status (listing_id, status) VALUES (?, 'open')",
        (listing_id,)
    )
    
    return listing_id


def insert_snapshot(
    conn: sqlite3.Connection,
    listing_id: int,
    scraped_at: datetime,
    title: str,
    price: str,
    price_value: Optional[int],
    location: str,
    rooms: str,
    size_sqm: str,
    size_sqm_value: Optional[float] = None,
    price_per_sqm: Optional[float] = None,
) -> None:
    """Insert a new snapshot for a listing."""
    conn.execute(
        """
        INSERT INTO snapshots 
        (listing_id, scraped_at, title, price, price_value, location, rooms, size_sqm, size_sqm_value, price_per_sqm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (listing_id, scraped_at, title, price, price_value, location, rooms, size_sqm, size_sqm_value, price_per_sqm)
    )


def get_open_listing_ad_ids(conn: sqlite3.Connection) -> List[str]:
    """Get all ad_ids of currently open listings."""
    cursor = conn.execute(
        """
        SELECT l.ad_id 
        FROM listings l
        JOIN listing_status ls ON l.id = ls.listing_id
        WHERE ls.status = 'open'
        """
    )
    return [row["ad_id"] for row in cursor.fetchall()]


def mark_listings_closed(
    conn: sqlite3.Connection, 
    ad_ids: List[str], 
    closed_at: datetime
) -> int:
    """Mark listings as closed. Returns count of closed listings."""
    if not ad_ids:
        return 0
    
    placeholders = ",".join("?" * len(ad_ids))
    cursor = conn.execute(
        f"""
        UPDATE listing_status
        SET status = 'closed', closed_at = ?
        WHERE listing_id IN (
            SELECT id FROM listings WHERE ad_id IN ({placeholders})
        )
        """,
        [closed_at] + ad_ids
    )
    return cursor.rowcount


def start_scrape_run(conn: sqlite3.Connection) -> int:
    """Start a new scrape run. Returns run_id."""
    cursor = conn.execute(
        "INSERT INTO scrape_runs (started_at, status) VALUES (?, 'running')",
        (datetime.utcnow(),)
    )
    return cursor.lastrowid


def complete_scrape_run(
    conn: sqlite3.Connection,
    run_id: int,
    listings_found: int,
    new_listings: int,
    closed_listings: int,
) -> None:
    """Mark a scrape run as completed."""
    conn.execute(
        """
        UPDATE scrape_runs 
        SET completed_at = ?, listings_found = ?, new_listings = ?, 
            closed_listings = ?, status = 'completed'
        WHERE id = ?
        """,
        (datetime.utcnow(), listings_found, new_listings, closed_listings, run_id)
    )


def fail_scrape_run(conn: sqlite3.Connection, run_id: int, error: str) -> None:
    """Mark a scrape run as failed."""
    conn.execute(
        """
        UPDATE scrape_runs 
        SET completed_at = ?, status = ?
        WHERE id = ?
        """,
        (datetime.utcnow(), f"failed: {error[:200]}", run_id)
    )


# Query helpers for dashboard

def get_listing_count_by_status(conn: sqlite3.Connection) -> dict:
    """Get count of open vs closed listings."""
    cursor = conn.execute(
        """
        SELECT status, COUNT(*) as count 
        FROM listing_status 
        GROUP BY status
        """
    )
    return {row["status"]: row["count"] for row in cursor.fetchall()}


def get_price_stats_over_time(conn: sqlite3.Connection) -> List[dict]:
    """Get average price statistics by scrape date."""
    cursor = conn.execute(
        """
        SELECT 
            DATE(scraped_at) as date,
            AVG(price_value) as avg_price,
            MIN(price_value) as min_price,
            MAX(price_value) as max_price,
            COUNT(*) as count
        FROM snapshots
        WHERE price_value IS NOT NULL
        GROUP BY DATE(scraped_at)
        ORDER BY date
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def get_price_by_district(conn: sqlite3.Connection) -> List[dict]:
    """Get price statistics by district/location."""
    cursor = conn.execute(
        """
        SELECT 
            location,
            AVG(price_value) as avg_price,
            COUNT(*) as count
        FROM snapshots s
        JOIN (
            SELECT listing_id, MAX(scraped_at) as max_scraped
            FROM snapshots
            GROUP BY listing_id
        ) latest ON s.listing_id = latest.listing_id AND s.scraped_at = latest.max_scraped
        WHERE price_value IS NOT NULL
        GROUP BY location
        ORDER BY avg_price DESC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def get_price_per_sqm_by_district(conn: sqlite3.Connection) -> List[dict]:
    """Get average price per sqm by district/location."""
    cursor = conn.execute(
        """
        SELECT 
            location,
            AVG(price_per_sqm) as avg_price_per_sqm,
            COUNT(*) as count
        FROM snapshots s
        JOIN (
            SELECT listing_id, MAX(scraped_at) as max_scraped
            FROM snapshots
            GROUP BY listing_id
        ) latest ON s.listing_id = latest.listing_id AND s.scraped_at = latest.max_scraped
        WHERE price_per_sqm IS NOT NULL
        GROUP BY location
        ORDER BY avg_price_per_sqm DESC
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def get_overall_price_stats(conn: sqlite3.Connection) -> dict:
    """Get overall price statistics: median, average, avg price per sqm."""
    # Get all prices for median calculation
    cursor = conn.execute(
        """
        SELECT price_value, price_per_sqm
        FROM snapshots s
        JOIN (
            SELECT listing_id, MAX(scraped_at) as max_scraped
            FROM snapshots
            GROUP BY listing_id
        ) latest ON s.listing_id = latest.listing_id AND s.scraped_at = latest.max_scraped
        WHERE price_value IS NOT NULL
        ORDER BY price_value
        """
    )
    rows = cursor.fetchall()
    
    if not rows:
        return {
            "median_price": 0,
            "avg_price": 0,
            "avg_price_per_sqm": 0,
            "count": 0,
        }
    
    prices = [row["price_value"] for row in rows]
    price_per_sqms = [row["price_per_sqm"] for row in rows if row["price_per_sqm"]]
    
    # Calculate median
    n = len(prices)
    if n % 2 == 0:
        median = (prices[n//2 - 1] + prices[n//2]) / 2
    else:
        median = prices[n//2]
    
    # Calculate averages
    avg_price = sum(prices) / len(prices)
    avg_price_per_sqm = sum(price_per_sqms) / len(price_per_sqms) if price_per_sqms else 0
    
    return {
        "median_price": round(median),
        "avg_price": round(avg_price),
        "avg_price_per_sqm": round(avg_price_per_sqm),
        "count": n,
    }


def get_all_listings_with_latest_snapshot(conn: sqlite3.Connection) -> List[dict]:
    """Get all listings with their most recent snapshot data."""
    cursor = conn.execute(
        """
        SELECT 
            l.id,
            l.ad_id,
            l.url,
            l.first_seen_at,
            ls.status,
            ls.closed_at,
            s.title,
            s.price,
            s.price_value,
            s.location,
            s.rooms,
            s.size_sqm,
            s.size_sqm_value,
            s.price_per_sqm,
            s.scraped_at
        FROM listings l
        JOIN listing_status ls ON l.id = ls.listing_id
        LEFT JOIN snapshots s ON l.id = s.listing_id
        LEFT JOIN (
            SELECT listing_id, MAX(scraped_at) as max_scraped
            FROM snapshots
            GROUP BY listing_id
        ) latest ON s.listing_id = latest.listing_id AND s.scraped_at = latest.max_scraped
        WHERE s.id IS NOT NULL OR latest.listing_id IS NULL
        ORDER BY s.scraped_at DESC NULLS LAST
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def get_recent_scrape_runs(conn: sqlite3.Connection, limit: int = 10) -> List[dict]:
    """Get recent scrape runs."""
    cursor = conn.execute(
        """
        SELECT * FROM scrape_runs 
        ORDER BY started_at DESC 
        LIMIT ?
        """,
        (limit,)
    )
    return [dict(row) for row in cursor.fetchall()]

"""
FastAPI Dashboard for Vienna Apartment Price Tracker.

Run with: uvicorn src.app:app --reload
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import (
    init_db,
    get_connection,
    get_listing_count_by_status,
    get_price_stats_over_time,
    get_price_by_district,
    get_price_per_sqm_by_district,
    get_overall_price_stats,
    get_all_listings_with_latest_snapshot,
    get_recent_scrape_runs,
)

app = FastAPI(title="Vienna Apartment Price Tracker")

# Templates
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    with get_connection() as conn:
        status_counts = get_listing_count_by_status(conn)
        price_over_time = get_price_stats_over_time(conn)
        price_by_district = get_price_by_district(conn)
        price_per_sqm_by_district = get_price_per_sqm_by_district(conn)
        price_stats = get_overall_price_stats(conn)
        recent_runs = get_recent_scrape_runs(conn, limit=5)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "status_counts": status_counts,
            "price_over_time_json": json.dumps(price_over_time, default=str),
            "price_by_district_json": json.dumps(price_by_district, default=str),
            "price_per_sqm_by_district_json": json.dumps(price_per_sqm_by_district, default=str),
            "recent_runs": recent_runs,
            "total_open": status_counts.get("open", 0),
            "total_closed": status_counts.get("closed", 0),
            "median_price": price_stats["median_price"],
            "avg_price": price_stats["avg_price"],
            "avg_price_per_sqm": price_stats["avg_price_per_sqm"],
        }
    )


@app.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request):
    """Listings table page."""
    with get_connection() as conn:
        listings = get_all_listings_with_latest_snapshot(conn)
    
    return templates.TemplateResponse(
        "listings.html",
        {
            "request": request,
            "listings": listings,
        }
    )


@app.get("/api/stats")
async def api_stats():
    """API endpoint for dashboard stats."""
    with get_connection() as conn:
        return {
            "status_counts": get_listing_count_by_status(conn),
            "price_over_time": get_price_stats_over_time(conn),
            "price_by_district": get_price_by_district(conn),
            "recent_runs": get_recent_scrape_runs(conn, limit=10),
        }


@app.get("/api/listings")
async def api_listings():
    """API endpoint for all listings."""
    with get_connection() as conn:
        return get_all_listings_with_latest_snapshot(conn)

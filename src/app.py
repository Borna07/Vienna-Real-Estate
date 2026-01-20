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
    get_price_distribution_simple,
    get_best_value_listings,
    get_best_value_by_district,
    get_market_trends,
    get_listing_price_history,
    get_listing_details,
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
        price_distribution = get_price_distribution_simple(conn)
        best_value_listings = get_best_value_listings(conn, limit=10)
        best_by_district = get_best_value_by_district(conn)
        market_trends = get_market_trends(conn)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "status_counts": status_counts,
            "price_over_time_json": json.dumps(price_over_time, default=str),
            "price_by_district_json": json.dumps(price_by_district, default=str),
            "price_per_sqm_by_district_json": json.dumps(price_per_sqm_by_district, default=str),
            "price_distribution_json": json.dumps(price_distribution, default=str),
            "recent_runs": recent_runs,
            "total_open": status_counts.get("open", 0),
            "total_closed": status_counts.get("closed", 0),
            "median_price": price_stats["median_price"],
            "avg_price": price_stats["avg_price"],
            "avg_price_per_sqm": price_stats["avg_price_per_sqm"],
            "best_value_listings": best_value_listings,
            "best_by_district": best_by_district,
            "market_trends": market_trends,
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


@app.get("/listing/{listing_id}", response_class=HTMLResponse)
async def listing_detail(request: Request, listing_id: int):
    """Listing detail page with price history."""
    with get_connection() as conn:
        listing = get_listing_details(conn, listing_id)
        price_history = get_listing_price_history(conn, listing_id)
    
    if not listing:
        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "Listing not found"},
            status_code=404
        )
    
    return templates.TemplateResponse(
        "listing_detail.html",
        {
            "request": request,
            "listing": listing,
            "price_history_json": json.dumps(price_history, default=str),
        }
    )


@app.get("/api/listing/{listing_id}/history")
async def api_listing_history(listing_id: int):
    """API endpoint for listing price history."""
    with get_connection() as conn:
        return get_listing_price_history(conn, listing_id)

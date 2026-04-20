"""
FastAPI Dashboard for Vienna Apartment Price Tracker.

Run with: uvicorn src.app:app --reload
"""

import json
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .db import (
    MARKET_RENT,
    MARKET_SALE,
    init_db,
    get_connection,
    get_listing_count_by_status,
    get_price_stats_over_time,
    get_price_by_district,
    get_price_per_sqm_by_district,
    get_listing_count_by_district,
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

TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

MarketQuery = Literal["sale", "rent"]


def _normalize_market(value: Optional[str]) -> str:
    if value == "rent":
        return MARKET_RENT
    return MARKET_SALE


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()


def _histogram_bucket(market: str) -> int:
    return 200 if market == MARKET_RENT else 50_000


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard (sale / Eigentum)."""
    market = MARKET_SALE
    is_rent = False
    with get_connection() as conn:
        status_counts = get_listing_count_by_status(conn, market)
        price_over_time = get_price_stats_over_time(conn, market)
        price_by_district = get_price_by_district(conn, market)
        price_per_sqm_by_district = get_price_per_sqm_by_district(conn, market)
        listing_count_by_district = get_listing_count_by_district(conn, market)
        price_stats = get_overall_price_stats(conn, market)
        recent_runs = get_recent_scrape_runs(conn, limit=5, market=market)
        price_distribution = get_price_distribution_simple(
            conn, bucket_size=_histogram_bucket(market), market=market
        )
        best_value_listings = get_best_value_listings(conn, limit=10, market=market)
        best_by_district = get_best_value_by_district(conn, market)
        market_trends = get_market_trends(conn, market)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "is_rent": is_rent,
            "market": market,
            "status_counts": status_counts,
            "price_over_time_json": json.dumps(price_over_time, default=str),
            "price_by_district_json": json.dumps(price_by_district, default=str),
            "price_per_sqm_by_district_json": json.dumps(
                price_per_sqm_by_district, default=str
            ),
            "listing_count_by_district_json": json.dumps(
                listing_count_by_district, default=str
            ),
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
        },
    )


@app.get("/rent", response_class=HTMLResponse)
async def dashboard_rent(request: Request):
    """Rental (Mietwohnungen) dashboard."""
    market = MARKET_RENT
    is_rent = True
    with get_connection() as conn:
        status_counts = get_listing_count_by_status(conn, market)
        price_over_time = get_price_stats_over_time(conn, market)
        price_by_district = get_price_by_district(conn, market)
        price_per_sqm_by_district = get_price_per_sqm_by_district(conn, market)
        listing_count_by_district = get_listing_count_by_district(conn, market)
        price_stats = get_overall_price_stats(conn, market)
        recent_runs = get_recent_scrape_runs(conn, limit=5, market=market)
        price_distribution = get_price_distribution_simple(
            conn, bucket_size=_histogram_bucket(market), market=market
        )
        best_value_listings = get_best_value_listings(conn, limit=10, market=market)
        best_by_district = get_best_value_by_district(conn, market)
        market_trends = get_market_trends(conn, market)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "is_rent": is_rent,
            "market": market,
            "status_counts": status_counts,
            "price_over_time_json": json.dumps(price_over_time, default=str),
            "price_by_district_json": json.dumps(price_by_district, default=str),
            "price_per_sqm_by_district_json": json.dumps(
                price_per_sqm_by_district, default=str
            ),
            "listing_count_by_district_json": json.dumps(
                listing_count_by_district, default=str
            ),
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
        },
    )


@app.get("/listings", response_class=HTMLResponse)
async def listings_page(request: Request):
    """Listings table (sale)."""
    market = MARKET_SALE
    with get_connection() as conn:
        listings = get_all_listings_with_latest_snapshot(conn, market)

    return templates.TemplateResponse(
        "listings.html",
        {
            "request": request,
            "listings": listings,
            "is_rent": False,
            "market": market,
        },
    )


@app.get("/rent/listings", response_class=HTMLResponse)
async def listings_rent_page(request: Request):
    """Listings table (rent)."""
    market = MARKET_RENT
    with get_connection() as conn:
        listings = get_all_listings_with_latest_snapshot(conn, market)

    return templates.TemplateResponse(
        "listings.html",
        {
            "request": request,
            "listings": listings,
            "is_rent": True,
            "market": market,
        },
    )


@app.get("/api/stats")
async def api_stats(market: MarketQuery = Query(default="sale")):
    """API endpoint for dashboard stats."""
    m = _normalize_market(market)
    with get_connection() as conn:
        return {
            "market": m,
            "status_counts": get_listing_count_by_status(conn, m),
            "price_over_time": get_price_stats_over_time(conn, m),
            "price_by_district": get_price_by_district(conn, m),
            "listing_count_by_district": get_listing_count_by_district(conn, m),
            "recent_runs": get_recent_scrape_runs(conn, limit=10, market=m),
        }


@app.get("/api/listings")
async def api_listings(market: MarketQuery = Query(default="sale")):
    """API endpoint for all listings in a market segment."""
    m = _normalize_market(market)
    with get_connection() as conn:
        return get_all_listings_with_latest_snapshot(conn, m)


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
            status_code=404,
        )

    is_rent = listing.get("market") == MARKET_RENT
    listings_back_href = "/rent/listings" if is_rent else "/listings"

    return templates.TemplateResponse(
        "listing_detail.html",
        {
            "request": request,
            "listing": listing,
            "price_history_json": json.dumps(price_history, default=str),
            "is_rent": is_rent,
            "listings_back_href": listings_back_href,
        },
    )


@app.get("/api/listing/{listing_id}/history")
async def api_listing_history(listing_id: int):
    """API endpoint for listing price history."""
    with get_connection() as conn:
        return get_listing_price_history(conn, listing_id)

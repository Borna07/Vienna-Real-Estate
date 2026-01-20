# CLAUDE.md - Project Context for AI Assistants

## Project Overview

Vienna Apartment Price Tracker - A web application that scrapes Willhaben.at apartment listings in Vienna, stores them in a database, and provides a dashboard for price tracking and analysis.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Scraping**: Playwright (headless browser)
- **Database**: SQLite (local), designed for easy migration to PostgreSQL
- **Frontend**: Jinja2 templates, Tailwind CSS, Plotly.js charts
- **Scheduling**: Windows Task Scheduler / Unix cron

## Project Structure

```
├── src/
│   ├── app.py          # FastAPI application with dashboard routes
│   ├── config.py       # Configuration from .env
│   ├── db.py           # SQLite database layer and queries
│   ├── scraper.py      # Willhaben scraper using Playwright
│   └── templates/      # Jinja2 HTML templates
├── scripts/
│   ├── scrape.py       # Scheduled scraper entrypoint
│   ├── schedule_windows.bat
│   └── schedule_unix.sh
├── data/               # SQLite database (gitignored)
├── logs/               # Scrape logs (gitignored)
├── myenv/              # Python virtual environment (gitignored)
└── config.example.env  # Example configuration
```

## Key Commands

```bash
# Activate virtual environment
source myenv/Scripts/activate  # Windows Git Bash
source myenv/bin/activate      # Linux/macOS

# Run the dashboard
uvicorn src.app:app --host 127.0.0.1 --port 8080

# Run a manual scrape
python -m scripts.scrape

# Install dependencies
pip install -r requirements.txt
python -m playwright install
```

## Database Schema

- **listings**: Immutable ad identity (ad_id, url, first_seen_at)
- **snapshots**: Point-in-time data (price, location, rooms, size, price_per_sqm)
- **listing_status**: Open/closed state with closed_at timestamp
- **scrape_runs**: Log of each scrape run

## Scraping Logic

1. Uses Playwright to load Willhaben search results
2. Extracts data from `window.__NEXT_DATA__` (Next.js SSR data)
3. Paginates through all results automatically
4. Calculates price_per_sqm from price_value / size_sqm_value

## Configuration

Copy `config.example.env` to `.env`:
- `DATABASE_URL`: SQLite path
- `SCRAPE_URL`: Willhaben search URL with filters
- `SCRAPE_INTERVAL_DAYS`: How often to scrape (default: 3)

## Scheduling

The scraper is designed to run every 3 days. Scheduling is NOT automatically set up - it requires manual configuration:

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task → Trigger: Daily, repeat every 3 days
3. Action: Start Program → `scripts/schedule_windows.bat`

### Linux/macOS Cron
```cron
0 6 */3 * * /path/to/project/scripts/schedule_unix.sh
```

## Important Notes

- The `myenv/` directory must stay in the project root (per user preference)
- URLs are built using base `https://www.willhaben.at/iad/` + SEO path
- Price values are stored as integers (cents removed)
- The dashboard auto-initializes the database on startup

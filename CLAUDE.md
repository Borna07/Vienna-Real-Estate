# CLAUDE.md - Project Context for AI Assistants

## Current State

Vienna Apartment Price Tracker is a FastAPI web app that scrapes Willhaben.at apartment listings in Vienna, stores them in a database, and provides a dashboard for price tracking and analysis.

### Dashboard Features

- Median price, average price, and average EUR per sqm cards
- Market trends card (avg price change, avg EUR per sqm change, listing count change)
- Price distribution histogram (EUR buckets)
- Average EUR per sqm by district chart
- Average price over time chart
- Best value listings table (lowest EUR per sqm)
- Best deal per district cards
- Recent scrape runs table
- Listing detail page with price history chart and snapshot table

## Tech Stack

- **Backend**: Python 3.11+, FastAPI
- **Scraping**: Playwright (headless browser), Next.js data extraction
- **Database**: SQLite (local), designed for migration to PostgreSQL
- **Frontend**: Jinja2 templates, Tailwind CSS, Plotly.js charts
- **Scheduling**: Windows Task Scheduler or cron/systemd on Linux

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

# Run the dashboard (local)
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
- `DATABASE_URL`: SQLite path (or PostgreSQL URI when migrating)
- `SCRAPE_URL`: Willhaben search URL with filters
- `SCRAPE_INTERVAL_DAYS`: How often to scrape (default: 3)

## Scheduling (Local)

The scraper is designed to run every 3 days. Scheduling is NOT automatically set up.

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task → Trigger: Daily, repeat every 3 days
3. Action: Start Program → `scripts/schedule_windows.bat`

### Linux/macOS Cron
```cron
0 6 */3 * * /path/to/project/scripts/schedule_unix.sh
```

## Next Steps: VPS Deployment

1. **Provision VPS**
   - Ubuntu 22.04 or similar
   - Open ports 22 (SSH) and 80/443 (HTTP/HTTPS)

2. **Install system dependencies**
   - Python 3.11+, build tools, and Playwright system deps
   - Example: `sudo apt-get install -y python3.11 python3.11-venv python3-pip`
   - Then: `python -m playwright install` and `python -m playwright install-deps`

3. **Clone repo and set up environment**
   - `git clone` the repository
   - Create `.env` from `config.example.env`
   - Set `SCRAPE_URL` for desired districts and filters
   - Keep `DATABASE_URL` as SQLite or switch to PostgreSQL

4. **Database choice**
   - **SQLite**: simplest, stored on disk
   - **PostgreSQL**: recommended for reliability and concurrency
   - Update `DATABASE_URL` if using PostgreSQL

5. **Run the app with a process manager**
   - Use `gunicorn` with `uvicorn` workers or systemd service
   - Bind to `0.0.0.0:8000`

6. **Reverse proxy**
   - Use Nginx to proxy to the FastAPI app
   - Add TLS with Let's Encrypt (Certbot)

7. **Schedule scraping**
   - Prefer `systemd` timer or cron
   - Run `python -m scripts.scrape` every 3 days

8. **Logging and monitoring**
   - Ensure `logs/` exists and is writable
   - Optional: add log rotation and basic uptime monitoring

## Important Notes

- The `myenv/` directory must stay in the project root (per user preference)
- URLs are built using base `https://www.willhaben.at/iad/` + SEO path
- Price values are stored as integers (cents removed)
- The dashboard auto-initializes the database on startup

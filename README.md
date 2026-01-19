# Vienna Apartment Price Tracker

A web application to track apartment prices in Vienna by scraping Willhaben listings every 3 days, storing them in a database, and visualizing price trends on a dashboard.

## Features

- **Automated Scraping**: Scrapes Willhaben apartment listings from a pre-filtered URL
- **Price Tracking**: Stores snapshots of listings with timestamps to track price changes
- **Open/Closed Status**: Automatically marks listings as closed when they disappear
- **Dashboard**: Interactive web dashboard with price charts and statistics
- **Listings Table**: Searchable/filterable table of all tracked apartments

## Project Structure

```
├── src/
│   ├── app.py          # FastAPI dashboard application
│   ├── config.py       # Configuration management
│   ├── db.py           # Database layer (SQLite)
│   ├── scraper.py      # Willhaben scraper module
│   └── templates/      # HTML templates for dashboard
├── scripts/
│   ├── scrape.py       # Scheduled scraper entrypoint
│   ├── schedule_windows.bat  # Windows Task Scheduler script
│   └── schedule_unix.sh      # Unix/Linux cron script
├── data/               # SQLite database storage
├── logs/               # Scrape run logs
├── myenv/              # Python virtual environment
├── config.example.env  # Example configuration file
└── requirements.txt    # Python dependencies
```

## Installation

### 1. Clone and Setup

```bash
cd "D:/03 Python/24 Web Crawler"

# Create virtual environment (if not exists)
python -m venv myenv

# Activate virtual environment
# Windows:
myenv\Scripts\activate
# Unix/Linux:
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install
```

### 2. Configuration

Copy the example config file and adjust as needed:

```bash
cp config.example.env .env
```

Edit `.env` to customize:
- `DATABASE_URL`: Path to SQLite database
- `SCRAPE_URL`: Willhaben search URL with your filters
- `SCRAPE_INTERVAL_DAYS`: How often to scrape (default: 3)

### 3. Initialize Database

The database is automatically created on first scrape or when starting the dashboard.

## Usage

### Run the Scraper Manually

```bash
python -m scripts.scrape
```

This will:
1. Scrape all listings from the configured URL
2. Store/update listings in the database
3. Mark missing listings as closed
4. Log results to `logs/scrape.log`

### Start the Dashboard

```bash
uvicorn src.app:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 in your browser.

### Schedule Automatic Scraping

#### Windows Task Scheduler

1. Open Task Scheduler
2. Create a new task
3. Set trigger: Every 3 days
4. Set action: Run `scripts\schedule_windows.bat`

#### Linux/macOS Cron

Add to crontab (`crontab -e`):

```cron
# Run every 3 days at 6:00 AM
0 6 */3 * * /path/to/project/scripts/schedule_unix.sh >> /path/to/project/logs/cron.log 2>&1
```

## Dashboard Pages

### Main Dashboard (`/`)
- Open/Closed/Total listing counts
- Average price over time chart
- Average price by district chart
- Recent scrape runs log

### Listings (`/listings`)
- Full table of all tracked apartments
- Search by title/location
- Filter by open/closed status
- Direct links to Willhaben listings

## API Endpoints

- `GET /api/stats` - Dashboard statistics
- `GET /api/listings` - All listings with latest snapshot data

## VPS Migration

When ready to deploy to a VPS:

1. **Database**: Consider switching to PostgreSQL by changing `DATABASE_URL`
2. **Config**: Use environment variables instead of `.env` file
3. **Scheduler**: Use systemd timer or cron
4. **Optional**: Add `Dockerfile` and `docker-compose.yml` for containerized deployment

## Requirements

- Python 3.10+
- Playwright (for browser automation)
- FastAPI (for web dashboard)
- SQLite (database)

## License

MIT

@echo off
REM Windows Task Scheduler batch script for Vienna Apartment Price Tracker
REM Schedule this script to run every 3 days via Task Scheduler

cd /d "%~dp0.."
call myenv\Scripts\activate.bat
python -m scripts.scrape

if %ERRORLEVEL% NEQ 0 (
    echo Scrape failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Scrape completed successfully

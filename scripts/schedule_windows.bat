@echo off
REM Windows Task Scheduler batch script for Vienna Apartment Price Tracker
REM Schedule this script to run every 3 days via Task Scheduler

cd /d "%~dp0.."
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format ''yyyy-MM-dd''"') do set "RUN_DATE=%%i"
set "LOG_DIR=logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\schedule_%RUN_DATE%.log"

echo [%DATE% %TIME%] Starting scheduled scrape >> "%LOG_FILE%"

call myenv\Scripts\activate.bat >> "%LOG_FILE%" 2>&1
python -m scripts.scrape >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo Scrape failed with error code %ERRORLEVEL% >> "%LOG_FILE%"
    exit /b %ERRORLEVEL%
)

echo Scrape completed successfully >> "%LOG_FILE%"

REM Git add/commit/push the database changes
if exist "data\*.db" (
    git add data\*.db >> "%LOG_FILE%" 2>&1
) else (
    echo No database file found to commit >> "%LOG_FILE%"
)

git diff --cached --quiet >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo No changes to commit >> "%LOG_FILE%"
    exit /b 0
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format ''yyyy-MM-dd HH:mm''"') do set "SCRAPE_TS=%%i"

git commit -m "Scrape run %SCRAPE_TS%" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Git commit failed with error code %ERRORLEVEL% >> "%LOG_FILE%"
    exit /b %ERRORLEVEL%
)

git push >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Git push failed with error code %ERRORLEVEL% >> "%LOG_FILE%"
    exit /b %ERRORLEVEL%
)

echo Git push completed successfully >> "%LOG_FILE%"
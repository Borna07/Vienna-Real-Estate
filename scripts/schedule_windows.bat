@echo off
setlocal EnableExtensions
REM Windows Task Scheduler batch script for Vienna Apartment Price Tracker
REM Schedule this script to run every 3 days via Task Scheduler
REM Optional arg %1: sale | rent | all (default all if omitted). Pass via Task Scheduler "Add arguments".

cd /d "%~dp0.." || exit /b 1

set "SCRAPE_MARKET=%~1"
if "%SCRAPE_MARKET%"=="" set "SCRAPE_MARKET=all"

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd'"') do set "RUN_DATE=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"') do set "RUN_TS=%%i"

set "LOG_DIR=logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\schedule_%RUN_DATE%.log"

call :log "Starting scheduled scrape"
call :log "Market: %SCRAPE_MARKET%"
call :log "Working dir: %CD%"

REM Activate virtual environment if present
if exist "myenv\Scripts\activate.bat" (
    call :log "Activating virtual environment"
    call myenv\Scripts\activate.bat >> "%LOG_FILE%" 2>&1
) else (
    call :log "Virtual environment not found at myenv\Scripts\activate.bat"
)

REM Run scraper
python -m scripts.scrape --market %SCRAPE_MARKET% >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    call :log "Scrape failed with error code %ERRORLEVEL%"
    exit /b %ERRORLEVEL%
)
call :log "Scrape completed successfully"

REM Git add/commit/push the database changes
if exist "data\*.db" (
    git add data\*.db >> "%LOG_FILE%" 2>&1
) else (
    call :log "No database file found to commit"
)

git diff --cached --quiet >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% EQU 0 (
    call :log "No changes to commit"
    exit /b 0
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"') do set "SCRAPE_TS=%%i"
git commit -m "Scrape run %SCRAPE_TS%" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    call :log "Git commit failed with error code %ERRORLEVEL%"
    exit /b %ERRORLEVEL%
)

git push >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    call :log "Git push failed with error code %ERRORLEVEL%"
    exit /b %ERRORLEVEL%
)

call :log "Git push completed successfully"
exit /b 0

:log
set "MSG=%~1"
echo [%RUN_TS%] %MSG% >> "%LOG_FILE%"
exit /b 0
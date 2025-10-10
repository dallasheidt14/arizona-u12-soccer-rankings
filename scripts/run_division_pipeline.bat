@echo off
REM scripts/run_division_pipeline.bat
REM Purpose: Run complete pipeline for a single division (Step 1-4)
REM Usage: scripts\run_division_pipeline.bat az_boys_u10

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: scripts\run_division_pipeline.bat ^<division^>
    echo Example: scripts\run_division_pipeline.bat az_boys_u10
    exit /b 1
)

set DIVISION=%1
echo.
echo ========================================
echo Running Pipeline for: %DIVISION%
echo ========================================
echo.

REM Step 1: Scrape team list
echo [1/4] Scraping team list -^> bronze/
python scrapers\scraper_multi_division.py --division %DIVISION% --mode teams
if errorlevel 1 (
    echo ERROR: Step 1 failed
    exit /b 1
)

REM Step 2: Scrape match histories
echo.
echo [2/4] Scraping match histories -^> gold/
python scrapers\scrape_team_history.py --division %DIVISION%
if errorlevel 1 (
    echo ERROR: Step 2 failed
    exit /b 1
)

REM Extract uppercase division for file paths (e.g., az_boys_u10 -> AZ_BOYS_U10)
for /f "delims=" %%i in ('powershell -command "'%DIVISION%'.ToUpper()"') do set DIV_UP=%%i

REM Step 3: Validate gold output
echo.
echo [3/4] Validating gold layer
python -m utils.validate_gold gold\Matched_Games_%DIV_UP%.csv
if errorlevel 1 (
    echo ERROR: Validation failed
    exit /b 1
)

REM Step 4: Generate rankings (convert az_boys_u10 -> AZ_Boys_U10)
echo.
echo [4/4] Generating rankings -^> rankings/

REM Convert division format: az_boys_u10 -> AZ_Boys_U10
for /f "tokens=1-3 delims=_" %%a in ("%DIVISION%") do (
    set STATE=%%a
    set GENDER=%%b
    set AGE=%%c
)

REM Capitalize first letter of each part
for /f "delims=" %%i in ('powershell -command "'!STATE!'.Substring(0,1).ToUpper() + '!STATE!'.Substring(1)"') do set STATE_CAP=%%i
for /f "delims=" %%i in ('powershell -command "'!GENDER!'.Substring(0,1).ToUpper() + '!GENDER!'.Substring(1)"') do set GENDER_CAP=%%i
for /f "delims=" %%i in ('powershell -command "'!AGE!'.ToUpper()"') do set AGE_UP=%%i

set DIV_ARG=!STATE_CAP!_!GENDER_CAP!_!AGE_UP!

python rankings\generate_team_rankings_v53_enhanced_multi.py --division %DIV_ARG%
if errorlevel 1 (
    echo ERROR: Ranking generation failed
    exit /b 1
)

echo.
echo ========================================
echo ✅ Pipeline complete for %DIVISION%
echo ========================================
echo.
echo Output files:
echo   - bronze\%DIVISION%_teams.csv
echo   - gold\Matched_Games_%DIV_UP%.csv
echo   - rankings\Rankings_AZ_M_%AGE%_2025_v53e.csv
echo.

endlocal


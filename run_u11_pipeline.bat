@echo off
cd /d "%~dp0"
echo ========================================
echo 🏆 U11 Division Data Pipeline
echo ========================================
echo.

echo Step 1: Scraping U11 teams and games...
python scraper_multi_division.py --division az_boys_u11
if %errorlevel% neq 0 (
    echo ❌ Scraping failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Generating U11 rankings...
python rankings/generate_team_rankings_v53_enhanced_multi.py --division AZ_Boys_U11
if %errorlevel% neq 0 (
    echo ❌ Ranking generation failed!
    pause
    exit /b 1
)

echo.
echo ✅ U11 division pipeline completed successfully!
echo 📁 Output files:
echo   - Rankings_AZ_M_U11_2025_v53e.csv
echo   - connectivity_report_u11_v53e.csv
echo   - AZ MALE U11 MASTER TEAM LIST.csv
echo.
echo 🌐 Test API: http://localhost:8000/api/rankings?division=az_boys_u11
echo.
pause

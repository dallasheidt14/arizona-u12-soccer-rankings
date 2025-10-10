@echo off
cd /d "%~dp0"
echo Starting Youth Soccer Rankings System with Multi-Division Support...

echo.
echo ========================================
echo 🏆 Multi-Division Soccer Rankings System
echo ========================================
echo.

echo Starting FastAPI backend...
start "FastAPI Backend" cmd /k "python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload"

echo Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak > nul

echo Starting React frontend...
start "React Frontend" cmd /k "npm run dev"

echo.
echo ✅ Both services are starting!
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📊 API Docs: http://localhost:8000/docs
echo.
echo Available Divisions:
echo   - Arizona Boys U12 (2014): /api/rankings?division=az_boys_u12
echo   - Arizona Boys U11 (2015): /api/rankings?division=az_boys_u11
echo.
echo Press any key to exit this window...
pause > nul

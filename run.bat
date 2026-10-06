@echo off
echo ============================================
echo  NEURA — Starting Backend & Frontend
echo ============================================

echo.
echo [1/2] Starting Backend on port 8000...
start "NEURA Backend" cmd /c "cd /d %~dp0backend && venv\Scripts\activate.bat && python run.py"

timeout /t 3 /nobreak >nul

echo.
echo [2/2] Starting Frontend on port 5500...
start "NEURA Frontend" cmd /c "cd /d %~dp0 && python -m http.server 5500 --bind 127.0.0.1"

echo.
echo ============================================
echo  Done! Open in browser:
echo    Backend:  http://127.0.0.1:8000
echo    Frontend: http://127.0.0.1:5500/index.html
echo    Swagger:  http://127.0.0.1:8000/api/v1/docs
echo ============================================

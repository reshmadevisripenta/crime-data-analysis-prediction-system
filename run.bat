@echo off
REM =========================================================================
REM  Crime Data Analysis & Prediction System - Start Server
REM =========================================================================
cd /d "%~dp0"
call venv\Scripts\activate
echo Starting Django Development Server on http://127.0.0.1:8000/ ...
echo Press Ctrl+C to stop the server.
python manage.py runserver 0.0.0.0:8000
pause

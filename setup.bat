@echo off
REM =========================================================================
REM  Crime Data Analysis & Prediction System - Automated Setup Script (Windows)
REM =========================================================================

echo [1/8] Checking Python environment...
python --version
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH. Please install Python 3.10+.
    pause
    exit /b 1
)

echo.
echo [2/8] Creating virtual environment (venv)...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/8] Activating virtual environment...
call venv\Scripts\activate

echo.
echo [4/8] Installing project dependencies from requirements.txt...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [5/8] Checking configuration and .env file...
if not exist ".env" (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Note: Created default .env. Please update DB credentials if necessary.
) else (
    echo .env file found.
)

echo.
echo [6/8] Running database migrations...
python manage.py makemigrations accounts core dashboard crime_data analysis location_analysis patterns ontology model_training prediction visualization reports notifications
python manage.py migrate
if errorlevel 1 (
    echo Migration warning: Ensure MySQL service is running and 'crimedb' database exists.
    echo SQL Command: CREATE DATABASE IF NOT EXISTS crimedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    pause
)

echo.
echo [7/8] Superuser creation prompt...
set /p CREATE_SUPER="Would you like to create an admin superuser now? (y/n): "
if /i "%CREATE_SUPER%"=="y" (
    python manage.py createsuperuser
)

echo.
echo [8/8] Optional: Seed initial demo data...
set /p SEED_DATA="Would you like to seed initial crime data and ontology? (y/n): "
if /i "%SEED_DATA%"=="y" (
    python manage.py seed_data
)

echo.
echo =========================================================================
echo Setup Completed Successfully! Starting Django Development Server...
echo Visit: http://127.0.0.1:8000/
echo =========================================================================
python manage.py runserver

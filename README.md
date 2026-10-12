# Crime Data Analysis & Prediction System

An end-to-end intelligent crime analytics platform built with **Django 4.2**, **MySQL**, **Scikit-Learn**, **Folium / Leaflet.js**, **Chart.js**, and **RDFLib (Ontology Reasoning)**.

---

## 📋 Features Overview

- **Role-Based Access Control (RBAC)**: Custom user model with roles (`admin`, `officer`, `analyst`, `viewer`).
- **Crime Data Ingestion & Management**: Excel/CSV bulk import, automated validation, cleaning, and preprocessing.
- **Statistical Crime Analysis**: Trend aggregation, time-of-day breakdowns, seasonal decomposition, and demographic profiling.
- **Geospatial & Hotspot Mapping**: Interactive maps with Leaflet/Folium, heatmap density layers, and high-risk zone boundaries.
- **Crime Pattern Mining**: Apriori association rule mining, modus operandi (MO) similarity detection, and recurring sequence detection.
- **Ontology & Semantic Reasoning**: RDF/OWL crime knowledge graphs, relationship traversal, and semantic inference with RDFLib.
- **Machine Learning & Prediction**: Classification and regression models (Random Forest, Gradient Boosting) for crime type forecasting, risk scores, and repeat offense likelihood.
- **Data Visualization Suite**: Executive dashboards featuring Chart.js and D3.js interactive graphs.
- **Automated Reporting**: Export comprehensive PDF summary reports with ReportLab and formatted Excel spreadsheets with openpyxl.
- **Alerts & Notifications**: Automated email notifications and incident alert feeds.

---

## ⚙️ System Requirements & Prerequisites

1. **Python 3.10+** (64-bit recommended)
2. **MySQL Server 8.0+**
3. **C++ Build Tools for Python** (required if compiling `mysqlclient` wheels on Windows)

---

## 🗄️ MySQL Database Setup

Before running migrations or starting the web server, create the MySQL database:

```sql
CREATE DATABASE IF NOT EXISTS crimedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Verify your credentials match your configuration (default user is `root` with password `root`).

---

## 🚀 Quick Start (Automated Script)

On Windows systems, simply double click or run `setup.bat`:

```bat
setup.bat
```

The script performs the following tasks:
1. Validates Python 3.10+
2. Creates virtual environment `venv`
3. Installs all dependencies from `requirements.txt`
4. Generates `.env` from `.env.example` if not already present
5. Runs Django database migrations
6. Prompts to create an administrator superuser
7. Prompts to seed initial demo data
8. Boots the development web server on `http://127.0.0.1:8000/`

---

## 🐳 Docker Deployment (Recommended for Instant Setup)

If you have **Docker Desktop** installed, you can spin up the entire application stack (Django + MySQL 8 + Gunicorn) in a single command with zero manual configuration:

```bash
docker compose up --build
```

- **Web App**: Accessible on [http://localhost:8000/](http://localhost:8000/)
- **MySQL Container**: Accessible externally on port `3307`
- Automated migrations, static asset collection, and database seeding are performed automatically on startup.
- Stop the containers anytime with:
```bash
docker compose down
```

---

## 🛠️ Manual Installation Guide

### 1. Clone or Open Workspace
```bash
cd "c:\Users\reshm\OneDrive\Desktop\crime data analysis prediction system"
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS / Linux
```

### 3. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Update database connection parameters inside `.env` to match your local MySQL settings:
```env
SECRET_KEY=django-insecure-crime-analysis-prediction-system-key-2024-secure!
DEBUG=True
DB_NAME=crimedb
DB_USER=root
DB_PASSWORD=root
DB_HOST=localhost
DB_PORT=3306
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
```

### 5. Run Database Migrations
```bash
python manage.py makemigrations accounts core dashboard crime_data analysis location_analysis patterns ontology model_training prediction visualization reports notifications
python manage.py migrate
```

### 6. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 7. Run Server
```bash
python manage.py runserver
```
Access the system in your browser at `http://127.0.0.1:8000/`.

---

## 📁 Project Architecture & Structure

```text
├── config/                  # Core project settings and URL router
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                    # Landing page, layout base templates & error handlers
├── accounts/                # Custom User model, RBAC, authentication & profile views
├── dashboard/               # Executive overview KPIs and activity feed
├── crime_data/              # Incident management, batch CSV/Excel import & validation
├── analysis/                # Statistical metrics, crime rates, time & day aggregations
├── location_analysis/       # Geospatial mapping, Leaflet heatmap overlays & clustering
├── patterns/                # Modus operandi matching, association rule mining
├── ontology/                # RDF/OWL knowledge representation & semantic query engine
├── model_training/          # ML pipeline orchestrator, model hyperparameter tuning
├── prediction/              # Real-time incident risk assessment & classification
├── visualization/           # Interactive Chart.js charts & comparative timelines
├── reports/                 # PDF (ReportLab) & Excel report generators
├── notifications/           # System alerts, threshold events & notification dispatch
├── static/                  # Shared CSS, JavaScript, vendor libraries & images
├── templates/               # Global templates (base.html, navbar, footer)
├── manage.py                # Django CLI entrypoint
├── requirements.txt         # Pinned python packages
├── setup.bat                # One-click Windows setup batch script
└── README.md                # System documentation
```

---

## 🎨 Design System & Theme Specifications

- **Primary Navy**: `#071B3A`
- **Secondary Navy**: `#102B52`
- **Primary Blue**: `#1769FF`
- **Accent Cyan**: `#20D5F5`
- **Background**: `#F4F7FC`
- **Card Background**: `#FFFFFF`
- **Text Color**: `#1C2940`
- **Frontend Stack**: Bootstrap 5, Bootstrap Icons, Chart.js, Leaflet.js, D3.js

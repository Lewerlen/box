# Muay Thai Tournament Management

## Overview
Web application for managing Muay Thai tournaments in Bashkortostan. Consists of a FastAPI backend, React+Vite frontend, and an existing Telegram bot (separate process).

## Architecture
- **Backend**: FastAPI (Python) on port 8000
- **Frontend**: React + Vite + Tailwind CSS on port 5000 (proxies /api to backend)
- **Database**: PostgreSQL (shared with Telegram bot)
- **Telegram Bot**: aiogram bot in `main.py` (runs separately)

## Project Structure
```
api/                    # FastAPI backend
  main.py              # App entry, CORS, router registration
  auth.py              # JWT auth helpers
  routers/
    auth_router.py     # POST /api/auth/login, GET /api/auth/me
    public.py          # Public endpoints (participants, brackets, refs, stats)
    registration.py    # Multi-step registration wizard API
    admin.py           # Admin CRUD, CSV import, Excel downloads, brackets
    admin_references.py # Admin reference data CRUD + merge (regions, cities, clubs, coaches)
    competitions.py    # Public + admin CRUD for competitions (/api/competitions)
    schedule.py        # Rings CRUD + fight schedule (admin) and public schedule view
frontend/              # React + Vite frontend
  src/
    api.ts             # Axios client with JWT interceptors
    App.tsx            # Route definitions
    components/Layout.tsx  # Nav, footer, admin detection
    pages/
      HomePage.tsx         # Competition listing (active/past), discipline badges
      CompetitionPage.tsx  # Competition detail page (/competition/:id)
      ParticipantsPage.tsx # Public participant list with filters
      BracketsPage.tsx     # Public approved brackets viewer
      SchedulePage.tsx     # Public fight schedule by day/ring
      RegistrationPage.tsx # Multi-step registration form (11 steps)
      LoginPage.tsx        # Admin login
    pages/admin/
      AdminDashboard.tsx   # Admin overview, Excel downloads
      AdminCompetitions.tsx # Competition CRUD (/admin/competitions)
      AdminParticipants.tsx # Admin CRUD, CSV import
      AdminBrackets.tsx    # Bracket management (swap, approve, regenerate)
      AdminReferences.tsx  # Reference data management (hierarchical CRUD + merge)
      AdminSchedule.tsx    # Schedule builder: rings + drag-and-drop fight assignment
db/                    # Database layer (psycopg2, sync)
  database.py          # All DB functions (includes competitions table)
  init_db.py           # Schema creation and reference data seeding
  cache.py             # In-memory cache for reference data
utils/
  draw_bracket.py      # Tournament bracket PNG generation
  excel_generator.py   # Excel report generation
fonts/                 # DejaVuSans.ttf for bracket images
```

## Key Configuration
- **Admin auth**: `ADMIN_USERNAME` (default: "admin"), `ADMIN_PASSWORD` (default: "admin123"), `ADMIN_PASSWORD_HASH`, `JWT_SECRET_KEY`
- **DB**: `DATABASE_URL` environment variable
- **Workflows**: "Backend API" (port 8000, console), "Start application" (port 5000, webview)

## Tech Stack
- Python: FastAPI, uvicorn, python-jose, passlib, psycopg2, openpyxl, Pillow
- Frontend: React 19, Vite 8, TypeScript, Tailwind CSS 4, React Router 7, Axios, Lucide React
- Language: Russian (all UI text)

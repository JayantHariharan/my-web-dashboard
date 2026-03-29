# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Tasks

### Running Locally

**Frontend Only (Recommended for UI work):**
```bash
cd my-web-dashboard/frontend/src
python -m http.server 3000
```
Then open http://localhost:3000

**Full Stack (Backend + Frontend):**
```bash
cd my-web-dashboard
python backend/main.py
```
The FastAPI server serves static files from the `frontend/src/` directory and provides authentication API endpoints at `/api/login` and `/api/signup`. Access at http://localhost:8000.

### Testing

**Run Visual Smoke Test:**
```bash
cd my-web-dashboard
export SITE_URL="your-live-site-url"
npm install playwright
npx playwright install chromium --with-deps
node tests/smoke.test.js
```
This launches a real browser, navigates to the site, takes a screenshot, and verifies "PlayNexus" appears on the page.

## Code Architecture

### High-Level Overview

PlayNexus is a web dashboard/gaming hub with:
- **Frontend:** Pure HTML/CSS/JavaScript (no build step, no framework)
- **Backend:** Python FastAPI (serves static files + auth API)
- **Database:** SQLite (local) / MySQL / PostgreSQL (production - depends on configuration)
- **Deployment:** Render (all-in-one: frontend + backend together)

### Key Components

**1. Static File Structure (my-web-dashboard/frontend/src/)**
- `index.html` - Main entry point with authentication portal and hub interface
- `css/` - Stylesheets (`style.css`, `crystal-portal.css`, `crystal-hub.css`)
- `js/` - Client-side logic:
  - `cinematic-startup.js` - Canvas-based particle background with Matter.js physics
  - `main.js` - Core PlayNexus logic, physics engine management, card interactions
  - `session.js` - Session recovery, intro screen handling, HUD updates
  - `splash.js` - Splash screen animations
- `assets/` - Images and icons
- `games/`, `news/`, `community/`, `author/` - Feature sections (standalone HTML pages)

**2. Backend API (backend/main.py)**
- FastAPI app mounted to serve static files from `frontend/src/` (path computed relative to script location)
- Authentication endpoints:
  - `POST /api/login` - Validates credentials against `users` table
  - `POST /api/signup` - Creates new user with password confirmation
- **Database:** Currently uses SQLite (local). For production (Render), update `get_db()` to use PostgreSQL (psycopg2) or MySQL (pymysql) based on `DATABASE_URL` environment variable
- Database table `users` created on startup
- No server-side session management (frontend uses `sessionStorage`)

**3. Visual Effects & Physics**
- Matter.js library loaded from CDN
- `cinematic-startup.js` creates particle system on canvas with antigravity physics
- `main.js` enables card physics in the hub (floating, bouncing cards)
- Gravity toggle feature integrated into HUD

**4. Deployment & CI/CD**

**Render Auto-Deploy (Current):**
- Service automatically deploys on every GitHub push
- Configured once in Render dashboard
- Build command: `pip install -r backend/requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Python version: 3.12 (specified in `runtime.txt` and `pyproject.toml`)

**Legacy GitHub Actions:** (removed - was for ProFreeHost FTP deployment)

### Branch Workflow

```
main        ← production (every push triggers live deploy)
  └─ develop  ← integration branch (safe to experiment)
       └─ feature/initial_setup  ← active feature work
```

### Important Notes

- **Render deployment** - Single service hosts both frontend and backend. Start command must be `uvicorn backend.main:app` (not `main:app`) because `main.py` is in `backend/` folder.
- **Database flexibility** - Local development uses SQLite (`sqlite3`). Production (Render) should use PostgreSQL (`psycopg2-binary`) or MySQL (`pymysql`). Update `get_db()` in `backend/main.py` accordingly and set `DATABASE_URL` or `DB_*` environment variables.
- **Session-based auth** - Frontend currently stores username in `sessionStorage`. The authentication UI exists but is bypassed via session recovery (no real API calls yet). To enable real auth, update `frontend/src/js/session.js` to call `/api/login` and `/api/signup`.
- **Python version** - Render uses Python 3.12.9 (specified in `runtime.txt` and `pyproject.toml`). This avoids `pydantic-core` build errors.
- **Ephemeral filesystem** - Render's filesystem resets on each deploy. Use external database, not local SQLite files, for persistence.
- **Environment variables** - Configure in Render dashboard: `DATABASE_URL` (or `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`). Also `FRONTEND_DIR` path is computed automatically.

### File Conventions

- HTML files: 2-space indentation
- CSS uses custom properties (CSS variables) for theme colors
- JavaScript uses ES6+ syntax with module pattern (PlayNexus object)
- Client-side auth flow bypassed via `sessionStorage` for demo purposes
- Database queries use parameterized queries (`?` placeholders) to prevent SQL injection

### File Conventions

- HTML files: 2-space indentation
- CSS uses custom properties (CSS variables) for theme colors
- JavaScript uses ES6+ syntax with module pattern (PlayNexus object)
- Client-side auth flow bypassed via `sessionStorage` for demo purposes

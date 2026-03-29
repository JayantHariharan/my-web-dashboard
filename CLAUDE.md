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
- **Database:** SQLite (user authentication only)
- **Deployment:** FTP to FreeHost via GitHub Actions

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
  - `POST /api/login` - Validates credentials against SQLite `users` table
  - `POST /api/signup` - Creates new user with password confirmation
- Uses `sessionStorage` on frontend; no server-side session management
- Database is initialized on startup with `users` table

**3. Visual Effects & Physics**
- Matter.js library loaded from CDN
- `cinematic-startup.js` creates particle system on canvas with antigravity physics
- `main.js` enables card physics in the hub (floating, bouncing cards)
- Gravity toggle feature integrated into HUD

**4. CI/CD Pipeline (.github/workflows/main.yml)**
- Triggers on push to `main`, `develop`, or `feature/**` branches
- Three jobs:
  1. `validate` - Checks required files exist in `frontend/src/`
  2. `deploy` - Runs only on `main`; FTP deploys `frontend/src/` to production server
  3. `smoke-test` - Runs after deploy; uses Playwright to verify live site and capture screenshot

### Branch Workflow

```
main        ← production (every push triggers live deploy)
  └─ develop  ← integration branch (safe to experiment)
       └─ feature/initial_setup  ← active feature work
```

### Important Notes

- **No npm/node workflow** - Only Python for local dev; Playwright used only in CI for smoke tests
- **Session-based auth** - Client stores username in `sessionStorage`; backend authentication is currently unused in frontend (index.html has auth UI but bypasses it with session recovery)
- **Static deployment** - All HTML is pre-built; FTP deployment copies `frontend/src/` folder only
- **Sensitive data** - FTP credentials stored in GitHub Secrets; SITE_URL used for smoke test

### File Conventions

- HTML files: 2-space indentation
- CSS uses custom properties (CSS variables) for theme colors
- JavaScript uses ES6+ syntax with module pattern (PlayNexus object)
- Client-side auth flow bypassed via `sessionStorage` for demo purposes

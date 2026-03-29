# Render Deployment - Complete Setup Guide

## Quick Start

Everything you need to deploy PlayNexus to Render (frontend + backend in one service).

---

## 📋 Checklist

- [ ] Push code to GitHub (done)
- [ ] Create Render Web Service
- [ ] Configure Render Service Settings
- [ ] Clear Build Cache and Deploy
- [ ] Fix: Change Start Command to `uvicorn backend.main:app`
- [ ] Create/Connect Database
- [ ] Update Database Code in `backend/main.py`
- [ ] Set Database Environment Variables
- [ ] Test Live App

---

## Step 1: Create Render Web Service

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account
4. Select repo: `my-web-dashboard`
5. Branch: `feature/initial_setup` (or `main`)

---

## Step 2: Configure Service Settings

**Basic Info:**
- **Name:** `playnexus`
- **Environment:** `Python 3`
- **Region:** Choose closest

**Build & Deploy:**
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** ❌ WRONG - `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Correct Start Command:** ✅ `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory:** Leave **EMPTY**

**Environment Variables:**
Add these:
```
DATABASE_URL = (add later after creating database)
```

---

## Step 3: Fix Start Command (IMPORTANT!)

**Your current start command is WRONG for the folder structure.**

### Change in Render Dashboard:

1. Go to your service → **Settings**
2. Find **"Start Command"** field
3. Change from:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   To:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
4. Save

**Why?** Because your `main.py` is in `backend/` folder, not root.

---

## Step 4: Clear Cache and Deploy

1. Go to your service → **Manual Deploy**
2. Select **"Clear cache and deploy"**
3. Wait 3-5 minutes

**Watch the logs:**
- Should see Python 3.12.x being installed
- Dependencies install without Rust errors
- Success message: "Build succeeded"

---

## Step 5: Create Database

**Option A: Render PostgreSQL (Recommended)**
1. Render Dashboard → **"New +"** → **"PostgreSQL"**
2. Name: `playnexus-db`
3. Region: Same as web service
4. Free Tier: 90 days free
5. Wait 1 minute
6. Copy **External Database URL** from PostgreSQL service "Connection" tab
7. Add to Web Service Environment Variables:
   ```
   DATABASE_URL = [paste connection string]
   ```

**Option B: FreeHost MySQL (External)**
1. Enable external connections in FreeHost panel
2. Get MySQL credentials (host, user, password, database)
3. Either:
   - Set single `DATABASE_URL` = `mysql://user:pass@host:port/dbname`
   - Or set separate: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

---

## Step 6: Update `backend/main.py` Database Code

**⚠️ MUST UPDATE before authentication will work.**

Current code uses SQLite. Update `get_db()` function:

### For Render PostgreSQL:

```python
import psycopg2
import os
from psycopg2.extras import RealDictCursor

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL not set")
    conn = psycopg2.connect(db_url)
    conn.cursor_factory = RealDictCursor
    return conn
```

Add `psycopg2-binary` to `backend/requirements.txt`.

### For MySQL:

```python
import pymysql
import os

def get_db():
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASSWORD")
    db_name = os.environ.get("DB_NAME")

    if not all([db_host, db_user, db_pass, db_name]):
        raise Exception("Database environment variables not set")

    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection
```

Add `pymysql` to `backend/requirements.txt`.

---

## Step 7: Push Database Code Update

```bash
git add backend/main.py backend/requirements.txt
git commit -m "Update database connection for production"
git push origin feature/initial_setup
```

Render will auto-deploy.

---

## Step 8: Test Your App

1. Visit your Render URL: `https://playnexus.onrender.com`
2. Try **Sign Up** → should create user in database
3. Try **Login** → should authenticate
4. Check Render logs if errors occur

---

## Step 9: Add Custom Domain (Optional)

1. Render → Web Service → **Settings** → **Custom Domains**
2. Click **"Add Custom Domain"**
3. Enter your domain (from FreeHost)
4. Copy DNS records
5. Add to FreeHost DNS settings
6. Wait for propagation

---

## Troubleshooting

### "Could not import module 'main'"
**Fix:** Change start command to `uvicorn backend.main:app`

### "pydantic-core" or Rust errors
**Fix:** `runtime.txt` specifies Python 3.12. Clear cache and redeploy.

### Database connection error
**Fix:** Ensure `DATABASE_URL` or `DB_*` env vars set correctly. Test connection string locally first.

### 404 on static files
**Fix:** Ensure `frontend/src/index.html` exists in GitHub repo. Check that `FRONTEND_DIR` path is correct.

---

## Files Overview

```
my-web-dashboard/
├── backend/
│   ├── main.py              # FastAPI app (serves frontend + API)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── src/                 # All HTML/CSS/JS files
├── runtime.txt              # Python 3.12.9 for Render
├── pyproject.toml           # Python version constraint
├── README.md                # Project overview
├── RENDER_DEPLOYMENT.md     # Detailed deployment guide (legacy)
└── DEPLOYMENT.md            # This file - quick reference
```

---

## Summary

✅ **Single Render service** - frontend + backend together
✅ **Free subdomain** - `https://playnexus.onrender.com`
✅ **Auto-deploy** from GitHub pushes
✅ **External database** - Render PostgreSQL or FreeHost MySQL

**Critical:** Start command must be `uvicorn backend.main:app` (not `main:app`)

---

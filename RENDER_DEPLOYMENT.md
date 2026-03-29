# Render Deployment Guide - All-in-One (Frontend + Backend)

## Quick Start

Deploy your entire PlayNexus app (frontend + backend) to Render in 10 minutes.

---

## What You'll Get

- ✅ **Single service** - FastAPI serves both static files and API
- ✅ **Free subdomain** - `https://your-service.onrender.com`
- ✅ **Automatic HTTPS** - SSL certificate included
- ✅ **GitHub auto-deploy** - Push to GitHub → Render updates automatically
- ✅ **Free tier** - $0/month (with sleep after 15 min inactivity)

---

## Important: Database Setup Required

Your backend code uses `get_db()` with `sqlite3.connect()`. This only works with **SQLite file paths**, not MySQL/PostgreSQL connection strings.

**You MUST update the database code before deploying** if using:
- MySQL (FreeHost)
- PostgreSQL (Render/Supabase)
- Any external database

See Step 2 below.

---

## Step 1: Commit and Push Your Changes

Make sure all your changes are committed and pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin feature/initial_setup
```

---

## Step 2: Update Database Code (CRITICAL)

The current `backend/main.py` uses SQLite. You need to change `get_db()` for your database type.

### Option A: MySQL (FreeHost externally)

Add to `backend/requirements.txt`:
```
pymysql==1.1.1
```

Update `backend/main.py`:

```python
import pymysql
import os

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Parse mysql://user:pass@host:port/dbname
        # Or use direct connection parameters from separate env vars
        connection = pymysql.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    else:
        # Fallback to hardcoded local (for dev only)
        return sqlite3.connect("local.db")
```

Set these environment variables in Render.

### Option B: PostgreSQL (Render/Supabase)

Add to `backend/requirements.txt`:
```
psycopg2-binary==2.9.10
```

Update `backend/main.py`:

```python
import psycopg2
import os
from psycopg2.extras import RealDictCursor

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to local SQLite for dev
        return sqlite3.connect("local.db")
    conn = psycopg2.connect(db_url)
    conn.cursor_factory = RealDictCursor
    return conn
```

Also update SQL queries if needed (PostgreSQL uses `RETURNING` instead of `lastrowid` for inserts).

### Option C: Keep SQLite (Not recommended for Render)

SQLite stores data in a file. On Render's ephemeral filesystem:
- Data is **lost** on every restart/deploy
- Only use for testing, not production

---

## Step 3: Create Render Web Service

## Prerequisites
- GitHub repository with your code pushed
- Render account (free)

---

## Step-by-Step Instructions

### Step 1: Commit and Push Your Changes

Make sure all your changes are committed and pushed to GitHub:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin feature/initial_setup
```

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** (top right button)
3. Select **"Web Service"**

---

### Step 4: Configure Render Service

Fill in these settings:

**Basic Info:**
- **Name:** `playnexus` (or your preferred name)
- **Environment:** `Python 3`
- **Region:** Select closest to your location

**Build & Deploy:**
- **Branch:** `feature/initial_setup` (or your working branch)
- **Build Command:**
  ```bash
  pip install -r backend/requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

**Advanced Settings:**

- **Root Directory:** *Leave empty* (Render runs from repository root)
  - Your `backend/main.py` uses `os.path` to correctly locate `frontend/src/`

- **Environment Variables:** Click "Add Environment Variable"
  ```
  DATABASE_URL = your-database-connection-string
  ```
  (Click "Add Another" for more variables if using separate DB credentials)

  **Examples:**
  - FreeHost MySQL: `mysql://username:password@host:3306/database`
  - Render PostgreSQL: (auto-provided, no need to add manually)
  - Supabase: `postgresql://postgres:[password]@[host]:5432/[database]`

**Free Instance Type:** Automatically selected (no cost)

---

### Step 5: Create the Service

Click **"Create Web Service"**

Render will:
1. Clone your GitHub repository
2. Install Python dependencies from `backend/requirements.txt`
3. Start your FastAPI server with uvicorn
4. Give you a live URL: `https://playnexus.onrender.com`

---

### Step 6: Wait for Deployment

- First deployment takes **3-5 minutes**
- Watch the build logs in Render dashboard
- Status changes: **"Building"** → **"Launching"** → **"Live"** (green)

---

### Step 7: Test Your Live App

1. Click your service URL in Render
2. Should see the PlayNexus frontend
3. Test login/signup (verify database connectivity)

If you see the frontend but API calls fail:
- Check Render logs for database errors
- Verify `DATABASE_URL` is correct
- Ensure database allows connections from Render's IPs

---

### Step 8: (Optional) Add Custom Domain

You can use your FreeHost domain later:

1. Render Dashboard → Your Service → **Settings**
2. Scroll to **Custom Domains**
3. Click **"Add Custom Domain"**
4. Enter your domain (e.g., `yourdomain.com`)
5. Render shows DNS records to configure

**At FreeHost DNS panel:**
- Add CNAME: `yourdomain.com` → `your-service.onrender.com`
- Or add A records if Render provides them
- Wait 5-30 minutes for DNS propagation

**Note:** Your FreeHost domain must point to Render. You cannot "transfer" a domain to Render (Render doesn't sell domains). You just point it.

---

## Free Tier Details

- **Sleep:** Service sleeps after 15 minutes of no requests
- **Wake-up:** First request takes 30-60 seconds (cold start)
- **Hours:** 100 hours/month free (enough for testing)
- **RAM:** 512 MB
- **Storage:** Ephemeral (resets on deploy) - always use external DB

---

## Database Setup Guide

### If Using Render PostgreSQL (Easiest)

1. In Render Dashboard: **New +** → **PostgreSQL**
2. Name: `playnexus-db`
3. Free tier: 90 days free, then $7/month
4. Copy the **Connection String** (External Database URL)
5. In your Web Service → Environment Variables → Add:
   ```
   DATABASE_URL = [paste connection string]
   ```
6. Update `backend/main.py` to use `psycopg2` (see Step 2)

### If Using FreeHost MySQL

1. In FreeHost panel, enable external connections (if needed)
2. Get MySQL connection details:
   - Host (e.g., `mysql.freefhost.com`)
   - Port (usually `3306`)
   - Database name
   - Username & password
3. In Render → Web Service → Environment Variables:
   ```
   DB_HOST = your-mysql-host
   DB_USER = your-username
   DB_PASSWORD = your-password
   DB_NAME = your-database
   ```
4. Update `backend/main.py` accordingly (see Step 2)

---

## Troubleshooting

### "Module not found: pymysql/psycopg2"
→ Add the package to `backend/requirements.txt` and redeploy.

### "Database connection refused"
- Check `DATABASE_URL` or DB_* env vars are set correctly
- Verify database allows external connections from Render
- Test connection string locally first

### "Cannot find frontend/src/"
- Your repository structure must be:
  ```
  repo/
  ├── backend/main.py
  └── frontend/src/index.html
  ```
- Render runs from repo root; `main.py` computes `frontend/src/` correctly

### 404 on static files
- Ensure `frontend/src/` exists in GitHub with all files
- Check build logs for permission errors
- Verify `index.html` is present

### Slow first request (30+ seconds)
- Normal behavior: free tier sleeps after 15 min inactivity
- Consider upgrading to paid plan ($7/month) to avoid sleep

---

## Need Help?

- **Render Docs:** https://render.com/docs
- **FastAPI on Render:** https://render.com/docs/deploy-fastapi
- **Community:** https://render.com/community

---

## Summary

✅ Everything in one Render service (frontend + backend)
✅ Free subdomain for testing
✅ External database (FreeHost MySQL or Render PostgreSQL)
✅ Environment variables for configuration
✅ Git auto-deploy from GitHub

**Ready?** Follow Steps 1-7 and your app will be live!

# Render Deployment Guide

## Overview
Deploy your PlayNexus backend (FastAPI) to Render with free tier. Frontend static files are served from the same service.

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

### Step 2: Create a New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** (top right)
3. Select **"Web Service"**

### Step 3: Configure Your Web Service

Fill in the following:

**Basic Info:**
- **Name:** `playnexus-backend` (or any name you prefer)
- **Environment:** `Python 3`
- **Region:** Choose closest to you (e.g., Oregon, Singapore)

**Build & Deploy:**
- **Branch:** `feature/initial_setup` (or your main branch)
- **Build Command:**
  ```bash
  pip install -r backend/requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

**Advanced (Optional but Recommended):**
- Scroll down to **"Advanced"** section
- **Environment Variables:** Add these:
  - `DATABASE_URL` = `https://api.freefhost.com/v1/databases`
  - (If you have a custom domain later, add `ALLOWED_ORIGINS`)

**Important:**
- **Root Directory:** Leave empty (Render runs from repo root)
- Your `backend/main.py` uses `os.path` to find `frontend/src/` relative to its location, so it will work.

### Step 4: Create Service

Click **"Create Web Service"**

Render will:
1. Clone your GitHub repo
2. Install dependencies from `backend/requirements.txt`
3. Start the server with uvicorn
4. Give you a URL like: `https://playnexus-backend.onrender.com`

### Step 5: Wait for Deployment

First deployment takes 3-5 minutes. Watch the logs in Render dashboard.

When it says **"Service deployed successfully"**, your API is live!

### Step 6: Test Your API

Open: `https://your-backend.onrender.com/api/login` (POST test)
Or visit: `https://your-backend.onrender.com` (should show your frontend)

### Step 7: Update Your Frontend (if needed)

If you keep frontend on Render (same domain), no changes needed.

If you want to:
- **Keep ProFreeHost** for frontend: Update `frontend/src/js/session.js` to point API calls to your Render backend URL
- **Move frontend to Render**: Already done! The FastAPI app serves `frontend/src/` as static files

### Step 8: Update FreeHost (Optional)

If you move frontend to Render:
1. Point your domain's DNS to Render (optional, use Render URL for now)
2. Or just use the Render URL directly

---

## Important Notes

### Free Tier Limitations
- Service **sleeps after 15 minutes of inactivity**
- First request after sleep takes 30-60 seconds (cold start)
- 512 MB RAM limit
- 100 hours/month runtime

### Database
Your current setup uses `https://api.freefhost.com/v1/databases` which is an external MySQL service. This will work if:
1. The URL is publicly accessible
2. Render can connect to it (outbound connections allowed)

If you have issues, consider:
- Using Render's PostgreSQL (free)
- Or switching to a local SQLite file (but not recommended for multi-instance)

### Custom Domain (Future)
To use `yourdomain.com` instead of `*.onrender.com`:
1. Add custom domain in Render dashboard
2. Update DNS records
3. Service is still free

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'fastapi'"**
→ Build command is wrong. It should be `pip install -r backend/requirements.txt`

**"Cannot find frontend/src/"**
→ Make sure your directory structure is correct. Render runs from repo root.

**404 on static files**
→ Check that `frontend/src/index.html` exists in your repo
→ Check build logs for errors

**Database connection failed**
→ Verify `DATABASE_URL` is set correctly in Render environment variables

---

## Need Help?
- Render Docs: https://render.com/docs
- FastAPI on Render: https://render.com/docs/deploy-fastapi

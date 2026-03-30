# Render Deployment Troubleshooting Guide

## Quick Diagnostic

Run this command locally to check if your Render API credentials work:

```bash
# Set these from your GitHub secrets
export RENDER_API_KEY="your-api-key-here"
export RENDER_SERVICE_ID_TEST="srv-xxxxxxxxxxxxxxxxx"

# Test API access
curl -s -w "\nHTTP:%{http_code}\n" \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID_TEST" | jq .
```

Expected: HTTP 200 with service details in JSON.

---

## Common Issues & Solutions

### 1. Auto-Deploy Still Enabled ⚠️
**Symptom:** Workflow runs but Render doesn't show deployment progress.

**Check:** Go to Render Dashboard → Service → Settings → **Auto-Deploy**
- **Must be:** Disabled/Manual
- If enabled: Render cancels API-triggered deployments

**Fix:** Toggle to **Manual** and save.

---

### 2. Wrong Service ID 🔴
**Symptom:** Service verification step fails (HTTP 404).

**Check:**
- Service ID format: `srv-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (24 chars)
- Not the service name or URL
- From Render Dashboard: Click service → Copy **Service ID**

**Fix:** Update GitHub secret with correct Service ID:
- `RENDER_SERVICE_ID_TEST` (for staging)
- `RENDER_SERVICE_ID_PROD` (for production)

---

### 3. API Key Access Denied 🔴
**Symptom:** Service verification fails (HTTP 401 or 403).

**Cause:** API key doesn't have access to the service.
- Render API key is account-level, but services might be in a different account
- API key might be from a different Render account

**Check:**
```bash
# Test with your API key
curl -s -H "Authorization: Bearer YOUR_KEY" \
  "https://api.render.com/v1/services/YOUR_SERVICE_ID" | jq .
```

Should return service details, not "Not found" or "Unauthorized".

**Fix:** Use an API key from the same Render account that owns the service.

**To get API key:**
- Render Dashboard → Account (top right) → **API Keys**
- Copy an existing key or create new
- Add to GitHub secrets: `RENDER_API_KEY`

---

### 4. Environment Group Misconfiguration 🟡
**Symptom:** "Environment group not found" or association step fails.

**Cause:** Environment group ID is optional, but if provided it must be correct.

**Check:**
- If you set `RENDER_ENV_GROUP_ID_TEST/PROD`, verify they exist
- From Render: Environment Groups → Copy ID (format: `evm-xxx`)

**Fix:**
- Either provide correct env group ID
- Or remove these secrets if not using Environment Groups

The workflow will skip association if the secret is empty.

---

### 5. Service is Suspended 🟡
**Symptom:** Verification succeeds (HTTP 200) but no deployment happens.

**Check:** Service state from verification response:
```
"State: suspended"
```

Render suspended services won't accept deployment triggers.

**Fix:** Unsuspend service in Render dashboard.

---

### 6. In-Progress Deploy Blocking 🟡
**Symptom:** "TIMEOUT: Previous deploy still in progress"

**Cause:** A deployment is already running (maybe auto-deploy triggered it).

**Check:** Render Dashboard → your service → Deployments tab
- Is there an ongoing deployment?
- If stuck, cancel it manually

**Fix:**
1. Disable Auto-Deploy to prevent this
2. Cancel any stuck deployments manually
3. Re-run workflow

---

### 7. GitHub Workflow Not Triggering 🔴
**Symptom:** Pushing to branch doesn't start workflow.

**Check:**
- Are you pushing to `develop` (staging) or `main` (production)?
- Workflow only triggers on push to these branches
- Go to GitHub → Actions tab → see if workflow runs appear

**Fix:**
```bash
git push origin develop   # for staging
git push origin main      # for production
```

Or manually trigger: GitHub → Actions → "Workflow Dispatch"

---

## How to Debug Your Current Issue

### Step 1: Check GitHub Actions Logs
1. Go to your GitHub repository
2. Click **Actions** tab
3. Click the latest workflow run
4. Scroll through each step and identify where it fails
   - ❌ Red = failed step
   - ✅ Green = passed step
   - ⏳ Yellow = skipped

**Look for these steps:**
- `quality` → must pass ✅
- `Verify Render service` → should show service details
- `Trigger Render deployment` → should show trigger response
- `Monitor deployment` → should show progress

**Copy any error messages** and share them.

---

### Step 2: Verify Secrets in GitHub

In GitHub: **Settings → Secrets and variables → Actions**

Check these secrets exist:
- ✅ `RENDER_API_KEY`
- ✅ `RENDER_SERVICE_ID_TEST`
- ✅ `RENDER_SERVICE_ID_PROD`
- Optional: `RENDER_ENV_GROUP_ID_TEST`, `RENDER_ENV_GROUP_ID_PROD`

**Test if they're correctly passed:**
The workflow logs will show truncated values. If they show as empty or masked incorrectly, that's the issue.

---

### Step 3: Run Local Diagnostics

```bash
# Copy the diagnostic scripts from scripts/ folder
cd scripts

# Bash (Git Bash, WSL, Linux, macOS):
chmod +x render-diagnostics.sh
./render-diagnostics.sh

# PowerShell (Windows):
.\render-diagnostics.ps1
```

This will test:
- All environment variables are set
- Render API is accessible
- Both services exist
- Auto-Deploy setting

---

### Step 4: Manual API Test

If workflow shows HTTP error codes, manually test the same API:

```bash
export RENDER_API_KEY="your-key"
export RENDER_SERVICE_ID="your-service-id"

# 1. Test service access
curl -v -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID" | jq .

# 2. Check current deployments
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID/deploys" | jq .

# 3. Test trigger (this will actually deploy!)
curl -v -X POST \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "https://api.render.com/v1/services/$RENDER_SERVICE_ID/deploys" | jq .
```

**Note:** Manual trigger will cause a deployment. Only do this if you want to test.

---

## Expected Workflow Output (Success)

### Verify Render service:
```
🔍 Verifying Render service exists and is accessible...
📨 Service verification response (HTTP 200):
{
  "service": {
    "name": "playnexus-test",
    "url": "playnexus-test.onrender.com",
    "state": "running"
  }
}
✅ Service verified:
   Name: playnexus-test
   URL: https://playnexus-test.onrender.com
   State: running
```

### Trigger Render deployment:
```
📤 Triggering new deployment...
📨 Trigger response (HTTP 201):
{
  "id": "deploy-xxxxxxxxxxxxx",
  "status": "created"
}
✅ Deployment triggered: deploy-xxxxxxxxxxxxx
```

### Monitor deployment:
```
⏳ Monitoring deployment progress...
Deploy ID: deploy-xxxxxxxxxxxxx

[00:00:01] Attempt 1/60 - Status: created
[00:00:31] Attempt 2/60 - Status: build_in_progress
   ➜ Building...
[00:01:01] Attempt 3/60 - Status: build_in_progress
...
[00:05:31] Attempt 11/60 - Status: live

✅ Deployment completed successfully!
🌐 Service URL: https://playnexus-test.onrender.com
```

---

## Quick Fixes Summary

| Problem | Check | Fix |
|---------|-------|-----|
| Auto-Deploy enabled | Render Settings | Disable Auto-Deploy (set to Manual) |
| Wrong Service ID | Service verification step | Copy correct ID from Render dashboard |
| API key invalid/expired | API test returns 401/403 | Generate new API key from Render account |
| Service suspended | State = "suspended" | Unsuspend service in dashboard |
| Workflow not triggering | Pushed to wrong branch | Push to `develop` or `main` |
| Env group error | Association step fails | Remove env group secrets or use correct ID |

---

## Need More Help?

1. **Share the GitHub Actions logs** (screenshot or copy error)
2. **Run diagnostic script** and share output
3. **Check Render dashboard** for any error notifications
4. **Verify service status** is "running" not "suspended"

---

**Most likely cause for "no deployment happening":**
1. ❌ **Auto-Deploy is still enabled** on Render → Disable it
2. ❌ **Service ID is wrong or inaccessible** → Verify with diagnostic script
3. ❌ **Workflow failing silently** → Check GitHub Actions logs for failed step

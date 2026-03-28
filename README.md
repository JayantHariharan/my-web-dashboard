# PlayNexus — Local Dev & Deployment Guide

## 🖥️ Testing Locally

### Option 1 — Python (Recommended, zero install needed)
Python ships with Windows. Open a terminal in the project folder and run:

```powershell
# Navigate to the project
cd C:\Projects\my-web-dashboard

# Start a local server on port 3000
python -m http.server 3000
```

Then open **http://localhost:3000** in your browser.  
Press `Ctrl+C` to stop the server.

> **Why not just open `index.html` directly?**  
> Double-clicking opens it as `file://` which can block fonts/scripts in some browsers. A local server is always the right way.

---

### Option 2 — VS Code Live Server (Auto-reload on save ✨)
1. Install the **Live Server** extension in VS Code
2. Right-click `index.html` → **Open with Live Server**
3. Your browser opens at `http://127.0.0.1:5500` and reloads every time you save a file

---

### Option 3 — npx serve (Node.js)
```powershell
npx serve . -p 3000
```

---

## 🌿 Branch Workflow

```
main        ← production (every push triggers live deploy)
  └─ develop  ← integration branch (safe to experiment)
       └─ feature/my-feature  ← day-to-day work
```

**Day-to-day flow:**
```powershell
# 1. Create a feature branch from develop
git checkout develop
git checkout -b feature/my-new-section

# 2. Make your changes, test locally at localhost:3000

# 3. Commit your work
git add -A
git commit -m "feat: add new section"

# 4. Push to GitHub
git push origin feature/my-new-section

# 5. Open a PR: feature → develop (review / test)

# 6. When ready to go live: merge develop → main
git checkout main
git merge develop
git push origin main
# ↑ This triggers GitHub Actions → FTP → live on playnexus.unaux.com 🚀
```

---

## 🔑 Setting Up GitHub Secrets (One-time)

1. Go to your repo: **https://github.com/JayantHariharan/my-web-dashboard**
2. Click **Settings → Secrets and variables → Actions**
3. Click **New repository secret** and add these 3 secrets:

| Secret Name    | Value (from ProFreeHost control panel) |
|----------------|----------------------------------------|
| `FTP_SERVER`   | e.g. `ftpupload.net`                   |
| `FTP_USERNAME` | e.g. `epiz_XXXXXXXX`                   |
| `FTP_PASSWORD` | Your hosting account password          |

> ⚠️ **Never** put these values in code or commit them. Only in GitHub Secrets.

---

## ✅ Pre-Deploy Checklist

- [ ] WordPress deleted from ProFreeHost `/htdocs/`
- [ ] 3 GitHub Secrets added (FTP_SERVER, FTP_USERNAME, FTP_PASSWORD)
- [ ] Tested locally at `localhost:3000` — looks good ✅
- [ ] Merged feature → develop → main
- [ ] Check **GitHub → Actions tab** for green checkmark ✅
- [ ] Visit **https://playnexus.unaux.com** 🎉

---

## 📁 Project Structure

```
my-web-dashboard/
├── index.html              ← Homepage
├── css/
│   └── style.css           ← All styles
├── js/
│   └── main.js             ← Interactions & animations
├── .github/
│   └── workflows/
│       └── deploy.yml      ← CI/CD pipeline
├── .gitignore
└── README.md
```

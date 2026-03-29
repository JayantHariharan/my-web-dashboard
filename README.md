# PlayNexus — Local Dev & Deployment Guide

## 🖥️ Testing Locally

### Option 1 — Python (Recommended)
Open a terminal **inside the `frontend/src/` folder** and run:

```powershell
cd C:\Projects\my-web-dashboard/frontend/src
python -m http.server 3000
```

Then open **http://localhost:3000** in your browser.

---

### Option 2 — VS Code Live Server
1. Install the **Live Server** extension.
2. Open `frontend/src/index.html`.
3. Right-click → **Open with Live Server**.

---

## 🌿 Branch Workflow

```
main        ← production (every push triggers live deploy)
  └─ develop  ← integration branch (safe to experiment)
       └─ feature/initial_setup  ← active feature work
```

---

## 📁 Project Structure

```
my-web-dashboard/
├── backend/                ← Python FastAPI server
│   ├── main.py             ← API endpoints + static file serving
│   └── requirements.txt    ← Python dependencies
├── frontend/               ← Frontend source code
│   └── src/                ← LIVE FILES (served to browser)
│       ├── index.html      ← Homepage
│       ├── css/            ← Stylesheets
│       ├── js/             ← Scripts
│       ├── assets/         ← Images & Icons
│       ├── games/          ← Games section
│       ├── news/           ← News section
│       ├── community/      ← Community section
│       └── author/         ← Author/Vault section
├── tests/                  ← Automated tests
│   └── smoke.test.js       ← Visual smoke test (Playwright)
├── .gitignore
├── CLAUDE.md               ← Claude Code guidance
├── DEPLOYMENT.md           ← Render deployment guide
├── pyproject.toml          ← Python version constraint
├── README.md
├── runtime.txt             ← Python 3.12.9 for Render
└── (other documentation files)
```

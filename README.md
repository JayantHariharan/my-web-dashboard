# PlayNexus — Local Dev & Deployment Guide

## 🖥️ Testing Locally

### Option 1 — Python (Recommended)
Open a terminal **inside the `src/` folder** and run:

```powershell
cd C:\Projects\my-web-dashboard/src
python -m http.server 3000
```

Then open **http://localhost:3000** in your browser.

---

### Option 2 — VS Code Live Server
1. Install the **Live Server** extension.
2. Open `src/index.html`.
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
├── src/                    ← LIVE FILES go here
│   ├── index.html          ← Homepage
│   ├── css/                ← Stylesheets
│   ├── js/                 ← Scripts
│   └── assets/             ← Images & Icons
├── .github/
│   └── workflows/
│       └── main.yml        ← Consolidated CI/CD
├── .gitignore
└── README.md
```

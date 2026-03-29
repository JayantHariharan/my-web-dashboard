from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3
import os
from typing import Optional

app = FastAPI()

# Serve static files from the frontend directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend", "src")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

# Database initialization - use environment variable for production
DATABASE_URL = os.environ.get("DATABASE_URL", "https://api.freefhost.com/v1/databases")

def get_db():
    db = sqlite3.connect(DATABASE_URL)
    db.row_factory = sqlite3.Row
    return db

# Create users table on startup
@app.on_event("startup")
async def startup():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    db.commit()
    db.close()

# Pydantic models
class LoginData(BaseModel):
    username: str
    password: str

class RegisterData(BaseModel):
    username: str
    password: str
    confirm_password: str

# Authentication endpoints
@app.post("/api/login")
async def login(login_data: LoginData):
    username = login_data.username.strip()
    password = login_data.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    db = get_db()
    db.row_factory = sqlite3.Row
    db.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = db.fetchone()
    db.close()

    if user and user["password"] == password:
        return {"message": "Login successful", "username": username}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/signup")
async def signup(register_data: RegisterData):
    username = register_data.username.strip()
    password = register_data.password.strip()
    confirm_password = register_data.confirm_password.strip()

    if not username or not password or not confirm_password:
        raise HTTPException(status_code=400, detail="All fields required")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    db = get_db()
    db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if db.fetchone() is not None:
        raise HTTPException(status_code=409, detail="Username already exists")

    db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    db.commit()
    db.close()

    return {"message": "Signup successful", "username": username}
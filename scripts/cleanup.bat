@echo off
REM Cleanup script for PlayNexus project (Windows)
REM This script cleans cache files and prepares for deployment

echo.
echo ============================================================
echo   PlayNexus Cleanup Script
echo ============================================================
echo.

cd /d "%~dp0.."
python scripts\cleanup.py

pause

@echo off
REM run.bat - Windows batch script to run Infinite Journal

echo Starting Infinite Journal...
cd /d "%~dp0"
python run.py
pause
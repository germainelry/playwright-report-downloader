@echo off
echo ============================================================
echo  Portal Automation - First Time Setup
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    echo Done.
) else (
    echo Virtual environment already exists. Skipping.
)

:: Activate and install dependencies
echo.
echo Installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo ============================================================
echo  Setup complete! You can now run downloader.bat.
echo ============================================================
pause
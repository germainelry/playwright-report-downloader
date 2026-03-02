@echo off
echo ============================================================
echo  Portal Report Downloader
echo ============================================================
echo.

:: Check venv exists — remind user to run setup first
if not exist ".venv" (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first before using this script.
    pause
    exit /b 1
)

:: Activate venv and run
call .venv\Scripts\activate.bat
python report_downloader.py %*

echo.
echo ============================================================
echo  Run complete. Press any key to close.
echo ============================================================
pause
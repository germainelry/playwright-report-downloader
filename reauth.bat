@echo off
echo ============================================================
echo  Portal - Re-authentication
echo ============================================================
echo.

:: Check venv exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first before using this script.
    pause
    exit /b 1
)

:: Activate venv and run
call .venv\Scripts\activate.bat
python authenticate.py

echo.
echo ============================================================
echo  Re-authentication complete. Press any key to close.
echo ============================================================
pause
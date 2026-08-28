@echo off
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -u quick_region_screenshot.py
) else (
    py -u quick_region_screenshot.py
)
echo.
echo (If there are errors, they will be shown above. Please copy and share them.)
pause

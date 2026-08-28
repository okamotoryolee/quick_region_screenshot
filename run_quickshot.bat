@echo off
cd /d "%~dp0"

rem Prefer the project-local virtual environment prepared for this PC.
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" /b "%~dp0.venv\Scripts\pythonw.exe" "%~dp0quick_region_screenshot.py"
) else (
    rem Fall back to the system Python launcher for a fresh checkout.
    start "" /b pyw.exe "%~dp0quick_region_screenshot.py"
)

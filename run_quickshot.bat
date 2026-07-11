@echo off
cd /d "%~dp0"

rem pythonw (pyw.exe) runs the app without attaching a console window.
rem start lets this batch file close immediately while QuickShot stays resident.
start "" /b pyw.exe "%~dp0quick_region_screenshot.py"

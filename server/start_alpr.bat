@echo off
REM Manual ALPR Startup Script
REM Double-click this file to start the ALPR server manually

echo Starting ALPR Integrated Server...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Run the PowerShell script
REM Change "basic" to "full" if you want VIN functionality
powershell.exe -ExecutionPolicy Bypass -File "server.ps1" run

echo.
echo Server has stopped. Press any key to exit...
pause

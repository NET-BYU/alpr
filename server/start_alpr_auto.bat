@echo off
REM ALPR Auto-Start Batch File
REM This file starts the ALPR server automatically on Windows boot

REM Change to the script directory
cd /d "%~dp0"

REM Log the startup attempt
echo [%date% %time%] ALPR Auto-start initiated >> autostart.log

REM Run the PowerShell script in auto mode
REM Change "basic" to "full" if you want VIN functionality enabled
powershell.exe -ExecutionPolicy Bypass -File "server.ps1" autorun >> autostart.log 2>&1

REM If we get here, the script has exited
echo [%date% %time%] ALPR Auto-start script exited >> autostart.log

pause

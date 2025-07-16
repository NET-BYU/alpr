@echo off
echo Installing ALPR Server Autorun...
echo.
echo This will configure the ALPR server to start automatically when Windows boots.
echo.
pause
echo.

PowerShell.exe -ExecutionPolicy Bypass -Command "& '%~dp0server.ps1' install-autorun"

echo.
echo Installation complete!
echo.
echo The ALPR server will now start automatically when Windows boots.
echo You can access the dashboard at: http://localhost:5000/dashboard
echo.
echo To manage the task, use Windows Task Scheduler: taskschd.msc
echo.
pause

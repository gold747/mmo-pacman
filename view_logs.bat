@echo off
echo Looking for MMO Pacman server log files...
echo.

:: Check if logs folder exists
if not exist "logs" (
    echo No logs folder found.
    echo Run the server first to generate logs.
    pause
    exit /b
)

:: Find the most recent log file in logs folder
for /f "delims=" %%i in ('dir /b /o-d logs\mmo_pacman_server_*.log 2^>nul') do (
    set "newest=logs\%%i"
    goto :found
)

:notfound
echo No log files found in logs folder.
echo Run the server first to generate logs.
pause
exit /b

:found
echo Most recent log file: %newest%
echo.
echo Choose an option:
echo 1) View entire log file
echo 2) View last 50 lines (tail)
echo 3) Follow log in real-time (like tail -f)
echo 4) Open log file in notepad
echo 5) List all log files
echo 6) Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    type "%newest%"
    pause
) else if "%choice%"=="2" (
    powershell -command "Get-Content '%newest%' | Select-Object -Last 50"
    pause
) else if "%choice%"=="3" (
    echo Press Ctrl+C to stop following the log...
    powershell -command "Get-Content '%newest%' -Wait -Tail 10"
) else if "%choice%"=="4" (
    notepad "%newest%"
) else if "%choice%"=="5" (
    echo All log files:
    dir logs\mmo_pacman_server_*.log /o-d
    pause
) else if "%choice%"=="6" (
    exit /b
) else (
    echo Invalid choice.
    pause
)

goto :found
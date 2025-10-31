@echo off
echo ================================================
echo MMO Pacman Multiplayer Bot Testing
echo ================================================
echo.
echo This will create automated bot clients to test multiplayer functionality
echo.

:menu
echo Choose testing option:
echo.
echo 1. Light test (5 bots for 30 seconds)
echo 2. Medium test (10 bots for 60 seconds)  
echo 3. Heavy test (20 bots for 120 seconds)
echo 4. Custom test
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo Starting light test...
    python test_multiplayer_bots.py --bots 5 --duration 30
    goto :menu
)

if "%choice%"=="2" (
    echo Starting medium test...
    python test_multiplayer_bots.py --bots 10 --duration 60
    goto :menu
)

if "%choice%"=="3" (
    echo Starting heavy test...
    python test_multiplayer_bots.py --bots 20 --duration 120
    goto :menu
)

if "%choice%"=="4" (
    set /p bots="Number of bots: "
    set /p duration="Duration in seconds: "
    echo Starting custom test with %bots% bots for %duration% seconds...
    python test_multiplayer_bots.py --bots %bots% --duration %duration%
    goto :menu
)

if "%choice%"=="5" (
    echo Goodbye!
    exit /b 0
)

echo Invalid choice. Please try again.
goto :menu
@echo off
echo Starting MMO Pacman Bot Simulation
echo ===================================
echo.
echo This will simulate 30 players connecting to your server
echo Make sure your server is running on localhost:5000
echo.
echo Press Ctrl+C to stop the simulation
echo.
pause
echo.
echo Starting bots...
C:\git\mmo-pacman\.venv\Scripts\python.exe test_bots.py --bots 30 --server http://localhost:5000
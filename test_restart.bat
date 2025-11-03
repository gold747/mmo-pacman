@echo off
echo Starting MMO Pacman Restart Test Harness...
echo.
echo This test will:
echo - Connect 5 test players to the game
echo - Run 3 complete game cycles (start -> play -> end -> restart)
echo - Verify all players remain connected through restarts
echo - Generate a detailed report
echo.
echo Make sure your MMO Pacman server is running first!
echo Server should be accessible at http://localhost:8080
echo.
pause

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo.
echo Running restart test harness...
python test_restart_harness.py --players 5 --cycles 3

echo.
echo Test completed! Check the log file for detailed results.
pause
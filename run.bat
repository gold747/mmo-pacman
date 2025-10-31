@echo off
echo Starting MMO Pacman Server...
echo.
echo Make sure you have Python installed with required packages:
echo pip install -r requirements.txt
echo.
echo Server will start on http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
echo IMPORTANT: Run this outside VS Code to avoid hangs!
echo Close VS Code or run this in a separate Command Prompt.
echo.


REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Run the server
python app.py
@echo off
echo Starting MMO Pacman Server...
echo.
echo Make sure you have Python installed with required packages:
echo pip install -r requirements.txt
echo.
echo Server will start on http://localhost:8080
echo For local network access, use your IP address (e.g., http://192.168.1.126:8080)
echo Press Ctrl+C to stop the server
echo.
echo IMPORTANT: Run this outside VS Code to avoid hangs!
echo Close VS Code or run this in a separate Command Prompt.
echo.


REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated successfully!
) else (
    echo WARNING: Virtual environment not found at .venv\Scripts\
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing requirements...
    pip install -r requirements.txt
)

echo.
echo Starting server with virtual environment...
REM Run the server
python app.py
#!/bin/bash
echo "Starting MMO Pacman Server..."
echo ""
echo "Make sure you have Python installed with required packages:"
echo "pip install -r requirements.txt"
echo ""
echo "Server will start on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo ""
read -p "Press Enter to continue..."
python3 app.py
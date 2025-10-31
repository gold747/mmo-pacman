# 🎮 MMO Pacman - Safe Running Instructions

## ⚠️ VS Code Hanging Issue

VS Code may hang when running the Flask-SocketIO server due to:
- Flask's debug reloader creating multiple processes
- Socket.IO background tasks interfering with VS Code's debugger
- Threading conflicts in the development environment

## ✅ Safe Ways to Run the Server

### Option 1: External Command Prompt (Recommended)
```cmd
# Open Command Prompt (not in VS Code)
cd "c:\git\mmo-pacman"
run.bat
```

### Option 2: PowerShell (External)
```powershell
# Open PowerShell (not in VS Code)
cd "c:\git\mmo-pacman"
.\run.bat
```

### Option 3: Direct Python (External Terminal)
```cmd
cd "c:\git\mmo-pacman"
.venv\Scripts\activate
python app.py
```

### Option 4: VS Code Terminal (Use with Caution)
If you must use VS Code terminal:
```cmd
# In VS Code terminal - may cause hanging
cd "c:\git\mmo-pacman"
C:/git/mmo-pacman/.venv/Scripts/python.exe app.py
```

## 🛡️ Preventing Hangs

The server code has been modified to reduce hang risk:
- ✅ `debug=False` - Disables Flask reloader
- ✅ `use_reloader=False` - Prevents multiple processes
- ✅ `socketio.start_background_task()` - Uses proper Socket.IO threading
- ✅ Daemon threads - Clean shutdown handling

## 🎯 Quick Start (No VS Code Issues)

1. **Close VS Code** (to be safe)
2. **Open Command Prompt**
3. **Navigate to project**: `cd "c:\git\mmo-pacman"`
4. **Run server**: `run.bat`
5. **Open browser**: `http://localhost:5000`
6. **Play the game!**

## 🐛 If VS Code Still Hangs

1. **Force close VS Code**: Task Manager → End Task
2. **Restart VS Code**
3. **Use external terminal** for server
4. **Edit code in VS Code**, run server externally

## 🔧 Development Workflow

**Recommended workflow to avoid hangs:**

1. **Edit code** → VS Code
2. **Run server** → External Command Prompt (`run.bat`)
3. **Test game** → Browser (`localhost:5000`)
4. **Stop server** → `Ctrl+C` in Command Prompt
5. **Repeat** → Make changes in VS Code, restart server externally

This way you get the best of both worlds:
- ✅ VS Code for editing (syntax highlighting, IntelliSense)
- ✅ External terminal for running (no hangs)
- ✅ Browser for testing (smooth gameplay)

## 🎮 Game Features Working

- ✅ 30 player multiplayer
- ✅ Real-time movement and pellet collection
- ✅ Ghost AI with player chasing
- ✅ Power pellets and scoring
- ✅ Live leaderboard
- ✅ Responsive design with mini-map

**The game is fully functional - just run it safely!** 🚀
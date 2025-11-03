# Environment Setup Instructions for MMO Pacman

## Automatic Activation Methods:

### Method 1: Use the PowerShell script (Recommended)
```powershell
# Run this from the project directory
.\start_server.ps1
```

### Method 2: Use the batch file
```cmd
# Double-click or run from command prompt
run.bat
```

### Method 3: Use VS Code Tasks
1. Open VS Code in the project folder
2. Press Ctrl+Shift+P
3. Type "Tasks: Run Task"
4. Select "Start MMO Pacman Server"

### Method 4: Manual activation (for development)
```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1
python app.py
```

```cmd
# Command Prompt
.venv\Scripts\activate.bat
python app.py
```

## Setting up automatic activation in VS Code

### Option A: Terminal Profile (Always activate when opening terminal)
1. Open VS Code Settings (Ctrl+,)
2. Search for "terminal.integrated.profiles.windows"
3. Add this configuration:

```json
{
    "terminal.integrated.profiles.windows": {
        "MMO-Pacman-Env": {
            "source": "PowerShell",
            "args": ["-ExecutionPolicy", "ByPass", "-NoExit", "-Command", "& '.venv/Scripts/Activate.ps1'"]
        }
    },
    "terminal.integrated.defaultProfile.windows": "MMO-Pacman-Env"
}
```

### Option B: Workspace Settings (Project-specific)
Create `.vscode/settings.json` with:

```json
{
    "python.defaultInterpreterPath": "./.venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "terminal.integrated.env.windows": {
        "VIRTUAL_ENV": "${workspaceFolder}/.venv"
    }
}
```

## Troubleshooting

If virtual environment doesn't exist:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you get execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
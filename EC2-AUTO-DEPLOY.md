# MMO Pacman EC2 Auto-Deploy Setup

This setup allows your EC2 instance to automatically pull the latest code from GitHub and restart the application on every boot.

## 🚀 Quick Start

### Option 1: Launch New Auto-Deploy EC2 Instance

```powershell
# Run this from your local machine (Windows PowerShell)
.\launch-ec2-autodeploy.ps1
```

This will:
- ✅ Create a new EC2 instance with auto-deploy configured
- ✅ Set up systemd service for automatic startup
- ✅ Configure Nginx reverse proxy
- ✅ Pull latest code on every boot

### Option 2: Add Auto-Deploy to Existing EC2

```bash
# SSH into your existing EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Download and run the auto-deploy setup
cd /tmp
curl -o aws-auto-deploy-setup.sh https://raw.githubusercontent.com/gold747/mmo-pacman/main/aws-auto-deploy-setup.sh
chmod +x aws-auto-deploy-setup.sh
./aws-auto-deploy-setup.sh
```

## 🔄 How Auto-Deploy Works

1. **On Boot**: EC2 instance automatically runs the auto-deploy service
2. **Git Pull**: Fetches latest code from `main` branch
3. **Dependencies**: Updates Python packages if requirements.txt changed
4. **Restart**: Stops old process and starts new version
5. **Logging**: All activities logged to `/home/ubuntu/mmo-pacman/logs/auto-deploy.log`

## 📋 Management Commands

### Manual Update (without restart)
```bash
/home/ubuntu/update-mmo-pacman.sh
```

### Service Management
```bash
# Check service status
systemctl status mmo-pacman-autodeploy

# Restart service (triggers fresh deployment)
sudo systemctl restart mmo-pacman-autodeploy

# View service logs
journalctl -u mmo-pacman-autodeploy -f

# View application logs
tail -f /home/ubuntu/mmo-pacman/logs/auto-deploy.log
tail -f /home/ubuntu/mmo-pacman/logs/app.log
```

### EC2 Instance Management
```powershell
# Stop instance (will auto-deploy when started again)
aws ec2 stop-instances --instance-ids i-your-instance-id

# Start instance (triggers auto-deploy)
aws ec2 start-instances --instance-ids i-your-instance-id

# Restart instance (quickest way to deploy latest code)
aws ec2 reboot-instances --instance-ids i-your-instance-id
```

## 🌐 Access Your Game

After setup completes (3-5 minutes):

- **Via Nginx (recommended)**: `http://your-ec2-public-ip`
- **Direct access**: `http://your-ec2-public-ip:8080`

## 🔄 Deployment Workflow

1. **Develop locally**: Make changes to your code
2. **Commit & Push**: `git add .; git commit -m "Your changes"; git push`
3. **Deploy**: Restart your EC2 instance or run manual update
4. **Automatic**: Latest code is pulled and app restarted

## 📁 File Structure on EC2

```
/home/ubuntu/
├── mmo-pacman/                 # Your game repository
│   ├── app.py                  # Main application
│   ├── auto-deploy.sh         # Auto-deployment script
│   ├── logs/                  # Application and deployment logs
│   └── .venv/                 # Python virtual environment
├── update-mmo-pacman.sh       # Manual update script
└── setup.log                  # Initial setup log
```

## 🛠️ Troubleshooting

### Check if service is running
```bash
ps aux | grep python
systemctl status mmo-pacman-autodeploy
```

### View deployment logs
```bash
tail -f /home/ubuntu/mmo-pacman/logs/auto-deploy.log
```

### Manual deployment (if auto-deploy fails)
```bash
cd /home/ubuntu/mmo-pacman
./auto-deploy.sh
```

### Check Git repository status
```bash
cd /home/ubuntu/mmo-pacman
git status
git log --oneline -5
```

## 🔐 Security Notes

- Auto-deploy script is included in public repository
- No sensitive credentials in the setup script
- EC2 security group restricts access to ports 22, 80, 8080
- Application runs as `ubuntu` user (non-root)

## ⚡ Benefits

- **Zero-downtime updates**: Just restart EC2 to get latest code
- **Always current**: Never worry about outdated deployments
- **Automatic recovery**: Service restarts automatically if it crashes
- **Easy rollback**: Git allows easy reversion to previous versions
- **Monitoring**: Comprehensive logging for troubleshooting
#!/bin/bash

# AWS EC2 Ubuntu Auto-Deploy Setup Script for MMO Pacman
# This script sets up automatic Git pull and app restart on EC2 startup

echo "🚀 Setting up MMO Pacman with Auto-Deploy on AWS EC2..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required tools
sudo apt install -y python3 python3-pip python3-venv git htop nginx curl

# Create application directory
cd /home/ubuntu

# Clone the repository (replace with your actual GitHub username)
echo "📥 Cloning repository..."
git clone https://github.com/gold747/mmo-pacman.git
cd mmo-pacman

# Create virtual environment and install dependencies
echo "🐍 Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up environment variables
echo "🔐 Setting up environment variables..."
export SECRET_KEY="$(openssl rand -base64 32)"
echo "export SECRET_KEY='$SECRET_KEY'" >> /home/ubuntu/.bashrc

# Create logs directory
mkdir -p logs

# Create the auto-deploy script
echo "📝 Creating auto-deploy script..."
cat > /home/ubuntu/mmo-pacman/auto-deploy.sh << 'EOF'
#!/bin/bash

# MMO Pacman Auto-Deploy Script
# This script pulls the latest code and restarts the application

REPO_DIR="/home/ubuntu/mmo-pacman"
LOG_FILE="$REPO_DIR/logs/auto-deploy.log"

echo "$(date): Starting auto-deploy process..." >> $LOG_FILE

cd $REPO_DIR

# Pull latest changes from Git
echo "$(date): Pulling latest changes from Git..." >> $LOG_FILE
git fetch origin
git reset --hard origin/main

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
echo "$(date): Installing/updating dependencies..." >> $LOG_FILE
pip install -r requirements.txt

# Stop existing process (if running)
echo "$(date): Stopping existing process..." >> $LOG_FILE
pkill -f "python.*app.py" || true

# Wait a moment for graceful shutdown
sleep 2

# Start the application in the background
echo "$(date): Starting MMO Pacman server..." >> $LOG_FILE
cd $REPO_DIR
source .venv/bin/activate
export SECRET_KEY="${SECRET_KEY}"
nohup python app.py > logs/app.log 2>&1 &

# Get the PID and save it
echo $! > /tmp/mmo-pacman.pid

echo "$(date): Auto-deploy completed successfully. PID: $(cat /tmp/mmo-pacman.pid)" >> $LOG_FILE
EOF

# Make the auto-deploy script executable
chmod +x /home/ubuntu/mmo-pacman/auto-deploy.sh

# Create systemd service for automatic startup
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/mmo-pacman.service << 'EOF'
[Unit]
Description=MMO Pacman Game Server with Auto-Deploy
After=network.target
Wants=network-online.target

[Service]
Type=forking
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/mmo-pacman
Environment=SECRET_KEY=
EnvironmentFile=/home/ubuntu/.bashrc
ExecStartPre=/bin/bash /home/ubuntu/mmo-pacman/auto-deploy.sh
ExecStart=/bin/bash -c 'source /home/ubuntu/mmo-pacman/.venv/bin/activate && cd /home/ubuntu/mmo-pacman && python app.py'
ExecStop=/bin/kill -TERM $MAINPID
PIDFile=/tmp/mmo-pacman.pid
Restart=always
RestartSec=10
StandardOutput=file:/home/ubuntu/mmo-pacman/logs/service.log
StandardError=file:/home/ubuntu/mmo-pacman/logs/service-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create a simpler service that just runs the auto-deploy script
sudo tee /etc/systemd/system/mmo-pacman-autodeploy.service << 'EOF'
[Unit]
Description=MMO Pacman Auto-Deploy Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/mmo-pacman
ExecStart=/bin/bash /home/ubuntu/mmo-pacman/auto-deploy.sh
RemainAfterExit=true
StandardOutput=file:/home/ubuntu/mmo-pacman/logs/autodeploy-service.log
StandardError=file:/home/ubuntu/mmo-pacman/logs/autodeploy-service-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create manual update script for easy updates
echo "🔄 Creating manual update script..."
cat > /home/ubuntu/update-mmo-pacman.sh << 'EOF'
#!/bin/bash

echo "🔄 Updating MMO Pacman..."
cd /home/ubuntu/mmo-pacman

# Run the auto-deploy script
./auto-deploy.sh

echo "✅ Update completed!"
echo "📊 Check status: systemctl status mmo-pacman-autodeploy"
echo "📋 View logs: tail -f /home/ubuntu/mmo-pacman/logs/auto-deploy.log"
echo "🌐 Your game should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
EOF

chmod +x /home/ubuntu/update-mmo-pacman.sh

# Set proper ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/mmo-pacman
sudo chown ubuntu:ubuntu /home/ubuntu/update-mmo-pacman.sh

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable mmo-pacman-autodeploy.service

# Run initial deploy
echo "🚀 Running initial deployment..."
/home/ubuntu/mmo-pacman/auto-deploy.sh

# Start the service
sudo systemctl start mmo-pacman-autodeploy.service

# Configure Nginx reverse proxy (optional)
echo "🌐 Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/mmo-pacman << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mmo-pacman /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "✅ Setup complete!"
echo "🔄 Auto-deploy service enabled - will run on every boot"
echo "🌐 Your game is available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "🌐 Direct access: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
echo ""
echo "📋 Useful commands:"
echo "  Manual update: /home/ubuntu/update-mmo-pacman.sh"
echo "  Check service: systemctl status mmo-pacman-autodeploy"
echo "  View logs: tail -f /home/ubuntu/mmo-pacman/logs/auto-deploy.log"
echo "  Restart service: sudo systemctl restart mmo-pacman-autodeploy"
echo ""
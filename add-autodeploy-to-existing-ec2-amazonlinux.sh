#!/bin/bash

# Add Auto-Deploy to Existing Amazon Linux EC2 Instance (ec2-user)
# Run this script on your existing EC2 instance to add auto-deploy functionality

echo "🔄 Adding Auto-Deploy functionality to existing MMO Pacman instance (Amazon Linux)..."

# Ensure we're in the right directory
cd /home/ec2-user/mmo-pacman || { echo "❌ MMO Pacman directory not found!"; exit 1; }

echo "📥 Pulling latest changes from Git..."
git pull origin main

echo "🐍 Updating Python dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

echo "📝 Creating auto-deploy script..."
cat > auto-deploy.sh << 'EOF'
#!/bin/bash

# MMO Pacman Auto-Deploy Script for Amazon Linux
# This script pulls the latest code and restarts the application

REPO_DIR="/home/ec2-user/mmo-pacman"
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
export SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 32)}"
nohup python app.py > logs/app.log 2>&1 &

# Get the PID and save it
echo $! > /tmp/mmo-pacman.pid

echo "$(date): Auto-deploy completed successfully. PID: $(cat /tmp/mmo-pacman.pid)" >> $LOG_FILE
EOF

chmod +x auto-deploy.sh

echo "⚙️ Creating systemd service for auto-deploy..."
sudo tee /etc/systemd/system/mmo-pacman-autodeploy.service << 'EOF'
[Unit]
Description=MMO Pacman Auto-Deploy Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/mmo-pacman
ExecStart=/bin/bash /home/ec2-user/mmo-pacman/auto-deploy.sh
RemainAfterExit=true
StandardOutput=file:/home/ec2-user/mmo-pacman/logs/autodeploy-service.log
StandardError=file:/home/ec2-user/mmo-pacman/logs/autodeploy-service-error.log

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Creating manual update script..."
cat > /home/ec2-user/update-mmo-pacman.sh << 'EOF'
#!/bin/bash

echo "🔄 Updating MMO Pacman..."
cd /home/ec2-user/mmo-pacman

# Run the auto-deploy script
./auto-deploy.sh

echo "✅ Update completed!"
echo "📊 Check status: systemctl status mmo-pacman-autodeploy"
echo "📋 View logs: tail -f /home/ec2-user/mmo-pacman/logs/auto-deploy.log"
echo "🌐 Your game should be available at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
EOF

chmod +x /home/ec2-user/update-mmo-pacman.sh

# Ensure logs directory exists
mkdir -p logs

# Set proper ownership
sudo chown -R ec2-user:ec2-user /home/ec2-user/mmo-pacman
sudo chown ec2-user:ec2-user /home/ec2-user/update-mmo-pacman.sh

# Enable and start the service
echo "🚀 Enabling auto-deploy service..."
sudo systemctl daemon-reload
sudo systemctl enable mmo-pacman-autodeploy.service

# Install Nginx if not already installed (Amazon Linux uses yum)
if ! command -v nginx &> /dev/null; then
    echo "🌐 Installing Nginx..."
    sudo yum update -y
    sudo amazon-linux-extras install nginx1 -y
fi

# Configure Nginx reverse proxy
echo "🌐 Setting up Nginx reverse proxy..."
sudo tee /etc/nginx/conf.d/mmo-pacman.conf << 'EOF'
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

# Remove default nginx config if exists
sudo rm -f /etc/nginx/nginx.conf.default

# Test and start Nginx
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl start nginx

# Run initial auto-deploy
echo "🚀 Running initial auto-deploy..."
./auto-deploy.sh

echo ""
echo "✅ Auto-Deploy setup complete!"
echo "🔄 Auto-deploy service enabled - will run on every boot"
echo "🌐 Your game is available at:"
echo "   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4) (via Nginx)"
echo "   http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080 (direct)"
echo ""
echo "📋 Useful commands:"
echo "  Manual update: /home/ec2-user/update-mmo-pacman.sh"
echo "  Check service: systemctl status mmo-pacman-autodeploy"
echo "  View logs: tail -f /home/ec2-user/mmo-pacman/logs/auto-deploy.log"
echo "  Restart service: sudo systemctl restart mmo-pacman-autodeploy"
echo ""
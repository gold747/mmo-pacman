#!/bin/bash

# AWS EC2 Ubuntu Setup Script Template for MMO Pacman
# Replace YOUR_GITHUB_USERNAME with your actual GitHub username

echo "🚀 Setting up MMO Pacman on AWS EC2..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required tools
sudo apt install -y python3 python3-pip python3-venv git htop nginx

# Install Node.js and PM2 for process management
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2

# Create application directory
cd /home/ubuntu

# CUSTOMIZE THIS: Replace YOUR_GITHUB_USERNAME with your actual username
git clone https://github.com/YOUR_GITHUB_USERNAME/mmo-pacman.git
cd mmo-pacman

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables for production
export SECRET_KEY="$(openssl rand -base64 32)"
echo "export SECRET_KEY='$SECRET_KEY'" >> ~/.bashrc

# Create PM2 ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'mmo-pacman',
    script: '.venv/bin/python',
    args: 'app.py',
    cwd: '/home/ubuntu/mmo-pacman',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      SECRET_KEY: process.env.SECRET_KEY
    },
    log_file: '/home/ubuntu/mmo-pacman/logs/combined.log',
    out_file: '/home/ubuntu/mmo-pacman/logs/out.log',
    error_file: '/home/ubuntu/mmo-pacman/logs/error.log'
  }]
}
EOF

# Create logs directory
mkdir -p logs

# Set up PM2 startup
pm2 start ecosystem.config.js
pm2 startup
pm2 save

# Configure Nginx reverse proxy (optional)
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
sudo systemctl reload nginx

echo "✅ Setup complete!"
echo "🌐 Your game will be available at: http://YOUR_EC2_PUBLIC_IP"
echo "📊 Monitor with: pm2 monit"
echo "📋 View logs with: pm2 logs mmo-pacman"
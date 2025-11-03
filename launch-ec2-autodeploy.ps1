# AWS PowerShell Script to Launch EC2 with Auto-Deploy for MMO Pacman
Write-Host "🚀 Creating EC2 instance with Auto-Deploy for MMO Pacman..." -ForegroundColor Green

# Variables
$InstanceName = "mmo-pacman-autodeploy"
$KeyName = "mmo-pacman-key"
$SecurityGroupName = "mmo-pacman-sg"
$AmiId = "ami-0c02fb55956c7d316"  # Ubuntu 22.04 LTS (ap-southeast-2)
$InstanceType = "t2.micro"

# Create key pair
Write-Host "🔑 Creating key pair..." -ForegroundColor Yellow
try {
    $KeyPair = aws ec2 create-key-pair --key-name $KeyName --query 'KeyMaterial' --output text
    $KeyPair | Out-File -FilePath "$KeyName.pem" -Encoding ASCII
    Write-Host "✅ Key pair saved as $KeyName.pem" -ForegroundColor Green
} catch {
    Write-Host "❌ Key pair might already exist" -ForegroundColor Red
}

# Create security group
Write-Host "🔒 Creating security group..." -ForegroundColor Yellow
try {
    $SecurityGroupId = aws ec2 create-security-group --group-name $SecurityGroupName --description "Security group for MMO Pacman auto-deploy server" --query 'GroupId' --output text

    # Add security group rules
    aws ec2 authorize-security-group-ingress --group-id $SecurityGroupId --protocol tcp --port 22 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $SecurityGroupId --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $SecurityGroupId --protocol tcp --port 8080 --cidr 0.0.0.0/0

    Write-Host "✅ Security group created: $SecurityGroupId" -ForegroundColor Green
} catch {
    Write-Host "❌ Security group might already exist" -ForegroundColor Red
    $SecurityGroupId = aws ec2 describe-security-groups --group-names $SecurityGroupName --query 'SecurityGroups[0].GroupId' --output text
    Write-Host "📋 Using existing security group: $SecurityGroupId" -ForegroundColor Yellow
}

# User data for automatic setup with auto-deploy
$UserData = @"
#!/bin/bash
cd /tmp
curl -o aws-auto-deploy-setup.sh https://raw.githubusercontent.com/gold747/mmo-pacman/main/aws-auto-deploy-setup.sh
chmod +x aws-auto-deploy-setup.sh
./aws-auto-deploy-setup.sh > /home/ubuntu/setup.log 2>&1
"@

# Encode user data to base64
$UserDataBytes = [System.Text.Encoding]::UTF8.GetBytes($UserData)
$UserDataBase64 = [System.Convert]::ToBase64String($UserDataBytes)

# Launch instance
Write-Host "🖥️ Launching EC2 instance with auto-deploy..." -ForegroundColor Yellow
$InstanceId = aws ec2 run-instances --image-id $AmiId --count 1 --instance-type $InstanceType --key-name $KeyName --security-group-ids $SecurityGroupId --user-data $UserDataBase64 --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$InstanceName}]" --query 'Instances[0].InstanceId' --output text

Write-Host "✅ Instance launched: $InstanceId" -ForegroundColor Green
Write-Host "⏳ Waiting for instance to be running..." -ForegroundColor Yellow

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $InstanceId

# Get public IP
$PublicIP = aws ec2 describe-instances --instance-ids $InstanceId --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

Write-Host ""
Write-Host "🎉 SUCCESS! Your Auto-Deploy MMO Pacman server is starting!" -ForegroundColor Green
Write-Host "📍 Instance ID: $InstanceId" -ForegroundColor Cyan
Write-Host "🌐 Public IP: $PublicIP" -ForegroundColor Cyan
Write-Host "🔑 SSH Key: $KeyName.pem" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎮 Your game will be available at:" -ForegroundColor Yellow
Write-Host "   🌐 http://$PublicIP (via Nginx)" -ForegroundColor Green
Write-Host "   🎯 http://$PublicIP:8080 (direct)" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 SSH access: ssh -i $KeyName.pem ubuntu@$PublicIP" -ForegroundColor Yellow
Write-Host ""
Write-Host "🚀 AUTO-DEPLOY FEATURES:" -ForegroundColor Magenta
Write-Host "   ✅ Pulls latest code on every boot" -ForegroundColor Green
Write-Host "   ✅ Automatic service restart" -ForegroundColor Green
Write-Host "   ✅ Manual update command available" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Useful SSH commands:" -ForegroundColor Cyan
Write-Host "   Update manually: /home/ubuntu/update-mmo-pacman.sh" -ForegroundColor White
Write-Host "   Check service: systemctl status mmo-pacman-autodeploy" -ForegroundColor White
Write-Host "   View logs: tail -f /home/ubuntu/mmo-pacman/logs/auto-deploy.log" -ForegroundColor White
Write-Host "   View setup log: tail -f /home/ubuntu/setup.log" -ForegroundColor White
Write-Host ""
Write-Host "⏰ Full setup will complete in ~3-5 minutes" -ForegroundColor Magenta
Write-Host "🔄 Every time you push to GitHub, restart the instance to auto-update!" -ForegroundColor Yellow

# Additional management commands
Write-Host ""
Write-Host "📊 Management commands:" -ForegroundColor Cyan
Write-Host "   Stop instance: aws ec2 stop-instances --instance-ids $InstanceId" -ForegroundColor White
Write-Host "   Start instance: aws ec2 start-instances --instance-ids $InstanceId" -ForegroundColor White
Write-Host "   Terminate: aws ec2 terminate-instances --instance-ids $InstanceId" -ForegroundColor White
Write-Host "   Monitor: aws ec2 describe-instances --instance-ids $InstanceId" -ForegroundColor White
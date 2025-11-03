# PowerShell script to add Auto-Deploy to existing EC2 instance
# This script will SSH into your existing EC2 instance and set up auto-deploy

$InstanceId = "i-0352092bc70157eb1"
$PublicIP = "54.206.100.30"
$KeyFile = "mmo-pacman-key.pem"
$User = "ec2-user"  # Amazon Linux uses ec2-user instead of ubuntu

Write-Host "Adding Auto-Deploy to existing EC2 instance..." -ForegroundColor Green
Write-Host "Instance: $InstanceId" -ForegroundColor Cyan
Write-Host "IP: $PublicIP" -ForegroundColor Cyan

# Check if key file exists
if (-not (Test-Path $KeyFile)) {
    Write-Host "ERROR: Key file '$KeyFile' not found!" -ForegroundColor Red
    Write-Host "Make sure you have the SSH key file in this directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Setting up SSH connection and deploying auto-deploy..." -ForegroundColor Yellow

# Copy the setup script to EC2 and run it
$SetupCommands = @"
# Download and run the auto-deploy setup script
cd /home/ec2-user
curl -o add-autodeploy-setup.sh https://raw.githubusercontent.com/gold747/mmo-pacman/main/add-autodeploy-to-existing-ec2-amazonlinux.sh
chmod +x add-autodeploy-setup.sh
./add-autodeploy-setup.sh
"@

# Execute the setup on EC2
Write-Host "Connecting to EC2 and running setup..." -ForegroundColor Magenta
ssh -i $KeyFile -o StrictHostKeyChecking=no $User@$PublicIP $SetupCommands

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS: Auto-Deploy successfully added to your existing EC2 instance!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your game is now available at:" -ForegroundColor Yellow
    Write-Host "   http://$PublicIP (via Nginx)" -ForegroundColor Green  
    Write-Host "   http://$PublicIP" + ":8080 (direct)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Auto-Deploy Features Added:" -ForegroundColor Magenta
    Write-Host "   - Pulls latest code on every boot" -ForegroundColor Green
    Write-Host "   - Automatic service restart" -ForegroundColor Green
    Write-Host "   - Nginx reverse proxy setup" -ForegroundColor Green
    Write-Host "   - Manual update command available" -ForegroundColor Green
    Write-Host ""
    Write-Host "SSH Commands (connect with: ssh -i $KeyFile $User@$PublicIP):" -ForegroundColor Cyan
    Write-Host "   Manual update: /home/ec2-user/update-mmo-pacman.sh" -ForegroundColor White
    Write-Host "   Check service: systemctl status mmo-pacman-autodeploy" -ForegroundColor White
    Write-Host "   View logs: tail -f /home/ec2-user/mmo-pacman/logs/auto-deploy.log" -ForegroundColor White
    Write-Host ""
    Write-Host "Future Deployments:" -ForegroundColor Yellow
    Write-Host "   1. Push code: git push" -ForegroundColor White
    Write-Host "   2. Deploy: aws ec2 reboot-instances --instance-ids $InstanceId" -ForegroundColor White
    Write-Host "   OR manually: /home/ec2-user/update-mmo-pacman.sh" -ForegroundColor White
} else {
    Write-Host "ERROR: Setup failed. Check the SSH connection and try again." -ForegroundColor Red
    Write-Host "Manual setup: ssh -i $KeyFile $User@$PublicIP" -ForegroundColor Yellow
}
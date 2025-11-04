# MMO Pacman EC2 Server Stop Script
param(
    [string]$InstanceId = "i-0352092bc70157eb1"
)

Write-Host "🛑 Stopping MMO Pacman EC2 Server..." -ForegroundColor Yellow
Write-Host "Instance ID: $InstanceId" -ForegroundColor Cyan

# Get current instance state
Write-Host "Checking current instance state..." -ForegroundColor Yellow
try {
    $instanceInfo = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0]" | ConvertFrom-Json
    
    $currentState = $instanceInfo.State.Name
    $publicIp = $instanceInfo.PublicIpAddress
    
    Write-Host "Current state: $currentState" -ForegroundColor Gray
    
    if ($currentState -eq "stopped") {
        Write-Host "✅ Instance is already stopped" -ForegroundColor Green
        exit 0
    } elseif ($currentState -eq "stopping") {
        Write-Host "⏳ Instance is already stopping..." -ForegroundColor Yellow
    } elseif ($currentState -ne "running") {
        Write-Host "⚠️ Instance is in '$currentState' state" -ForegroundColor Yellow
    }
    
    if ($publicIp) {
        Write-Host "Public IP (will be released): $publicIp" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "❌ Failed to get instance status: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Stop the EC2 instance
Write-Host "Stopping EC2 instance..." -ForegroundColor Yellow
try {
    $stopResult = aws ec2 stop-instances --instance-ids $InstanceId | ConvertFrom-Json
    
    if ($stopResult.StoppingInstances) {
        $newState = $stopResult.StoppingInstances[0].CurrentState.Name
        $prevState = $stopResult.StoppingInstances[0].PreviousState.Name
        Write-Host "✅ Instance state changed: $prevState -> $newState" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to stop instance: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Wait for instance to be fully stopped
Write-Host "Waiting for instance to be fully stopped..." -ForegroundColor Yellow

$maxAttempts = 20
$attempt = 0

do {
    $attempt++
    Start-Sleep -Seconds 5
    
    Write-Host "Attempt $attempt/$maxAttempts - Checking stop progress..." -ForegroundColor Gray
    
    try {
        $instanceInfo = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0].State" | ConvertFrom-Json
        $state = $instanceInfo.Name
        
        Write-Host "State: $state" -ForegroundColor Gray
        
        if ($state -eq "stopped") {
            Write-Host "✅ Instance is fully stopped!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "Error checking status: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "⚠️ Instance may still be stopping. Check AWS Console for final status." -ForegroundColor Yellow
}

# Display results
Write-Host ""
Write-Host "============================================================" -ForegroundColor Red
Write-Host "MMO PACMAN SERVER STOPPED" -ForegroundColor Red -BackgroundColor Black
Write-Host "============================================================" -ForegroundColor Red
Write-Host ""

Write-Host "Instance Details:" -ForegroundColor Cyan
Write-Host "Instance ID: $InstanceId" -ForegroundColor White
Write-Host "Status: Stopped" -ForegroundColor White
Write-Host "Public IP: Released (will get new IP when restarted)" -ForegroundColor Gray
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "Start: .\start-ec2-clean.ps1" -ForegroundColor Green
Write-Host "Status: aws ec2 describe-instances --instance-ids $InstanceId --query 'Reservations[0].Instances[0].State'" -ForegroundColor Gray
Write-Host ""

Write-Host "💰 Instance is now stopped - no compute charges will accrue" -ForegroundColor Green
Write-Host "💾 All data and configuration are preserved" -ForegroundColor Green
Write-Host "🔄 Use start-ec2-clean.ps1 to restart when needed" -ForegroundColor Green
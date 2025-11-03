# MMO Pacman EC2 Server Startup Script
param(
    [string]$InstanceId = "i-0352092bc70157eb1"
)

Write-Host "Starting MMO Pacman EC2 Server..." -ForegroundColor Yellow
Write-Host "Instance ID: $InstanceId" -ForegroundColor Cyan

# Start the EC2 instance
Write-Host "Starting EC2 instance..." -ForegroundColor Yellow
try {
    $startResult = aws ec2 start-instances --instance-ids $InstanceId | ConvertFrom-Json
    
    if ($startResult.StartingInstances) {
        $currentState = $startResult.StartingInstances[0].CurrentState.Name
        $previousState = $startResult.StartingInstances[0].PreviousState.Name
        Write-Host "Instance state changed: $previousState -> $currentState" -ForegroundColor Green
    }
} catch {
    Write-Host "Failed to start instance: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Wait for instance to be running and get public IP
Write-Host "Waiting for instance to be running and get public IP..." -ForegroundColor Yellow

$maxAttempts = 30
$attempt = 0
$publicIp = $null

do {
    $attempt++
    Start-Sleep -Seconds 10
    
    Write-Host "Attempt $attempt/$maxAttempts - Checking instance status..." -ForegroundColor Gray
    
    try {
        $instanceInfo = aws ec2 describe-instances --instance-ids $InstanceId --query "Reservations[0].Instances[0]" | ConvertFrom-Json
        
        $state = $instanceInfo.State.Name
        $publicIp = $instanceInfo.PublicIpAddress
        
        Write-Host "State: $state" -ForegroundColor Gray
        
        if ($state -eq "running" -and $publicIp) {
            Write-Host "Instance is running!" -ForegroundColor Green
            break
        } elseif ($state -eq "running" -and !$publicIp) {
            Write-Host "Instance running but no public IP yet..." -ForegroundColor Gray
        } else {
            Write-Host "Instance state: $state" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Error checking status: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} while ($attempt -lt $maxAttempts)

if (!$publicIp -or $attempt -ge $maxAttempts) {
    Write-Host "Failed to get public IP after $maxAttempts attempts" -ForegroundColor Red
    Write-Host "You can manually check the instance in AWS Console" -ForegroundColor Yellow
    exit 1
}

# Wait for auto-deploy service to start
Write-Host "Waiting for auto-deploy service to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Display the results
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "MMO PACMAN SERVER IS READY!" -ForegroundColor Green -BackgroundColor Black
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Game URL:" -ForegroundColor Cyan
Write-Host "http://$publicIp`:8080" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""

Write-Host "Instance Details:" -ForegroundColor Cyan
Write-Host "Instance ID: $InstanceId" -ForegroundColor White
Write-Host "Public IP: $publicIp" -ForegroundColor White
Write-Host "Port: 8080" -ForegroundColor White
Write-Host ""

Write-Host "Useful Commands:" -ForegroundColor Cyan
Write-Host "SSH: ssh -i `"mmo-pacman-key.pem`" ec2-user@$publicIp" -ForegroundColor Gray
Write-Host "Stop: aws ec2 stop-instances --instance-ids $InstanceId" -ForegroundColor Gray
Write-Host ""

# Try to open in browser
$openBrowser = Read-Host "Open game in browser? (y/N)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    $gameUrl = "http://$publicIp`:8080"
    Write-Host "Opening $gameUrl..." -ForegroundColor Yellow
    Start-Process $gameUrl
}

Write-Host "Ready to play! Share the URL with friends for multiplayer action!" -ForegroundColor Green
# Web Research Agent - PATH Setup Script for Windows
# This script adds the Python Scripts directory to your PATH permanently

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Web Research Agent - PATH Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "For permanent PATH changes, please run PowerShell as Administrator" -ForegroundColor Yellow
    Write-Host ""

    $choice = Read-Host "Continue with temporary PATH change for this session? (y/n)"
    if ($choice -ne "y") {
        Write-Host "Setup cancelled." -ForegroundColor Red
        exit
    }
}

# Detect Python Scripts directory
$pythonVersion = python --version 2>&1 | Select-String -Pattern "\d+\.\d+" | ForEach-Object { $_.Matches.Value }
$scriptsPath = "$env:APPDATA\Python\Python$($pythonVersion.Replace('.', ''))\Scripts"

# Check if directory exists
if (-not (Test-Path $scriptsPath)) {
    Write-Host "Checking alternative Python locations..." -ForegroundColor Yellow

    # Try common alternatives
    $alternatives = @(
        "$env:LOCALAPPDATA\Programs\Python\Python$($pythonVersion.Replace('.', ''))\Scripts",
        "$env:USERPROFILE\AppData\Roaming\Python\Python$($pythonVersion.Replace('.', ''))\Scripts",
        "C:\Python$($pythonVersion.Replace('.', ''))\Scripts"
    )

    foreach ($alt in $alternatives) {
        if (Test-Path $alt) {
            $scriptsPath = $alt
            break
        }
    }

    if (-not (Test-Path $scriptsPath)) {
        Write-Host "ERROR: Could not find Python Scripts directory" -ForegroundColor Red
        Write-Host "Expected location: $scriptsPath" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please manually add your Python Scripts directory to PATH" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Found Python Scripts directory:" -ForegroundColor Green
Write-Host "  $scriptsPath" -ForegroundColor White
Write-Host ""

# Check if already in PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -like "*$scriptsPath*") {
    Write-Host "✓ Scripts directory is already in your PATH!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Try running: webresearch" -ForegroundColor Cyan
    Write-Host "If it still doesn't work, restart your terminal." -ForegroundColor Yellow
    exit 0
}

# Add to PATH
if ($isAdmin) {
    Write-Host "Adding to PATH permanently..." -ForegroundColor Cyan

    try {
        $newPath = $currentPath + ";$scriptsPath"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")

        Write-Host "✓ Successfully added to PATH!" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANT: Restart your terminal for changes to take effect" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Then run: webresearch" -ForegroundColor Cyan
    }
    catch {
        Write-Host "ERROR: Failed to update PATH" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "Adding to PATH for current session only..." -ForegroundColor Yellow
    $env:Path += ";$scriptsPath"

    Write-Host "✓ Temporary PATH updated!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Try running: webresearch" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "NOTE: This change only lasts until you close this terminal." -ForegroundColor Yellow
    Write-Host "For permanent changes, run this script as Administrator." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Cyan

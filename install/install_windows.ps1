<#
.SYNOPSIS
Bash.ai Windows Installer
#>

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Installing Python 3..."
    winget install Python.Python.3 --accept-package-agreements --accept-source-agreements
    if (-not $?) {
        Write-Error "Failed to install Python. Please install it manually from python.org"
        exit 1
    }
}

# Clone repository if not already present
if (-not (Test-Path "bash.ai")) {
    git clone https://github.com/Nullmega15/bash.ai.git
    cd bash.ai
}

# Install dependencies
Write-Host "Installing dependencies..."
python -m pip install -r .\requirements.txt
if (-not $?) {
    Write-Error "Failed to install dependencies"
    exit 1
}

# Create launcher
Write-Host "Creating launcher..."
@"
@echo off
python "%~dp0bash.ai\src\bashai.py" %*
"@ | Out-File -Encoding ascii bashai.cmd

# Add to PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $currentPath.Contains((Get-Location).Path)) {
    [Environment]::SetEnvironmentVariable(
        "Path",
        $currentPath + ";" + (Get-Location).Path,
        "User"
    )
    $env:Path += ";" + (Get-Location).Path
}

Write-Host @"

Bash.ai installed successfully!

Usage:
  bashai [command]    - Execute single command
  bashai              - Interactive mode

Try these examples:
  bashai "list files"
  bashai "show processes"
"@

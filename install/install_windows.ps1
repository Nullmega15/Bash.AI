@'
# Corrected Bash.ai Windows Installer
$ErrorActionPreference = "Stop"

# Set proper paths
$repoDir = $PWD
$srcPath = Join-Path $repoDir "src\bashai.py"

# Verify source file exists
if (-not (Test-Path $srcPath)) {
    throw "Source file not found at $srcPath"
}

# Install dependencies
python -m pip install -r (Join-Path $repoDir "requirements.txt")

# Create launcher in user's local bin
$launcherPath = Join-Path $env:USERPROFILE "AppData\Local\Microsoft\WindowsApps\bashai.cmd"
@"
@echo off
python "$srcPath" %*
"@ | Out-File -Encoding ascii $launcherPath

# Add to PATH if not already present
$path = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $path.Contains($env:USERPROFILE + "\AppData\Local\Microsoft\WindowsApps")) {
    [Environment]::SetEnvironmentVariable(
        "Path",
        $path + ";" + $env:USERPROFILE + "\AppData\Local\Microsoft\WindowsApps",
        "User"
    )
}

Write-Host @"

✅ Bash.ai installed successfully!
Usage:
  bashai [command]    - Execute single command
  bashai              - Interactive mode

First run configuration:
  bashai --configure
"@
'@ | Out-File -Encoding ascii install_windows.ps1

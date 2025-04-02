# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Please install Python 3 first."
    exit 1
}

# Install dependencies
pip install -r requirements.txt

# Create batch file
@"
@echo off
python "%~dp0src\bashai.py" %*
"@ | Out-File -Encoding ascii bashai.cmd

# Add to PATH
$env:Path += ";$pwd"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$pwd", "User")

Write-Host "Bash.ai installed successfully! Run with 'bashai'"

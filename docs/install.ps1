# Gaia CLI Windows Installer — https://gaia.tiongson.co/install.ps1
# Usage: iex (irm https://gaia.tiongson.co/install.ps1)
# -----------------------------------------------------------------------------
$ErrorActionPreference = "Stop"

$MinPythonMajor = 3
$MinPythonMinor = 8

Write-Host "Checking for Python..." -ForegroundColor Cyan

# 1. Find Python executable
$PythonCmd = $null
foreach ($cmd in @("python", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        # Check version
        try {
            $verString = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            $parts = $verString.Split('.')
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            
            if ($major -eq $MinPythonMajor -and $minor -ge $MinPythonMinor) {
                $PythonCmd = $cmd
                break
            }
        } catch {
            # Continue checking
        }
    }
}

if ($null -eq $PythonCmd) {
    Write-Error "Error: Python 3.8+ is required but not found on your system. Please install Python from https://python.org and try again."
    exit 1
}

Write-Host "Found Python ($PythonCmd). Checking installation method..." -ForegroundColor Gray

# 2. Check if pipx is available
$InstalledViaPipx = $false
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    Write-Host "Installing gaia-cli via pipx..." -ForegroundColor Cyan
    try {
        & pipx install gaia-cli
        $InstalledViaPipx = $true
    } catch {
        Write-Host "pipx install failed. Falling back to pip..." -ForegroundColor Yellow
    }
}

if (-not $InstalledViaPipx) {
    Write-Host "Installing gaia-cli via pip..." -ForegroundColor Cyan
    & $PythonCmd -m pip install --user gaia-cli
}

# 3. Handle PATH configuration
Write-Host "Checking PATH environment variable..." -ForegroundColor Gray
$UserScripts = & $PythonCmd -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"

if ($UserScripts) {
    # Check if path exists in current env PATH
    $Paths = $env:PATH -split ';'
    $NormalizedUserScripts = $UserScripts.TrimEnd('\')
    
    $InPath = $false
    foreach ($p in $Paths) {
        if ($p.TrimEnd('\') -ieq $NormalizedUserScripts) {
            $InPath = $true
            break
        }
    }
    
    if (-not $InPath) {
        Write-Host "Adding '$NormalizedUserScripts' to PATH..." -ForegroundColor Cyan
        
        # Current Session
        $env:PATH += ";$UserScripts"
        
        # Persistent User Environment Variable
        try {
            $UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
            if ($UserPath -split ';' -notcontains $NormalizedUserScripts) {
                $NewUserPath = $UserPath
                if ($NewUserPath -and -not $NewUserPath.EndsWith(';')) {
                    $NewUserPath += ";"
                }
                $NewUserPath += $UserScripts
                [Environment]::SetEnvironmentVariable("PATH", $NewUserPath, "User")
                Write-Host "Successfully added to persistent User PATH variable!" -ForegroundColor Green
            }
        } catch {
            Write-Host "Warning: Could not update persistent PATH registry. You may need to manually add '$UserScripts' to your PATH." -ForegroundColor Yellow
        }
    } else {
         Write-Host "Installation directory is already in your PATH." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Done! Please restart your terminal/PowerShell window." -ForegroundColor Green
Write-Host "Verify installation with: gaia --version" -ForegroundColor Green

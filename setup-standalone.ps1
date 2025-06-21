param(
    [switch]$SkipDependencies = $false
)

$ErrorActionPreference = "Stop"

function Write-Step { 
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan 
}

function Write-Success { 
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green 
}

function Install-Chocolatey {
    if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Step "Installing Chocolatey"
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
        Write-Success "Chocolatey installed"
    } else {
        Write-Success "Chocolatey already installed"
    }
}

function Install-Prerequisites {
    Write-Step "Installing Prerequisites"
    
    $dependencies = @(
        @{Name="python"; Package="python"; Check="python"},
        @{Name="nodejs"; Package="nodejs"; Check="node"},
        @{Name="git"; Package="git"; Check="git"}
    )
    
    foreach ($dep in $dependencies) {
        if (!(Get-Command $dep.Check -ErrorAction SilentlyContinue)) {
            Write-Host "Installing $($dep.Name)..." -ForegroundColor Yellow
            choco install $dep.Package -y
        } else {
            Write-Success "$($dep.Name) already installed"
        }
    }
    
    # Refresh environment
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
}

function Create-DirectoryStructure {
    Write-Step "Creating Directory Structure"
    
    $dirs = @(
        "standalone",
        "standalone/build", 
        "standalone/configs",
        "standalone/electron",
        "standalone/electron/assets",
        "standalone/dist"
    )
    
    foreach ($dir in $dirs) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "Created: $dir" -ForegroundColor Gray
        }
    }
    
    Write-Success "Directory structure created"
}

function Show-NextSteps {
    Write-Host @"

🎯 SETUP COMPLETE!

Next steps:
1. Make the minimal database change in backend/bracket/database.py
2. Copy all the new files from the artifacts
3. Run: .\build-standalone.ps1

The setup has created:
- standalone/ folder structure
- All necessary directories for build system

"@ -ForegroundColor Green
}

# Execute setup
try {
    Write-Host @"
╔════════════════════════════════════════════════════════════╗
║          Bracket Tournament System Setup                   ║
║           Preparing Standalone Environment                 ║
╚════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Magenta

    if (!$SkipDependencies) {
        Install-Chocolatey
        Install-Prerequisites
    }
    
    Create-DirectoryStructure
    Show-NextSteps

} catch {
    Write-Error "Setup failed: $($_.Exception.Message)"
    exit 1
}
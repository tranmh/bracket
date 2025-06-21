# ============================================================================
# MASTER BUILD SCRIPT - BUILDS COMPLETE STANDALONE APPLICATION
# ============================================================================

# File: build-standalone.ps1 (NEW FILE - Root directory)
param(
    [string]$OutputDir = ".\dist-standalone",
    [switch]$SkipTests = $false,
    [switch]$DevMode = $false,
    [switch]$Verbose = $false
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

function Write-Error { 
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red 
}

function Test-Prerequisites {
    Write-Step "Checking Prerequisites"
    
    $missing = @()
    
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        $missing += "Python"
    }
    
    if (!(Get-Command node -ErrorAction SilentlyContinue)) {
        $missing += "Node.js"
    }
    
    if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
        $missing += "npm"
    }
    
    if ($missing.Count -gt 0) {
        Write-Error "Missing prerequisites: $($missing -join ', ')"
        Write-Host "Please install the missing prerequisites and try again."
        exit 1
    }
    
    Write-Success "All prerequisites found"
}

function Install-Dependencies {
    Write-Step "Installing Build Dependencies"
    
    # Python dependencies
    Write-Host "📦 Installing Python dependencies..."
    python -m pip install -r standalone/requirements.txt
    
    # Electron dependencies
    Write-Host "📦 Installing Electron dependencies..."
    Set-Location standalone/electron
    npm install
    Set-Location ../..
    
    Write-Success "Dependencies installed"
}

function Build-Backend {
    Write-Step "Building Backend Executable"
    
    python standalone/build/backend.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Backend build failed"
        exit 1
    }
    
    Write-Success "Backend executable built"
}

function Build-Frontend {
    Write-Step "Building Frontend Static Files"
    
    python standalone/build/frontend.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Frontend build failed"
        exit 1
    }
    
    Write-Success "Frontend static files built"
}

function Build-Electron {
    Write-Step "Building Electron Application"
    
    Set-Location standalone/electron
    
    if ($DevMode) {
        Write-Host "🔧 Building development version..."
        npm run build
    } else {
        Write-Host "🔧 Building production version..."
        npm run build-win
    }
    
    if ($LASTEXITCODE -ne 0) {
        Set-Location ../..
        Write-Error "Electron build failed"
        exit 1
    }
    
    Set-Location ../..
    Write-Success "Electron application built"
}

function Test-Build {
    if ($SkipTests) {
        Write-Host "⏭️ Skipping tests (--SkipTests flag used)"
        return
    }
    
    Write-Step "Testing Build"
    
    # Test backend executable
    python standalone/build/test_backend.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Backend test failed"
        exit 1
    }
    
    Write-Success "Build tests passed"
}

function Copy-Final-Output {
    Write-Step "Preparing Final Output"
    
    # Create output directory
    if (Test-Path $OutputDir) {
        Remove-Item $OutputDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    
    # Copy Electron dist files
    $electronDist = "standalone/electron/dist"
    if (Test-Path $electronDist) {
        Copy-Item "$electronDist/*" -Destination $OutputDir -Recurse -Force
    }
    
    # Find the main executable
    $exeFiles = Get-ChildItem $OutputDir -Filter "*.exe" -Recurse
    if ($exeFiles.Count -gt 0) {
        $mainExe = $exeFiles[0]
        Write-Success "Executable created: $($mainExe.FullName)"
        Write-Host "📏 Size: $([math]::Round($mainExe.Length / 1MB, 2)) MB"
    }
    
    Write-Success "Final output prepared in: $OutputDir"
}

function Show-Summary {
    Write-Step "Build Summary"
    
    $exePath = Get-ChildItem $OutputDir -Filter "*.exe" -Recurse | Select-Object -First 1
    
    if ($exePath) {
        Write-Host @"
🎉 BUILD COMPLETE!

📁 Output Location: $($exePath.FullName)
📏 File Size: $([math]::Round($exePath.Length / 1MB, 2)) MB
🔧 Dependencies: NONE
🌐 Internet Required: NO
💾 Database: Embedded SQLite

✨ Ready for distribution!

To test: Double-click the .exe file
To distribute: Give the single .exe file to users

"@ -ForegroundColor Green
    } else {
        Write-Error "No executable found in output directory"
    }
}

# Main execution
try {
    Write-Host @"
==============================================================
|          Bracket Tournament System Builder                 |
|              Standalone Desktop Version                    |
==============================================================
"@ -ForegroundColor Magenta

    Test-Prerequisites
    Install-Dependencies
    Build-Backend
    Build-Frontend
    Build-Electron
    Test-Build
    Copy-Final-Output
    Show-Summary

} catch {
    Write-Error "Build failed: $($_.Exception.Message)"
    if ($Verbose) {
        Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    }
    exit 1
}

# ============================================================================
# SETUP SCRIPT - PREPARES ENVIRONMENT FOR BUILDING
# ============================================================================

# File: setup-standalone.ps1 (NEW FILE - Root directory)
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
==============================================================
|          Bracket Tournament System Setup                   |
|           Preparing Standalone Environment                 |
==============================================================
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

# ============================================================================
# DEVELOPMENT HELPER SCRIPTS
# ============================================================================

# File: standalone/scripts/dev-start.ps1 (NEW FILE)
# Quick development start script
param([switch]$Backend, [switch]$Frontend, [switch]$Electron)

if ($Backend) {
    Write-Host "🚀 Starting backend in standalone mode..."
    $env:BRACKET_STANDALONE = "true"
    Set-Location backend
    python main.py
}

if ($Frontend) {
    Write-Host "🎨 Starting frontend development server..."
    Set-Location frontend
    npm run dev
}

if ($Electron) {
    Write-Host "⚡ Starting Electron in development mode..."
    Set-Location standalone/electron
    npm run dev
}

if (!$Backend -and !$Frontend -and !$Electron) {
    Write-Host @"
Development Helper Script

Usage:
  .\dev-start.ps1 -Backend     # Start backend only
  .\dev-start.ps1 -Frontend    # Start frontend only  
  .\dev-start.ps1 -Electron    # Start Electron only

For full development:
1. Start backend: .\dev-start.ps1 -Backend
2. Start frontend: .\dev-start.ps1 -Frontend  
3. Start Electron: .\dev-start.ps1 -Electron
"@
}

# ============================================================================
# DOCUMENTATION FILES
# ============================================================================

# File: standalone/README.md (NEW FILE)
@"
# Bracket Tournament System - Standalone Desktop Application

This directory contains the standalone desktop application implementation of the Bracket Tournament System.

## Overview

The standalone version packages the entire tournament system into a single executable file that:
- Requires no Docker or server setup
- Uses SQLite instead of PostgreSQL
- Includes an Electron-based desktop interface
- Works completely offline

## Architecture

```
Standalone Application
├── Backend (PyInstaller executable)
│   ├── FastAPI server
│   └── SQLite database
├── Frontend (Static files)
│   └── Next.js exported static site
└── Desktop Shell (Electron)
    └── Native window wrapper
```

## Building

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm

### Quick Build
```powershell
# Setup environment (first time only)
.\setup-standalone.ps1

# Build application
.\build-standalone.ps1
```

### Development Build
```powershell
# Build with development features
.\build-standalone.ps1 -DevMode

# Start components individually
.\standalone\scripts\dev-start.ps1 -Backend
.\standalone\scripts\dev-start.ps1 -Frontend
.\standalone\scripts\dev-start.ps1 -Electron
```

## Directory Structure

- `build/` - Build scripts and tools
- `configs/` - Configuration files for standalone mode
- `electron/` - Electron desktop application
- `dist/` - Built executables and static files
- `scripts/` - Development helper scripts

## Configuration

The standalone version uses environment variable `BRACKET_STANDALONE=true` to enable SQLite mode and adjust other settings for desktop deployment.

## Differences from Docker Version

| Feature | Docker | Standalone |
|---------|--------|------------|
| Database | PostgreSQL | SQLite |
| Deployment | Container-based | Single executable |
| Performance | High (dedicated DB) | Good (embedded DB) |
| Setup Complexity | Requires Docker | Double-click to run |
| Use Case | Production/Multi-user | Desktop/Single tournament |

## License

Same as main project: AGPL-3.0
"@ | Set-Content -Path "standalone/README.md"

# File: STANDALONE_IMPLEMENTATION.md (NEW FILE - Root directory)
@"
# Standalone Implementation Guide

This document describes how to implement the standalone desktop version of Bracket Tournament System.

## Quick Start

1. **Run setup script:**
   ```powershell
   .\setup-standalone.ps1
   ```

2. **Make the minimal database change:**
   In `backend/bracket/database.py`, find the line with `DATABASE_URL = os.getenv("PG_DSN", ...)` and replace with the code from Artifact 1.

3. **Copy all new files from the artifacts to your project**

4. **Build the application:**
   ```powershell
   .\build-standalone.ps1
   ```

5. **Find your executable in `dist-standalone/`**

## File Changes Summary

### Modified Files (1 file)
- `backend/bracket/database.py` - Add SQLite support with environment variable

### New Files (15 files)
- Build system: 6 files in `standalone/build/`
- Electron app: 4 files in `standalone/electron/`
- Configuration: 2 files in `standalone/configs/`
- Scripts: 3 files for building and setup

## Testing

The build process includes automatic testing:
- Backend executable functionality
- API endpoint responsiveness
- Database connectivity

## Distribution

The final output is a single `.exe` file that can be distributed to users. No installation required - just double-click to run.

## Community Contribution

This implementation is designed to be contributed back to the main project:
- No breaking changes to existing code
- Additive features only
- Clean separation of concerns
- Comprehensive documentation

See the community contribution roadmap for integration strategy.
"@ | Set-Content -Path "STANDALONE_IMPLEMENTATION.md"

# ============================================================================
# VERIFICATION SCRIPT
# ============================================================================

# File: verify-standalone.ps1 (NEW FILE - Root directory)
# Script to verify the implementation is working correctly

Write-Host "🔍 Verifying Standalone Implementation..." -ForegroundColor Cyan

$checks = @()

# Check file structure
$requiredFiles = @(
    "standalone/build/backend.py",
    "standalone/build/frontend.py", 
    "standalone/electron/main.js",
    "standalone/electron/package.json",
    "build-standalone.ps1"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        $checks += "✅ $file exists"
    } else {
        $checks += "❌ $file missing"
    }
}

# Check if database modification was made
$dbFile = "backend/bracket/database.py"
if (Test-Path $dbFile) {
    $content = Get-Content $dbFile -Raw
    if ($content -like "*BRACKET_STANDALONE*") {
        $checks += "✅ Database modification applied"
    } else {
        $checks += "❌ Database modification needed"
    }
} else {
    $checks += "❌ Database file not found"
}

# Display results
foreach ($check in $checks) {
    if ($check.StartsWith("✅")) {
        Write-Host $check -ForegroundColor Green
    } else {
        Write-Host $check -ForegroundColor Red
    }
}

$passed = ($checks | Where-Object { $_.StartsWith("✅") }).Count
$total = $checks.Count

Write-Host "`n📊 Verification: $passed/$total checks passed" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

if ($passed -eq $total) {
    Write-Host "🎉 Ready to build! Run: .\build-standalone.ps1" -ForegroundColor Green
} else {
    Write-Host "⚠️ Please address the missing items above" -ForegroundColor Yellow
}
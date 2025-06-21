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

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
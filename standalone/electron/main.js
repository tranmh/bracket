const { app, BrowserWindow, Menu, dialog, shell, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const log = require('electron-log');
const fs = require('fs');

// Configure logging
log.transports.file.level = 'info';
log.transports.console.level = 'debug';

class BracketDesktopApp {
    constructor() {
        this.mainWindow = null;
        this.backendProcess = null;
        this.isQuitting = false;
        this.serverPort = 8400;
        this.isDev = process.argv.includes('--dev');
    }

    async initialize() {
        try {
            log.info('Starting Bracket Tournament System...');
            
            // Start embedded backend
            await this.startBackend();
            
            // Wait for backend to be ready
            await this.waitForBackend();
            
            // Create main window
            this.createMainWindow();
            
            // Setup application menu
            this.setupMenu();
            
            log.info('Application initialized successfully');
        } catch (error) {
            log.error('Failed to initialize application:', error);
            this.showErrorDialog('Initialization Error', 
                `Failed to start the tournament system:\n\n${error.message}\n\nPlease try restarting the application.`);
        }
    }

    async startBackend() {
        return new Promise((resolve, reject) => {
            log.info('Starting backend server...');
            
            // Determine backend executable path
            const backendPath = this.isDev 
                ? path.join(__dirname, '..', 'dist', 'bracket-backend.exe')
                : path.join(process.resourcesPath, 'app', 'bracket-backend.exe');
            
            log.info('Backend path:', backendPath);
            
            // Check if backend exists
            if (!fs.existsSync(backendPath)) {
                reject(new Error(`Backend executable not found at: ${backendPath}`));
                return;
            }

            // Set environment for standalone mode
            const env = { 
                ...process.env, 
                BRACKET_STANDALONE: 'true',
                PORT: this.serverPort.toString()
            };

            // Start backend process
            this.backendProcess = spawn(backendPath, [], {
                stdio: ['pipe', 'pipe', 'pipe'],
                env: env,
                cwd: path.dirname(backendPath)
            });

            this.backendProcess.stdout.on('data', (data) => {
                const output = data.toString();
                log.info('Backend:', output);
                
                // Look for startup confirmation
                if (output.includes('Uvicorn running') || output.includes('Application startup complete')) {
                    resolve();
                }
            });

            this.backendProcess.stderr.on('data', (data) => {
                log.warn('Backend stderr:', data.toString());
            });

            this.backendProcess.on('error', (error) => {
                log.error('Backend process error:', error);
                reject(error);
            });

            this.backendProcess.on('close', (code) => {
                log.info(`Backend process exited with code ${code}`);
                if (!this.isQuitting && code !== 0) {
                    this.showErrorDialog('Backend Error', 'The tournament system backend has stopped unexpectedly.');
                }
            });

            // Timeout fallback
            setTimeout(() => {
                log.info('Backend startup timeout reached, assuming ready');
                resolve();
            }, 10000);
        });
    }

    async waitForBackend() {
        log.info('Waiting for backend to be ready...');
        const maxAttempts = 15;
        let attempts = 0;

        return new Promise((resolve, reject) => {
            const checkBackend = async () => {
                attempts++;
                
                try {
                    const fetch = require('node-fetch');
                    const response = await fetch(`http://localhost:${this.serverPort}/docs`, {
                        timeout: 2000
                    });
                    
                    if (response.ok) {
                        log.info('Backend is ready and responding');
                        resolve();
                        return;
                    }
                } catch (error) {
                    // Backend not ready yet
                }

                if (attempts < maxAttempts) {
                    setTimeout(checkBackend, 1000);
                } else {
                    log.warn('Backend health check failed, proceeding anyway');
                    resolve(); // Proceed even if health check fails
                }
            };

            checkBackend();
        });
    }

    createMainWindow() {
        this.mainWindow = new BrowserWindow({
            width: 1400,
            height: 900,
            minWidth: 1000,
            minHeight: 700,
            show: false,
            titleBarStyle: 'default',
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                enableRemoteModule: false,
                preload: path.join(__dirname, 'preload.js')
            }
        });

        // Load the frontend
        const frontendPath = this.isDev
            ? `http://localhost:3000` // Dev mode uses live server
            : `http://localhost:${this.serverPort}`; // Production uses backend static serve

        log.info('Loading frontend from:', frontendPath);
        this.mainWindow.loadURL(frontendPath);

        // Show window when ready
        this.mainWindow.once('ready-to-show', () => {
            this.mainWindow.show();
            log.info('Main window shown');
        });

        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Handle external links
        this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            shell.openExternal(url);
            return { action: 'deny' };
        });

        // Development tools
        if (this.isDev) {
            this.mainWindow.webContents.openDevTools();
        }
    }

    setupMenu() {
        const template = [
            {
                label: 'File',
                submenu: [
                    {
                        label: 'New Tournament',
                        accelerator: 'CmdOrCtrl+N',
                        click: () => {
                            // Navigate to new tournament page
                            if (this.mainWindow) {
                                this.mainWindow.webContents.executeJavaScript(`
                                    window.location.href = '/tournaments/new';
                                `);
                            }
                        }
                    },
                    { type: 'separator' },
                    {
                        label: 'Refresh',
                        accelerator: 'F5',
                        click: () => {
                            if (this.mainWindow) {
                                this.mainWindow.webContents.reload();
                            }
                        }
                    },
                    { type: 'separator' },
                    {
                        label: 'Exit',
                        accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
                        click: () => {
                            this.isQuitting = true;
                            app.quit();
                        }
                    }
                ]
            },
            {
                label: 'View',
                submenu: [
                    { role: 'reload' },
                    { role: 'forceReload' },
                    { role: 'toggleDevTools' },
                    { type: 'separator' },
                    { role: 'resetZoom' },
                    { role: 'zoomIn' },
                    { role: 'zoomOut' },
                    { type: 'separator' },
                    { role: 'togglefullscreen' }
                ]
            },
            {
                label: 'Tournament',
                submenu: [
                    {
                        label: 'Dashboard',
                        click: () => {
                            if (this.mainWindow) {
                                this.mainWindow.webContents.executeJavaScript(`
                                    window.location.href = '/dashboard';
                                `);
                            }
                        }
                    },
                    {
                        label: 'Manage Tournaments',
                        click: () => {
                            if (this.mainWindow) {
                                this.mainWindow.webContents.executeJavaScript(`
                                    window.location.href = '/tournaments';
                                `);
                            }
                        }
                    }
                ]
            },
            {
                label: 'Help',
                submenu: [
                    {
                        label: 'Documentation',
                        click: () => {
                            shell.openExternal('https://docs.bracketapp.nl');
                        }
                    },
                    {
                        label: 'Report Issue',
                        click: () => {
                            shell.openExternal('https://github.com/evroon/bracket/issues');
                        }
                    },
                    { type: 'separator' },
                    {
                        label: 'About',
                        click: () => {
                            dialog.showMessageBox(this.mainWindow, {
                                type: 'info',
                                title: 'About Bracket Tournament System',
                                message: 'Bracket Tournament System',
                                detail: `Version: 1.0.0\nDesktop Edition\n\nA self-hosted tournament management system\nBuilt with FastAPI, Next.js, and Electron\n\nLicense: AGPL-3.0`
                            });
                        }
                    }
                ]
            }
        ];

        const menu = Menu.buildFromTemplate(template);
        Menu.setApplicationMenu(menu);
    }

    showErrorDialog(title, message) {
        dialog.showErrorBox(title, message);
    }

    async cleanup() {
        this.isQuitting = true;
        
        if (this.backendProcess) {
            log.info('Terminating backend process...');
            this.backendProcess.kill('SIGTERM');
            
            // Give it time to cleanup gracefully
            setTimeout(() => {
                if (this.backendProcess && !this.backendProcess.killed) {
                    log.warn('Force killing backend process');
                    this.backendProcess.kill('SIGKILL');
                }
            }, 3000);
        }
    }
}

// Create application instance
const bracketApp = new BracketDesktopApp();

// App event handlers
app.whenReady().then(() => {
    bracketApp.initialize();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        bracketApp.initialize();
    }
});

app.on('before-quit', async (event) => {
    if (!bracketApp.isQuitting) {
        event.preventDefault();
        await bracketApp.cleanup();
        app.quit();
    }
});

// Handle errors
process.on('uncaughtException', (error) => {
    log.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    log.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// File: standalone/electron/preload.js (NEW FILE)
const { contextBridge, ipcRenderer } = require('electron');

// Expose safe APIs to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
    platform: process.platform,
    versions: {
        node: process.versions.node,
        chrome: process.versions.chrome,
        electron: process.versions.electron
    },
    
    // App specific APIs can be added here
    openExternal: (url) => {
        // This would need to be implemented via IPC if needed
        console.log('Would open external URL:', url);
    }
});

// Prevent context menu in production
if (process.env.NODE_ENV === 'production') {
    window.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });
}
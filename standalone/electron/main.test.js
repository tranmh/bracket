import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { fileURLToPath } from 'node:url';

// main.js is a CommonJS Electron entry point with side effects and no exports.
// To unit test it without Electron we evaluate its source with a fake `require`,
// a fake `process` and append an export of the class and the singleton instance.
const DIR = path.dirname(fileURLToPath(import.meta.url));
const MAIN_PATH = path.join(DIR, 'main.js');
const SOURCE = fs.readFileSync(MAIN_PATH, 'utf8');

function createFakeChildProcess() {
    const child = new EventEmitter();
    child.stdout = new EventEmitter();
    child.stderr = new EventEmitter();
    child.killed = false;
    child.kill = vi.fn();
    return child;
}

class FakeBrowserWindow extends EventEmitter {
    constructor(options) {
        super();
        this.options = options;
        this.loadURL = vi.fn();
        this.show = vi.fn();
        this.webContents = {
            setWindowOpenHandler: vi.fn(),
            openDevTools: vi.fn(),
            executeJavaScript: vi.fn(),
            reload: vi.fn(),
        };
        FakeBrowserWindow.instances.push(this);
    }
}
FakeBrowserWindow.instances = [];
FakeBrowserWindow.getAllWindows = vi.fn(() => FakeBrowserWindow.instances);

function loadMain({
    argv = ['electron', '.'],
    platform = 'win32',
    env = { PATH: '/usr/bin', NODE_ENV: 'test' },
    resourcesPath = '/opt/bracket/resources',
    existsSync = vi.fn(() => true),
    fetchImpl = vi.fn(),
    withContextBridge = true,
} = {}) {
    FakeBrowserWindow.instances = [];
    FakeBrowserWindow.getAllWindows = vi.fn(() => FakeBrowserWindow.instances);

    const appHandlers = {};
    let readyCallback = null;
    const app = {
        whenReady: vi.fn(() => ({
            then: (cb) => {
                readyCallback = cb;
            },
        })),
        on: vi.fn((event, cb) => {
            appHandlers[event] = cb;
        }),
        quit: vi.fn(),
    };
    const Menu = {
        buildFromTemplate: vi.fn((template) => ({ template })),
        setApplicationMenu: vi.fn(),
    };
    const dialog = { showErrorBox: vi.fn(), showMessageBox: vi.fn() };
    const shell = { openExternal: vi.fn() };
    const electron = {
        app,
        BrowserWindow: FakeBrowserWindow,
        Menu,
        dialog,
        shell,
        ipcMain: {},
        ipcRenderer: {},
    };
    if (withContextBridge) {
        electron.contextBridge = { exposeInMainWorld: vi.fn() };
    }

    const log = {
        transports: { file: {}, console: {} },
        info: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        debug: vi.fn(),
    };
    const children = [];
    const spawn = vi.fn(() => {
        const child = createFakeChildProcess();
        children.push(child);
        return child;
    });

    const processHandlers = {};
    const proc = {
        argv,
        platform,
        env,
        resourcesPath,
        versions: { node: '18.0.0', chrome: '118.0', electron: '27.0.0' },
        on: vi.fn((event, cb) => {
            processHandlers[event] = cb;
        }),
    };
    const fakeWindow = { addEventListener: vi.fn() };

    const modules = {
        electron,
        path,
        child_process: { spawn },
        'electron-log': log,
        fs: { existsSync },
        'node-fetch': fetchImpl,
    };
    const fakeRequire = (name) => {
        if (!Object.prototype.hasOwnProperty.call(modules, name)) {
            throw new Error(`unexpected require: ${name}`);
        }
        return modules[name];
    };
    const module = { exports: {} };
    const fn = new Function(
        'require',
        'module',
        'exports',
        '__dirname',
        '__filename',
        'process',
        'window',
        `${SOURCE}\nmodule.exports = { BracketDesktopApp, bracketApp };`
    );
    fn(fakeRequire, module, module.exports, DIR, MAIN_PATH, proc, fakeWindow);

    return {
        ...module.exports,
        app,
        appHandlers,
        getReadyCallback: () => readyCallback,
        Menu,
        dialog,
        shell,
        electron,
        log,
        spawn,
        children,
        proc,
        processHandlers,
        fakeWindow,
        existsSync,
        fetchImpl,
    };
}

function okResponse() {
    return { ok: true, status: 200 };
}

function notOkResponse() {
    return { ok: false, status: 503 };
}

describe('main.js module setup', () => {
    it('configures electron-log levels', () => {
        const { log } = loadMain();
        expect(log.transports.file.level).toBe('info');
        expect(log.transports.console.level).toBe('debug');
    });

    it('initializes the app once electron is ready', () => {
        const ctx = loadMain();
        const init = vi.spyOn(ctx.bracketApp, 'initialize').mockResolvedValue(undefined);
        expect(ctx.app.whenReady).toHaveBeenCalledTimes(1);
        ctx.getReadyCallback()();
        expect(init).toHaveBeenCalledTimes(1);
    });

    it('quits when all windows are closed on non-macOS platforms', () => {
        const ctx = loadMain({ platform: 'win32' });
        ctx.appHandlers['window-all-closed']();
        expect(ctx.app.quit).toHaveBeenCalledTimes(1);
    });

    it('keeps running when all windows are closed on macOS', () => {
        const ctx = loadMain({ platform: 'darwin' });
        ctx.appHandlers['window-all-closed']();
        expect(ctx.app.quit).not.toHaveBeenCalled();
    });

    it('re-initializes on activate when no windows are open', () => {
        const ctx = loadMain();
        const init = vi.spyOn(ctx.bracketApp, 'initialize').mockResolvedValue(undefined);
        ctx.appHandlers.activate();
        expect(init).toHaveBeenCalledTimes(1);
    });

    it('does not re-initialize on activate when a window is open', () => {
        const ctx = loadMain();
        const init = vi.spyOn(ctx.bracketApp, 'initialize').mockResolvedValue(undefined);
        new FakeBrowserWindow({});
        ctx.appHandlers.activate();
        expect(init).not.toHaveBeenCalled();
    });

    it('before-quit prevents the quit, cleans up, then quits when not yet quitting', async () => {
        const ctx = loadMain();
        const cleanup = vi.spyOn(ctx.bracketApp, 'cleanup').mockResolvedValue(undefined);
        const event = { preventDefault: vi.fn() };
        await ctx.appHandlers['before-quit'](event);
        expect(event.preventDefault).toHaveBeenCalledTimes(1);
        expect(cleanup).toHaveBeenCalledTimes(1);
        expect(ctx.app.quit).toHaveBeenCalledTimes(1);
    });

    it('before-quit lets the quit proceed when already quitting', async () => {
        const ctx = loadMain();
        const cleanup = vi.spyOn(ctx.bracketApp, 'cleanup').mockResolvedValue(undefined);
        ctx.bracketApp.isQuitting = true;
        const event = { preventDefault: vi.fn() };
        await ctx.appHandlers['before-quit'](event);
        expect(event.preventDefault).not.toHaveBeenCalled();
        expect(cleanup).not.toHaveBeenCalled();
        expect(ctx.app.quit).not.toHaveBeenCalled();
    });

    it('logs uncaught exceptions and unhandled rejections', () => {
        const ctx = loadMain();
        const err = new Error('boom');
        ctx.processHandlers.uncaughtException(err);
        expect(ctx.log.error).toHaveBeenCalledWith('Uncaught Exception:', err);

        const promise = Promise.resolve();
        ctx.processHandlers.unhandledRejection('reason-x', promise);
        expect(ctx.log.error).toHaveBeenCalledWith('Unhandled Rejection at:', promise, 'reason:', 'reason-x');
    });

    it.skip('aqaa: open bug, see report - loads in the Electron main process, where contextBridge is not available', () => {
        // aqaa: suspected bug - the preload script ("File: standalone/electron/preload.js (NEW FILE)")
        // was pasted at the bottom of main.js. In the main process require('electron').contextBridge
        // is undefined, so loading main.js throws a TypeError.
        expect(() => loadMain({ withContextBridge: false })).not.toThrow();
    });

    it.skip('aqaa: open bug, see report - ships the preload.js referenced by the BrowserWindow and the build config', () => {
        // aqaa: suspected bug - webPreferences.preload and package.json build.files reference preload.js,
        // but the file does not exist (its content was inlined into main.js).
        expect(fs.existsSync(path.join(DIR, 'preload.js'))).toBe(true);
    });
});

describe('BracketDesktopApp constructor', () => {
    it('uses production defaults', () => {
        const { bracketApp } = loadMain();
        expect(bracketApp.mainWindow).toBeNull();
        expect(bracketApp.backendProcess).toBeNull();
        expect(bracketApp.isQuitting).toBe(false);
        expect(bracketApp.serverPort).toBe(8400);
        expect(bracketApp.isDev).toBe(false);
    });

    it('enables dev mode with the --dev flag', () => {
        const { bracketApp } = loadMain({ argv: ['electron', '.', '--dev'] });
        expect(bracketApp.isDev).toBe(true);
    });

    it('does not enable dev mode for similar flags', () => {
        const { bracketApp } = loadMain({ argv: ['electron', '.', '--developer'] });
        expect(bracketApp.isDev).toBe(false);
    });
});

describe('startBackend', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it('rejects when the backend executable does not exist', async () => {
        const ctx = loadMain({ existsSync: vi.fn(() => false) });
        const expectedPath = path.join('/opt/bracket/resources', 'app', 'bracket-backend.exe');
        await expect(ctx.bracketApp.startBackend()).rejects.toThrow(
            `Backend executable not found at: ${expectedPath}`
        );
        expect(ctx.spawn).not.toHaveBeenCalled();
    });

    it('spawns the production backend from the resources path with standalone env', () => {
        const ctx = loadMain();
        ctx.bracketApp.startBackend();
        const expectedPath = path.join('/opt/bracket/resources', 'app', 'bracket-backend.exe');
        expect(ctx.existsSync).toHaveBeenCalledWith(expectedPath);
        expect(ctx.spawn).toHaveBeenCalledTimes(1);
        const [cmd, args, opts] = ctx.spawn.mock.calls[0];
        expect(cmd).toBe(expectedPath);
        expect(args).toEqual([]);
        expect(opts.stdio).toEqual(['pipe', 'pipe', 'pipe']);
        expect(opts.cwd).toBe(path.dirname(expectedPath));
        expect(opts.env).toEqual({
            PATH: '/usr/bin',
            NODE_ENV: 'test',
            BRACKET_STANDALONE: 'true',
            PORT: '8400',
        });
        expect(ctx.bracketApp.backendProcess).toBe(ctx.children[0]);
    });

    it('spawns the backend from ../dist in dev mode', () => {
        const ctx = loadMain({ argv: ['electron', '.', '--dev'] });
        ctx.bracketApp.startBackend();
        const expectedPath = path.join(DIR, '..', 'dist', 'bracket-backend.exe');
        expect(ctx.spawn.mock.calls[0][0]).toBe(expectedPath);
        expect(ctx.spawn.mock.calls[0][2].cwd).toBe(path.dirname(expectedPath));
    });

    it('passes a custom server port as a string', () => {
        const ctx = loadMain();
        ctx.bracketApp.serverPort = 9123;
        ctx.bracketApp.startBackend();
        expect(ctx.spawn.mock.calls[0][2].env.PORT).toBe('9123');
    });

    it('does not mutate process.env', () => {
        const env = { PATH: '/usr/bin' };
        const ctx = loadMain({ env });
        ctx.bracketApp.startBackend();
        expect(env).toEqual({ PATH: '/usr/bin' });
    });

    it.each([
        ['INFO:     Uvicorn running on http://0.0.0.0:8400'],
        ['INFO:     Application startup complete.'],
    ])('resolves when the backend prints %s', async (line) => {
        const ctx = loadMain();
        const promise = ctx.bracketApp.startBackend();
        ctx.children[0].stdout.emit('data', Buffer.from(line));
        // fake timers are not advanced, so only the startup message can resolve the promise
        await expect(promise).resolves.toBeUndefined();
    });

    it('waits for the 10 second fallback when no startup message is printed', async () => {
        const ctx = loadMain();
        const onResolved = vi.fn();
        ctx.bracketApp.startBackend().then(onResolved);
        ctx.children[0].stdout.emit('data', Buffer.from('INFO: Waiting for application startup.'));
        await vi.advanceTimersByTimeAsync(9999);
        expect(onResolved).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(1);
        expect(onResolved).toHaveBeenCalledTimes(1);
    });

    it('logs stdout and stderr output', () => {
        const ctx = loadMain();
        ctx.bracketApp.startBackend();
        ctx.children[0].stdout.emit('data', Buffer.from('hello'));
        ctx.children[0].stderr.emit('data', Buffer.from('warning!'));
        expect(ctx.log.info).toHaveBeenCalledWith('Backend:', 'hello');
        expect(ctx.log.warn).toHaveBeenCalledWith('Backend stderr:', 'warning!');
    });

    it('rejects when the backend process emits an error', async () => {
        const ctx = loadMain();
        const promise = ctx.bracketApp.startBackend();
        const err = new Error('spawn EACCES');
        ctx.children[0].emit('error', err);
        await expect(promise).rejects.toBe(err);
        expect(ctx.log.error).toHaveBeenCalledWith('Backend process error:', err);
    });

    it('shows an error dialog when the backend exits unexpectedly with a non-zero code', () => {
        const ctx = loadMain();
        ctx.bracketApp.startBackend();
        ctx.children[0].emit('close', 1);
        expect(ctx.dialog.showErrorBox).toHaveBeenCalledWith(
            'Backend Error',
            'The tournament system backend has stopped unexpectedly.'
        );
    });

    it('does not show an error dialog when the backend exits with code 0', () => {
        const ctx = loadMain();
        ctx.bracketApp.startBackend();
        ctx.children[0].emit('close', 0);
        expect(ctx.dialog.showErrorBox).not.toHaveBeenCalled();
        expect(ctx.log.info).toHaveBeenCalledWith('Backend process exited with code 0');
    });

    it('does not show an error dialog when the backend exits while quitting', () => {
        const ctx = loadMain();
        ctx.bracketApp.startBackend();
        ctx.bracketApp.isQuitting = true;
        ctx.children[0].emit('close', 143);
        expect(ctx.dialog.showErrorBox).not.toHaveBeenCalled();
    });
});

describe('waitForBackend', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it('resolves as soon as the docs endpoint responds ok', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(okResponse());
        const ctx = loadMain({ fetchImpl });
        await ctx.bracketApp.waitForBackend();
        expect(fetchImpl).toHaveBeenCalledTimes(1);
        expect(fetchImpl).toHaveBeenCalledWith('http://localhost:8400/docs', { timeout: 2000 });
        expect(ctx.log.info).toHaveBeenCalledWith('Backend is ready and responding');
    });

    it('uses the configured server port', async () => {
        const fetchImpl = vi.fn().mockResolvedValue(okResponse());
        const ctx = loadMain({ fetchImpl });
        ctx.bracketApp.serverPort = 9000;
        await ctx.bracketApp.waitForBackend();
        expect(fetchImpl.mock.calls[0][0]).toBe('http://localhost:9000/docs');
    });

    it('retries every second after errors and non-ok responses', async () => {
        const fetchImpl = vi
            .fn()
            .mockRejectedValueOnce(new Error('ECONNREFUSED'))
            .mockResolvedValueOnce(notOkResponse())
            .mockResolvedValueOnce(okResponse());
        const ctx = loadMain({ fetchImpl });
        const onResolved = vi.fn();
        ctx.bracketApp.waitForBackend().then(onResolved);

        await vi.advanceTimersByTimeAsync(0);
        expect(fetchImpl).toHaveBeenCalledTimes(1);
        expect(onResolved).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1000);
        expect(fetchImpl).toHaveBeenCalledTimes(2);
        expect(onResolved).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1000);
        expect(fetchImpl).toHaveBeenCalledTimes(3);
        expect(onResolved).toHaveBeenCalledTimes(1);
        expect(ctx.log.warn).not.toHaveBeenCalled();
    });

    it('gives up after 15 attempts and proceeds anyway', async () => {
        const fetchImpl = vi.fn().mockRejectedValue(new Error('ECONNREFUSED'));
        const ctx = loadMain({ fetchImpl });
        const onResolved = vi.fn();
        const onRejected = vi.fn();
        ctx.bracketApp.waitForBackend().then(onResolved, onRejected);

        await vi.advanceTimersByTimeAsync(13999);
        expect(fetchImpl).toHaveBeenCalledTimes(14);
        expect(onResolved).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1);
        expect(fetchImpl).toHaveBeenCalledTimes(15);
        expect(onResolved).toHaveBeenCalledTimes(1);
        expect(onRejected).not.toHaveBeenCalled();
        expect(ctx.log.warn).toHaveBeenCalledWith('Backend health check failed, proceeding anyway');

        await vi.advanceTimersByTimeAsync(5000);
        expect(fetchImpl).toHaveBeenCalledTimes(15);
    });

    it('succeeds on the last (15th) attempt without warning', async () => {
        const fetchImpl = vi.fn();
        for (let i = 0; i < 14; i++) fetchImpl.mockResolvedValueOnce(notOkResponse());
        fetchImpl.mockResolvedValueOnce(okResponse());
        const ctx = loadMain({ fetchImpl });
        const onResolved = vi.fn();
        ctx.bracketApp.waitForBackend().then(onResolved);
        await vi.advanceTimersByTimeAsync(14000);
        expect(fetchImpl).toHaveBeenCalledTimes(15);
        expect(onResolved).toHaveBeenCalledTimes(1);
        expect(ctx.log.info).toHaveBeenCalledWith('Backend is ready and responding');
        expect(ctx.log.warn).not.toHaveBeenCalled();
    });
});

describe('createMainWindow', () => {
    it('creates a hidden, secure window with the expected size constraints', () => {
        const { bracketApp } = loadMain();
        bracketApp.createMainWindow();
        const win = bracketApp.mainWindow;
        expect(win).toBeInstanceOf(FakeBrowserWindow);
        expect(win.options).toMatchObject({
            width: 1400,
            height: 900,
            minWidth: 1000,
            minHeight: 700,
            show: false,
        });
        expect(win.options.webPreferences).toEqual({
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false,
            preload: path.join(DIR, 'preload.js'),
        });
    });

    it('loads the frontend from the backend in production and keeps devtools closed', () => {
        const { bracketApp } = loadMain();
        bracketApp.createMainWindow();
        expect(bracketApp.mainWindow.loadURL).toHaveBeenCalledWith('http://localhost:8400');
        expect(bracketApp.mainWindow.webContents.openDevTools).not.toHaveBeenCalled();
    });

    it('loads the frontend from the backend on a custom port', () => {
        const { bracketApp } = loadMain();
        bracketApp.serverPort = 8500;
        bracketApp.createMainWindow();
        expect(bracketApp.mainWindow.loadURL).toHaveBeenCalledWith('http://localhost:8500');
    });

    it('loads the live dev server and opens devtools in dev mode', () => {
        const { bracketApp } = loadMain({ argv: ['electron', '.', '--dev'] });
        bracketApp.createMainWindow();
        expect(bracketApp.mainWindow.loadURL).toHaveBeenCalledWith('http://localhost:3000');
        expect(bracketApp.mainWindow.webContents.openDevTools).toHaveBeenCalledTimes(1);
    });

    it('shows the window once it is ready to show', () => {
        const { bracketApp } = loadMain();
        bracketApp.createMainWindow();
        const win = bracketApp.mainWindow;
        expect(win.show).not.toHaveBeenCalled();
        win.emit('ready-to-show');
        expect(win.show).toHaveBeenCalledTimes(1);
        win.emit('ready-to-show');
        expect(win.show).toHaveBeenCalledTimes(1);
    });

    it('clears the window reference when the window is closed', () => {
        const { bracketApp } = loadMain();
        bracketApp.createMainWindow();
        bracketApp.mainWindow.emit('closed');
        expect(bracketApp.mainWindow).toBeNull();
    });

    it('opens new-window links in the external browser and denies in-app windows', () => {
        const ctx = loadMain();
        ctx.bracketApp.createMainWindow();
        const handler = ctx.bracketApp.mainWindow.webContents.setWindowOpenHandler.mock.calls[0][0];
        const result = handler({ url: 'https://example.org/x' });
        expect(ctx.shell.openExternal).toHaveBeenCalledWith('https://example.org/x');
        expect(result).toEqual({ action: 'deny' });
    });
});

describe('setupMenu', () => {
    function setup(opts) {
        const ctx = loadMain(opts);
        ctx.bracketApp.setupMenu();
        const template = ctx.Menu.buildFromTemplate.mock.calls[0][0];
        const find = (top, label) =>
            template.find((m) => m.label === top).submenu.find((i) => i.label === label);
        return { ...ctx, template, find };
    }

    it('builds and installs the application menu', () => {
        const ctx = setup();
        expect(ctx.template.map((m) => m.label)).toEqual(['File', 'View', 'Tournament', 'Help']);
        expect(ctx.Menu.setApplicationMenu).toHaveBeenCalledWith({ template: ctx.template });
    });

    it('provides the standard view roles', () => {
        const ctx = setup();
        const roles = ctx.template
            .find((m) => m.label === 'View')
            .submenu.filter((i) => i.role)
            .map((i) => i.role);
        expect(roles).toEqual([
            'reload',
            'forceReload',
            'toggleDevTools',
            'resetZoom',
            'zoomIn',
            'zoomOut',
            'togglefullscreen',
        ]);
    });

    it('uses Ctrl+Q to exit on non-macOS and Cmd+Q on macOS', () => {
        expect(setup({ platform: 'win32' }).find('File', 'Exit').accelerator).toBe('Ctrl+Q');
        expect(setup({ platform: 'linux' }).find('File', 'Exit').accelerator).toBe('Ctrl+Q');
        expect(setup({ platform: 'darwin' }).find('File', 'Exit').accelerator).toBe('Cmd+Q');
    });

    it.each([
        ['File', 'New Tournament', '/tournaments/new'],
        ['Tournament', 'Dashboard', '/dashboard'],
        ['Tournament', 'Manage Tournaments', '/tournaments'],
    ])('%s > %s navigates the window to %s', (top, label, route) => {
        const ctx = setup();
        ctx.bracketApp.createMainWindow();
        ctx.find(top, label).click();
        const exec = ctx.bracketApp.mainWindow.webContents.executeJavaScript;
        expect(exec).toHaveBeenCalledTimes(1);
        expect(exec.mock.calls[0][0]).toContain(`window.location.href = '${route}';`);
    });

    it.each([
        ['File', 'New Tournament'],
        ['File', 'Refresh'],
        ['Tournament', 'Dashboard'],
        ['Tournament', 'Manage Tournaments'],
    ])('%s > %s does nothing without a main window', (top, label) => {
        const ctx = setup();
        expect(ctx.bracketApp.mainWindow).toBeNull();
        expect(() => ctx.find(top, label).click()).not.toThrow();
    });

    it('File > Refresh reloads the window and uses F5', () => {
        const ctx = setup();
        ctx.bracketApp.createMainWindow();
        const item = ctx.find('File', 'Refresh');
        expect(item.accelerator).toBe('F5');
        item.click();
        expect(ctx.bracketApp.mainWindow.webContents.reload).toHaveBeenCalledTimes(1);
    });

    it('File > New Tournament uses CmdOrCtrl+N', () => {
        expect(setup().find('File', 'New Tournament').accelerator).toBe('CmdOrCtrl+N');
    });

    it('File > Exit marks the app as quitting and quits', () => {
        const ctx = setup();
        ctx.find('File', 'Exit').click();
        expect(ctx.bracketApp.isQuitting).toBe(true);
        expect(ctx.app.quit).toHaveBeenCalledTimes(1);
    });

    it('Help > Documentation and Report Issue open external URLs', () => {
        const ctx = setup();
        ctx.find('Help', 'Documentation').click();
        ctx.find('Help', 'Report Issue').click();
        expect(ctx.shell.openExternal).toHaveBeenNthCalledWith(1, 'https://docs.bracketapp.nl');
        expect(ctx.shell.openExternal).toHaveBeenNthCalledWith(2, 'https://github.com/evroon/bracket/issues');
    });

    it('Help > About shows an info message box attached to the main window', () => {
        const ctx = setup();
        ctx.bracketApp.createMainWindow();
        ctx.find('Help', 'About').click();
        expect(ctx.dialog.showMessageBox).toHaveBeenCalledTimes(1);
        const [parent, opts] = ctx.dialog.showMessageBox.mock.calls[0];
        expect(parent).toBe(ctx.bracketApp.mainWindow);
        expect(opts.type).toBe('info');
        expect(opts.title).toBe('About Bracket Tournament System');
        expect(opts.message).toBe('Bracket Tournament System');
        expect(opts.detail).toContain('Version: 1.0.0');
        expect(opts.detail).toContain('License: AGPL-3.0');
    });
});

describe('showErrorDialog', () => {
    it('delegates to dialog.showErrorBox', () => {
        const ctx = loadMain();
        ctx.bracketApp.showErrorDialog('Title', 'Message');
        expect(ctx.dialog.showErrorBox).toHaveBeenCalledWith('Title', 'Message');
    });
});

describe('initialize', () => {
    it('starts the backend, waits for it, creates the window and the menu in order', async () => {
        const ctx = loadMain();
        const app = ctx.bracketApp;
        const order = [];
        vi.spyOn(app, 'startBackend').mockImplementation(async () => order.push('start'));
        vi.spyOn(app, 'waitForBackend').mockImplementation(async () => order.push('wait'));
        vi.spyOn(app, 'createMainWindow').mockImplementation(() => order.push('window'));
        vi.spyOn(app, 'setupMenu').mockImplementation(() => order.push('menu'));
        await app.initialize();
        expect(order).toEqual(['start', 'wait', 'window', 'menu']);
        expect(ctx.dialog.showErrorBox).not.toHaveBeenCalled();
        expect(ctx.log.info).toHaveBeenCalledWith('Application initialized successfully');
    });

    it('shows an error dialog and stops when the backend cannot be started', async () => {
        const ctx = loadMain({ existsSync: vi.fn(() => false) });
        const app = ctx.bracketApp;
        const wait = vi.spyOn(app, 'waitForBackend');
        const createWindow = vi.spyOn(app, 'createMainWindow');
        await expect(app.initialize()).resolves.toBeUndefined();
        expect(wait).not.toHaveBeenCalled();
        expect(createWindow).not.toHaveBeenCalled();
        expect(ctx.dialog.showErrorBox).toHaveBeenCalledTimes(1);
        const [title, message] = ctx.dialog.showErrorBox.mock.calls[0];
        expect(title).toBe('Initialization Error');
        expect(message).toContain('Failed to start the tournament system:');
        expect(message).toContain('Backend executable not found at:');
        expect(message).toContain('Please try restarting the application.');
        expect(ctx.log.error).toHaveBeenCalledWith('Failed to initialize application:', expect.any(Error));
    });

    it('shows an error dialog when creating the window fails', async () => {
        const ctx = loadMain();
        const app = ctx.bracketApp;
        vi.spyOn(app, 'startBackend').mockResolvedValue(undefined);
        vi.spyOn(app, 'waitForBackend').mockResolvedValue(undefined);
        vi.spyOn(app, 'createMainWindow').mockImplementation(() => {
            throw new Error('GPU process crashed');
        });
        const menu = vi.spyOn(app, 'setupMenu');
        await app.initialize();
        expect(menu).not.toHaveBeenCalled();
        expect(ctx.dialog.showErrorBox.mock.calls[0][1]).toContain('GPU process crashed');
    });
});

describe('cleanup', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it('marks the app as quitting when no backend is running', async () => {
        const { bracketApp } = loadMain();
        await expect(bracketApp.cleanup()).resolves.toBeUndefined();
        expect(bracketApp.isQuitting).toBe(true);
    });

    it('sends SIGTERM and does not force kill a process that terminated', async () => {
        const { bracketApp } = loadMain();
        const child = createFakeChildProcess();
        child.kill.mockImplementation(() => {
            child.killed = true;
        });
        bracketApp.backendProcess = child;
        await bracketApp.cleanup();
        expect(child.kill).toHaveBeenCalledTimes(1);
        expect(child.kill).toHaveBeenCalledWith('SIGTERM');
        vi.advanceTimersByTime(3000);
        expect(child.kill).toHaveBeenCalledTimes(1);
    });

    it('force kills the backend with SIGKILL after 3 seconds when it is not killed', async () => {
        const { bracketApp } = loadMain();
        const child = createFakeChildProcess();
        bracketApp.backendProcess = child;
        await bracketApp.cleanup();
        vi.advanceTimersByTime(2999);
        expect(child.kill).toHaveBeenCalledTimes(1);
        vi.advanceTimersByTime(1);
        expect(child.kill).toHaveBeenCalledTimes(2);
        expect(child.kill).toHaveBeenLastCalledWith('SIGKILL');
    });

    it('does not force kill when the backend reference was cleared meanwhile', async () => {
        const { bracketApp } = loadMain();
        const child = createFakeChildProcess();
        bracketApp.backendProcess = child;
        await bracketApp.cleanup();
        bracketApp.backendProcess = null;
        vi.advanceTimersByTime(3000);
        expect(child.kill).toHaveBeenCalledTimes(1);
    });

    it.skip('aqaa: open bug, see report - force kills a backend that ignores SIGTERM (Node ChildProcess semantics)', async () => {
        // aqaa: suspected bug - Node sets ChildProcess.killed = true as soon as the signal was
        // delivered, not when the process exited. A backend that ignores SIGTERM is still running
        // (exitCode === null) but `killed` is true, so the SIGKILL fallback never fires.
        const { bracketApp } = loadMain();
        const child = createFakeChildProcess();
        child.exitCode = null;
        child.signalCode = null;
        child.kill.mockImplementation(() => {
            child.killed = true; // signal delivered, process keeps running
            return true;
        });
        bracketApp.backendProcess = child;
        await bracketApp.cleanup();
        vi.advanceTimersByTime(3000);
        expect(child.kill).toHaveBeenLastCalledWith('SIGKILL');
    });
});

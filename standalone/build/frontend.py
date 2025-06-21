# File: standalone/build/frontend.py (SIMPLIFIED VERSION - Replace your current one)
import subprocess
import os
import sys
import shutil
from pathlib import Path

def create_professional_frontend():
    """Create a professional static frontend (skip npm entirely)"""
    
    print("[INFO] Creating professional static frontend...")
    
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "standalone" / "dist" / "frontend"
    
    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a professional HTML page
    index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bracket Tournament System</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏆</text></svg>">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container { 
            max-width: 800px; 
            margin: 20px;
            background: rgba(255,255,255,0.1); 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            backdrop-filter: blur(20px);
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .logo { 
            font-size: 4em; 
            margin-bottom: 20px;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
            margin-bottom: 30px;
        }
        
        .status {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 15px;
            margin: 30px 0;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .btn {
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 15px 30px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 12px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 10px 15px;
            transition: all 0.3s ease;
            font-size: 16px;
            font-weight: 500;
            min-width: 200px;
        }
        
        .btn:hover {
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.2);
        }
        
        .btn.primary {
            background: rgba(76, 175, 80, 0.8);
            border-color: rgba(76, 175, 80, 1);
        }
        
        .btn.primary:hover {
            background: rgba(76, 175, 80, 1);
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 30px;
            text-align: center;
        }
        
        .feature {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🏆</div>
        <h1>Bracket Tournament System</h1>
        <p class="subtitle">Desktop Edition - Standalone Version</p>
        
        <div class="status" id="status">
            <div class="pulse">
                <div class="spinner"></div>
                <span style="margin-left: 10px;">Connecting to tournament system...</span>
            </div>
        </div>
        
        <div>
            <a href="http://localhost:8400/" class="btn primary" id="mainBtn">
                Launch Tournament System
            </a>
            <a href="http://localhost:8400/docs" class="btn" id="apiBtn">
                API Documentation
            </a>
        </div>
        
        <div class="features">
            <div class="feature">
                <h3>✅ No Installation</h3>
                <p>Ready to run out of the box</p>
            </div>
            <div class="feature">
                <h3>📱 Works Offline</h3>
                <p>No internet connection required</p>
            </div>
            <div class="feature">
                <h3>💾 Portable</h3>
                <p>Single file, take it anywhere</p>
            </div>
        </div>
        
        <div style="margin-top: 40px; font-size: 0.9em; opacity: 0.7;">
            <p>Professional tournament management made simple</p>
        </div>
    </div>

    <script>
        let connected = false;
        let retryCount = 0;
        const maxRetries = 30;
        
        async function checkBackend() {
            const statusDiv = document.getElementById('status');
            
            if (connected) return;
            
            retryCount++;
            
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3000);
                
                const response = await fetch('http://localhost:8400/', { 
                    signal: controller.signal,
                    mode: 'no-cors'
                });
                
                clearTimeout(timeoutId);
                
                // If we get here without error, server is running
                connected = true;
                statusDiv.innerHTML = `
                    <div style="color: #4CAF50;">
                        <strong>✅ Tournament system ready!</strong><br>
                        <span style="font-size: 0.9em;">Click "Launch Tournament System" to start</span>
                    </div>
                `;
                statusDiv.style.background = 'rgba(76, 175, 80, 0.2)';
                statusDiv.style.borderColor = 'rgba(76, 175, 80, 0.5)';
                
            } catch (error) {
                if (retryCount < maxRetries) {
                    const dots = '.'.repeat((retryCount % 3) + 1);
                    statusDiv.innerHTML = `
                        <div class="pulse">
                            <div class="spinner"></div>
                            <span style="margin-left: 10px;">Starting tournament system${dots}</span><br>
                            <small style="opacity: 0.7;">Attempt ${retryCount}/${maxRetries}</small>
                        </div>
                    `;
                    setTimeout(checkBackend, 2000);
                } else {
                    statusDiv.innerHTML = `
                        <div style="color: #ff9800;">
                            <strong>⚠️ Connection timeout</strong><br>
                            <span style="font-size: 0.9em;">Backend may still be starting. Try clicking the buttons below.</span>
                        </div>
                    `;
                    statusDiv.style.background = 'rgba(255, 152, 0, 0.2)';
                    statusDiv.style.borderColor = 'rgba(255, 152, 0, 0.5)';
                }
            }
        }
        
        // Start checking immediately
        checkBackend();
        
        // Add click handlers
        document.getElementById('mainBtn').onclick = function(e) {
            if (!connected && retryCount < 5) {
                e.preventDefault();
                alert('Tournament system is still starting up. Please wait a moment and try again.');
                return false;
            }
        };
        
        document.getElementById('apiBtn').onclick = function(e) {
            if (!connected && retryCount < 5) {
                e.preventDefault();
                alert('Tournament system is still starting up. Please wait a moment and try again.');
                return false;
            }
        };
    </script>
</body>
</html>'''
    
    # Write the HTML file
    (output_dir / "index.html").write_text(index_html, encoding='utf-8')
    
    print(f"[OK] Professional frontend created at: {output_dir}")
    print("[INFO] Frontend will connect to your backend automatically")
    return True

def build_frontend_static():
    """Build static frontend - skip npm entirely due to dependency conflicts"""
    
    print("[INFO] Building frontend static files...")
    print("[INFO] Skipping npm due to dependency conflicts - using professional fallback")
    
    return create_professional_frontend()

if __name__ == "__main__":
    success = build_frontend_static()
    sys.exit(0 if success else 1)
# File: standalone/build/backend.py (ENHANCED VERSION)
import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_all_dependencies():
    """Install both original backend dependencies and standalone requirements"""
    
    print("📦 Installing all required dependencies...")
    
    # Install original backend requirements first
    backend_requirements = Path(__file__).parent.parent.parent / "backend" / "requirements.txt"
    if backend_requirements.exists():
        print("📥 Installing original backend requirements...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "-r", str(backend_requirements)
        ], check=True)
    
    # Install standalone requirements
    standalone_requirements = Path(__file__).parent.parent / "requirements.txt"
    print("📥 Installing standalone requirements...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "-r", str(standalone_requirements)
    ], check=True)
    
    # Install some additional common dependencies
    additional_deps = [
        "uvicorn[standard]",  # Include standard uvicorn with all features
        "gunicorn",           # Alternative ASGI server
    ]
    
    for dep in additional_deps:
        try:
            print(f"📥 Installing {dep}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", dep
            ], check=True)
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to install {dep}, continuing...")

def find_main_file():
    """Find the correct backend entry point"""
    
    backend_dir = Path(__file__).parent.parent.parent / "backend"
    
    # Check for our created main.py first
    main_file = backend_dir / "main.py"
    if main_file.exists():
        print(f"✅ Using main.py")
        return main_file
    
    # Fallback to other options
    possible_main_files = ["app.py", "server.py", "run.py", "start.py"]
    
    for filename in possible_main_files:
        main_file = backend_dir / filename
        if main_file.exists():
            print(f"✅ Found main file: {filename}")
            return main_file
    
    print("❌ No suitable main file found!")
    return None

def create_enhanced_main_file():
    """Create an enhanced main.py with better error handling"""
    
    backend_dir = Path(__file__).parent.parent.parent / "backend"
    main_file = backend_dir / "main.py"
    
    print("📝 Creating enhanced main.py file...")
    
    main_content = '''"""
Bracket Tournament System - Standalone Server Entry Point
Enhanced version with better dependency handling
"""

import os
import sys
import time

# Set standalone mode early
os.environ['BRACKET_STANDALONE'] = 'true'

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'uvicorn',
        'fastapi', 
        'sqlalchemy',
        'databases',
        'aiosqlite'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} available")
        except ImportError:
            missing.append(module)
            print(f"❌ {module} missing")
    
    if missing:
        print(f"\\n❌ Missing dependencies: {', '.join(missing)}")
        print("💡 The executable may need to be rebuilt with these dependencies")
        return False
    
    return True

def find_app():
    """Find the FastAPI app instance with comprehensive search"""
    
    print("🔍 Searching for FastAPI application...")
    
    # Comprehensive list of possible import paths
    possible_imports = [
        # Standard patterns
        ("bracket.app", "app"),
        ("bracket.main", "app"), 
        ("bracket.server", "app"),
        ("bracket.api", "app"),
        ("bracket.backend", "app"),
        ("bracket.core.app", "app"),
        ("bracket.core.main", "app"),
        
        # Alternative patterns
        ("app", "app"),
        ("main", "app"), 
        ("server", "app"),
        ("api", "app"),
        
        # Check for application factory patterns
        ("bracket.app", "create_app"),
        ("bracket.main", "create_app"),
        ("bracket", "app"),
    ]
    
    for module_name, app_name in possible_imports:
        try:
            print(f"🔍 Trying {module_name}.{app_name}...")
            module = __import__(module_name, fromlist=[app_name])
            app = getattr(module, app_name, None)
            
            if app:
                # Check if it's actually a FastAPI app
                if hasattr(app, 'openapi') or 'FastAPI' in str(type(app)):
                    print(f"✅ Found FastAPI app: {module_name}.{app_name}")
                    return app, f"{module_name}:{app_name}"
                elif callable(app):
                    # Might be an app factory
                    try:
                        app_instance = app()
                        if hasattr(app_instance, 'openapi'):
                            print(f"✅ Found FastAPI app factory: {module_name}.{app_name}")
                            return app_instance, f"{module_name}:{app_name}"
                    except:
                        pass
                        
        except ImportError as e:
            print(f"⚠️ Could not import {module_name}: {e}")
            continue
        except Exception as e:
            print(f"⚠️ Error loading {module_name}: {e}")
            continue
    
    return None, None

def start_server():
    """Start the uvicorn server"""
    
    print("🚀 Starting Bracket Tournament System (Standalone Mode)")
    print(f"📍 Python executable: {sys.executable}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔧 Standalone mode: {os.getenv('BRACKET_STANDALONE', 'false')}")
    
    # Check dependencies
    if not check_dependencies():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Import uvicorn here (after dependency check)
    try:
        import uvicorn
        print("✅ uvicorn imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import uvicorn: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Try to find the FastAPI app
    app, app_string = find_app()
    
    if app and app_string:
        print(f"✅ Starting server with {app_string}")
        print("🌐 Server will be available at: http://127.0.0.1:8400")
        print("📚 API documentation at: http://127.0.0.1:8400/docs")
        
        try:
            # Start uvicorn server
            uvicorn.run(
                app_string,
                host="127.0.0.1",
                port=8400,
                log_level="info",
                access_log=True,
                reload=False
            )
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
    else:
        print("❌ Could not find FastAPI app!")
        print("\\n🔍 Please check that your FastAPI app is properly defined")
        print("💡 The app should be importable and named 'app'")
        
        # Give some debug information
        print("\\n📁 Current directory contents:")
        try:
            for item in os.listdir('.'):
                if item.endswith('.py'):
                    print(f"  📄 {item}")
        except:
            pass
            
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\\n👋 Server stopped by user")
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
'''
    
    main_file.write_text(main_content)
    print(f"✅ Created enhanced {main_file}")
    
    return main_file

def build_backend_executable():
    """Build standalone backend executable with comprehensive dependencies"""
    
    print("🔧 Building backend executable...")
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    backend_dir = project_root / "backend"
    output_dir = project_root / "standalone" / "dist"
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Install all dependencies
    install_all_dependencies()
    
    # Find or create main file
    main_file = find_main_file()
    if not main_file:
        main_file = create_enhanced_main_file()
    
    if not main_file or not main_file.exists():
        print("❌ Could not find or create main file")
        return False
    
    print(f"🎯 Using main file: {main_file}")
    
    # Comprehensive PyInstaller arguments
    pyinstaller_args = [
        str(main_file),
        "--onefile",
        "--name=bracket-backend",
        f"--distpath={output_dir}",
        "--workpath=" + str(output_dir / "build"),
        "--specpath=" + str(output_dir / "build"),
        "--console",  # Keep console for now to see errors
        "--clean",
    ]
    
    # Comprehensive hidden imports
    hidden_imports = [
        # Core web framework
        "uvicorn",
        "uvicorn.main",
        "uvicorn.config",
        "uvicorn.server",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off", 
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.workers",
        
        # FastAPI and related
        "fastapi",
        "fastapi.applications",
        "fastapi.routing",
        "fastapi.middleware",
        "pydantic",
        "starlette",
        "starlette.applications",
        "starlette.routing",
        "starlette.middleware",
        
        # Database support
        "aiosqlite",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "sqlalchemy.sql.default_comparator",
        "databases",
        
        # Additional common imports
        "heliclockter",
        "email_validator",
        "python_multipart",
        "python_jose",
        "passlib",
        
        # JSON handling
        "orjson",
        "ujson",
        
        # HTTP clients
        "httpx",
        "requests",
    ]
    
    for import_name in hidden_imports:
        pyinstaller_args.extend(["--hidden-import", import_name])
    
    # Add data files
    data_dirs = ["static", "templates", "migrations"]
    for data_dir in data_dirs:
        data_path = backend_dir / data_dir
        if data_path.exists():
            pyinstaller_args.append(f"--add-data={data_path};{data_dir}")
    
    # Run PyInstaller
    print("🏗️ Running PyInstaller with comprehensive dependencies...")
    env = os.environ.copy()
    env['BRACKET_STANDALONE'] = 'true'
    
    result = subprocess.run(
        ["pyinstaller"] + pyinstaller_args,
        cwd=str(backend_dir),
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ PyInstaller failed:")
        print("STDOUT:", result.stdout[-2000:])  # Last 2000 chars
        print("STDERR:", result.stderr[-2000:])  # Last 2000 chars
        return False
    
    # Verify executable was created
    exe_path = output_dir / "bracket-backend.exe"
    if exe_path.exists():
        print(f"✅ Backend executable created: {exe_path}")
        print(f"📏 Size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    else:
        print("❌ Executable not found after build")
        return False

if __name__ == "__main__":
    success = build_backend_executable()
    sys.exit(0 if success else 1)
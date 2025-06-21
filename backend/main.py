# File: backend/main.py (FIXED VERSION - Replace your current one)
"""
Bracket Tournament System - Standalone Server Entry Point
Windows console compatible version (no emoji characters)
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
            print(f"[OK] {module} available")
        except ImportError:
            missing.append(module)
            print(f"[ERROR] {module} missing")
    
    if missing:
        print(f"\n[ERROR] Missing dependencies: {', '.join(missing)}")
        print("[INFO] The executable may need to be rebuilt with these dependencies")
        return False
    
    return True

def find_app():
    """Find the FastAPI app instance with comprehensive search"""
    
    print("[INFO] Searching for FastAPI application...")
    
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
            print(f"[INFO] Trying {module_name}.{app_name}...")
            module = __import__(module_name, fromlist=[app_name])
            app = getattr(module, app_name, None)
            
            if app:
                # Check if it's actually a FastAPI app
                if hasattr(app, 'openapi') or 'FastAPI' in str(type(app)):
                    print(f"[OK] Found FastAPI app: {module_name}.{app_name}")
                    return app, f"{module_name}:{app_name}"
                elif callable(app):
                    # Might be an app factory
                    try:
                        app_instance = app()
                        if hasattr(app_instance, 'openapi'):
                            print(f"[OK] Found FastAPI app factory: {module_name}.{app_name}")
                            return app_instance, f"{module_name}:{app_name}"
                    except:
                        pass
                        
        except ImportError as e:
            print(f"[WARN] Could not import {module_name}: {e}")
            continue
        except Exception as e:
            print(f"[WARN] Error loading {module_name}: {e}")
            continue
    
    return None, None

def start_server():
    """Start the uvicorn server"""
    
    print("=" * 60)
    print("BRACKET TOURNAMENT SYSTEM - STANDALONE MODE")
    print("=" * 60)
    print(f"Python executable: {sys.executable}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Standalone mode: {os.getenv('BRACKET_STANDALONE', 'false')}")
    print("=" * 60)
    
    # Check dependencies
    print("\n[INFO] Checking dependencies...")
    if not check_dependencies():
        print("\n[ERROR] Dependency check failed!")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Import uvicorn here (after dependency check)
    try:
        import uvicorn
        print("[OK] uvicorn imported successfully")
    except ImportError as e:
        print(f"[ERROR] Failed to import uvicorn: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Try to find the FastAPI app
    app, app_string = find_app()
    
    if app and app_string:
        print(f"\n[OK] Starting server with {app_string}")
        print("[INFO] Server will be available at: http://127.0.0.1:8400")
        print("[INFO] API documentation at: http://127.0.0.1:8400/docs")
        print("\n[INFO] Starting web server...")
        print("=" * 60)
        
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
            print(f"\n[ERROR] Failed to start server: {e}")
            input("Press Enter to exit...")
            sys.exit(1)
    else:
        print("\n[ERROR] Could not find FastAPI app!")
        print("\n[INFO] Please check that your FastAPI app is properly defined")
        print("[INFO] The app should be importable and named 'app'")
        
        # Give some debug information
        print("\n[DEBUG] Current directory contents:")
        try:
            for item in os.listdir('.'):
                if item.endswith('.py'):
                    print(f"  - {item}")
        except:
            pass
            
        input("Press Enter to exit...")
        sys.exit(1)

def main():
    """Main entry point"""
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
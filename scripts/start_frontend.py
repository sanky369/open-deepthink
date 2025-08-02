#!/usr/bin/env python3
"""
Script to start the Streamlit frontend for Open Deep Think.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_streamlit_installed():
    """Check if Streamlit is installed."""
    try:
        import streamlit
        return True
    except ImportError:
        return False

def install_frontend_dependencies():
    """Install frontend dependencies."""
    print("📦 Installing frontend dependencies...")
    
    frontend_requirements = project_root / "frontend" / "requirements.txt"
    
    if frontend_requirements.exists():
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(frontend_requirements)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Frontend dependencies installed successfully!")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    else:
        print(f"❌ Requirements file not found: {frontend_requirements}")
        return False

def main():
    """Start the Streamlit frontend."""
    print("🚀 Starting Open Deep Think Frontend...")
    print()
    
    # Check if Streamlit is installed
    if not check_streamlit_installed():
        print("⚠️  Streamlit not found. Installing frontend dependencies...")
        if not install_frontend_dependencies():
            print("❌ Failed to install dependencies. Please install manually:")
            print("   pip install -r frontend/requirements.txt")
            return 1
    
    # Check if backend is running
    print("🔍 Checking if backend is running...")
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running at http://localhost:8000")
        else:
            print("⚠️  Backend returned unexpected status code")
    except requests.exceptions.RequestException:
        print("⚠️  Backend doesn't seem to be running at http://localhost:8000")
        print("   Please start the backend first with: python scripts/start_server.py")
        print("   The frontend will still start but won't be able to connect.")
    
    print()
    print("🎨 Starting Streamlit frontend...")
    print("   Frontend will be available at: http://localhost:8501")
    print("   Press Ctrl+C to stop")
    print()
    
    # Start Streamlit
    frontend_app = project_root / "frontend" / "streamlit_app.py"
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(frontend_app),
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped.")
        return 0
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
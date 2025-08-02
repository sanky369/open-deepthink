#!/usr/bin/env python3
"""
Script to start the Open Deep Think server.
"""
import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings


def main():
    """Start the FastAPI server."""
    settings = get_settings()
    
    print(f"Starting {settings.app_name} server...")
    print(f"Debug mode: {settings.debug}")
    print(f"Pipeline timeout: {settings.pipeline_timeout}s")
    print(f"Default thinking paths: {settings.default_n_paths}")
    
    # Check if API key is configured
    if not settings.gemini_api_key or settings.gemini_api_key == "test_key_placeholder":
        print("\n⚠️  WARNING: No valid Gemini API key configured!")
        print("   Set GEMINI_API_KEY environment variable or update .env file")
        print("   The server will start but API calls will fail.\n")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )


if __name__ == "__main__":
    main()
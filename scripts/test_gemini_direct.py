#!/usr/bin/env python3
"""
Direct Gemini API test script to isolate connection issues.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from clients.gemini import GeminiClient
from app.config import get_settings


async def test_gemini_direct():
    """Test Gemini API directly."""
    print("🧪 Testing Gemini API connection directly...")
    
    try:
        # Get settings
        settings = get_settings()
        print(f"✅ Configuration loaded")
        print(f"   API Key: {settings.gemini_api_key[:8]}..." if settings.gemini_api_key else "❌ No API key")
        
        # Create client
        client = GeminiClient(
            api_key=settings.gemini_api_key,
            timeout=30,
            model_name="gemini-2.5-pro"
        )
        print(f"✅ Client created")
        
        # Test simple prompt
        print("\n🤖 Testing simple prompt...")
        response = await client.generate_content_async(
            "Hello! Please respond with 'Hi there' to test the connection.",
            temperature=0.0,
            max_tokens=2048
        )
        
        print(f"✅ Response received: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_different_prompts():
    """Test different types of prompts."""
    settings = get_settings()
    client = GeminiClient(
        api_key=settings.gemini_api_key,
        timeout=10,  # Shorter timeout for testing
        model_name="gemini-2.5-pro"
    )
    
    test_prompts = [
        "Hi",
        "What is 1+1?",
        "Tell me a joke",
        "Explain gravity briefly",
        "The sky is blue because"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n🧪 Test {i}: '{prompt}'")
        try:
            response = await client.generate_content_async(
                prompt,
                temperature=0.7,
                max_tokens=2048
            )
            print(f"✅ Success: {response[:100]}{'...' if len(response) > 100 else ''}")
        except Exception as e:
            print(f"❌ Failed: {e}")


def main():
    """Main test function."""
    print("🔍 Gemini API Direct Test")
    print("=" * 50)
    
    # Test basic connection
    result = asyncio.run(test_gemini_direct())
    
    if result:
        print("\n🎉 Basic connection works! Testing different prompts...")
        asyncio.run(test_different_prompts())
    else:
        print("\n❌ Basic connection failed. Please check:")
        print("   1. API key is valid and active")
        print("   2. Internet connection is working")
        print("   3. Gemini API service is available")
        print("   4. No firewall blocking the requests")


if __name__ == "__main__":
    main()
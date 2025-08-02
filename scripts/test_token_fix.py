#!/usr/bin/env python3
"""
Test script to verify the Gemini API token limit fix.
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from clients.gemini import GeminiClient
from app.config import get_settings


async def test_token_limits():
    """Test that various token limits work without empty responses."""
    print("🧪 Testing Gemini API Token Limit Fix...")
    
    try:
        # Get settings
        settings = get_settings()
        
        # Create client
        client = GeminiClient(
            api_key=settings.gemini_api_key,
            timeout=60,
            model_name="gemini-2.5-pro"
        )
        
        # Test cases with different complexities
        test_cases = [
            {
                "name": "Simple Query",
                "prompt": "What is 2+2?",
                "max_tokens": 1000,
                "expected_success": True
            },
            {
                "name": "Medium Complexity",
                "prompt": "Explain quantum entanglement in detail with examples.",
                "max_tokens": 3000,
                "expected_success": True
            },
            {
                "name": "Complex Creative Task",
                "prompt": "Write a haiku where the second letter of each word spells 'BUDDHA'. Make it poetic and meaningful.",
                "max_tokens": 6000,
                "expected_success": True
            },
            {
                "name": "Very Complex Reasoning",
                "prompt": "Explain the philosophical implications of consciousness, the hard problem of consciousness, and different theories including integrated information theory, global workspace theory, and panpsychism. Provide examples and compare their strengths and weaknesses.",
                "max_tokens": 8000,
                "expected_success": True
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['name']}")
            print(f"   Max tokens: {test_case['max_tokens']}")
            
            try:
                response = await client.generate_content_async(
                    test_case["prompt"],
                    temperature=0.7,
                    max_tokens=test_case["max_tokens"]
                )
                
                success = len(response.strip()) > 0
                results.append({
                    "test": test_case["name"],
                    "success": success,
                    "response_length": len(response),
                    "error": None
                })
                
                if success:
                    print(f"   ✅ Success: {len(response)} characters generated")
                    print(f"   📝 Preview: {response[:100]}...")
                else:
                    print(f"   ❌ Failed: Empty response (old bug)")
                    
            except Exception as e:
                results.append({
                    "test": test_case["name"],
                    "success": False,
                    "response_length": 0,
                    "error": str(e)
                })
                print(f"   ❌ Error: {e}")
        
        # Summary
        print(f"\n📊 Test Results Summary:")
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        
        print(f"   Successful: {successful}/{total}")
        print(f"   Success Rate: {(successful/total)*100:.1f}%")
        
        if successful == total:
            print("\n🎉 All tests passed! Token limit fix is working.")
            return True
        else:
            print(f"\n⚠️  {total - successful} tests failed. Check for remaining issues.")
            return False
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False


def main():
    """Main test function."""
    print("🔧 Gemini API Token Limit Fix Verification")
    print("=" * 50)
    
    success = asyncio.run(test_token_limits())
    
    if success:
        print("\n✅ Fix verification complete - system should work properly now!")
        print("🚀 You can restart your server and test complex queries.")
    else:
        print("\n❌ Some issues remain. Check the test results above.")


if __name__ == "__main__":
    main()
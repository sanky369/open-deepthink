#!/usr/bin/env python3
"""
Simple Deep Think pipeline test with reduced parameters.
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.dependencies import get_pipeline
from app.config import get_settings


async def test_pipeline_simple():
    """Test the pipeline with simple parameters."""
    print("🧠 Testing Deep Think Pipeline (Simple)...")
    
    try:
        # Get settings
        settings = get_settings()
        print(f"✅ Configuration loaded")
        
        # Get pipeline
        pipeline = await get_pipeline()
        print(f"✅ Pipeline initialized")
        
        # Test with reduced parameters
        test_query = "What is 2+2?"
        
        print(f"\n🤖 Testing query: '{test_query}'")
        print("⚙️  Parameters: n_paths=2, top_k=2, timeout=120s")
        
        result = await pipeline.run(
            query=test_query,
            n_paths=2,  # Reduced from 8 to 2
            max_iterations=1,
            top_k=2,    # Reduced from 3 to 2
            timeout=120  # Standard timeout
        )
        
        print(f"✅ Pipeline completed successfully!")
        print(f"📝 Answer: {result.get('final_answer', 'No answer')}")
        print(f"⏱️  Execution time: {result.get('execution_time', 0):.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


def main():
    """Main test function."""
    print("🔍 Deep Think Pipeline Simple Test")
    print("=" * 50)
    
    result = asyncio.run(test_pipeline_simple())
    
    if result:
        print("\n🎉 Pipeline test successful! You can try more complex queries.")
    else:
        print("\n❌ Pipeline test failed. Check backend logs for details.")


if __name__ == "__main__":
    main()
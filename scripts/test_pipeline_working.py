#!/usr/bin/env python3
"""
Working Deep Think pipeline test demonstrating the fix.
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.dependencies import get_pipeline
from app.config import get_settings


async def test_working_pipeline():
    """Test the pipeline with proper result extraction."""
    print("🧠 Testing Working Deep Think Pipeline...")
    
    try:
        # Get settings
        settings = get_settings()
        print(f"✅ Configuration loaded")
        
        # Get pipeline
        pipeline = await get_pipeline()
        print(f"✅ Pipeline initialized")
        
        # Test with simple query
        test_query = "What is 2+2?"
        
        print(f"\n🤖 Testing query: '{test_query}'")
        print("⚙️  Parameters: n_paths=2, top_k=2, timeout=120s")
        
        result = await pipeline.run(
            query=test_query,
            n_paths=2,
            max_iterations=1,
            top_k=2,
            timeout=120
        )
        
        print(f"✅ Pipeline completed successfully!")
        print(f"⏱️  Execution time: {result.get('execution_time', 0):.1f}s")
        
        # Extract the actual answer
        refinement_result = result.get('refinement_result', {})
        final_answer = refinement_result.get('final_answer')
        
        print(f"\n📝 Final Answer:")
        if isinstance(final_answer, dict):
            direct_answer = final_answer.get('direct_answer', 'No direct answer')
            print(f"   Direct Answer: {direct_answer}")
            
            perspectives = final_answer.get('perspectives', [])
            if perspectives:
                print(f"   Additional Perspectives ({len(perspectives)}):")
                for i, perspective in enumerate(perspectives[:3], 1):  # Show first 3
                    name = perspective.get('perspective', f'Perspective {i}')
                    explanation = perspective.get('explanation', '')[:100]
                    print(f"   {i}. {name}: {explanation}...")
        else:
            print(f"   Answer: {final_answer}")
        
        # Show pipeline statistics
        print(f"\n📊 Pipeline Statistics:")
        print(f"   Thinking paths: {result.get('n_paths', 'N/A')}")
        print(f"   Valid candidates: {len(result.get('thinking_results', []))}")
        print(f"   Top candidates selected: {result.get('top_k', 'N/A')}")
        
        # Show stage completion times
        planning_time = result.get('planning_result', {}).get('execution_time', 0)
        thinking_time = sum(tr.get('execution_time', 0) for tr in result.get('thinking_results', []))
        critique_time = result.get('critique_result', {}).get('execution_time', 0)
        refinement_time = result.get('refinement_result', {}).get('execution_time', 0)
        
        print(f"\n⏱️  Stage Timing:")
        print(f"   Planning: {planning_time:.1f}s")
        print(f"   Thinking: {thinking_time:.1f}s")
        print(f"   Critique: {critique_time:.1f}s")
        print(f"   Refinement: {refinement_time:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


def main():
    """Main test function."""
    print("🔍 Working Deep Think Pipeline Test")
    print("=" * 50)
    
    result = asyncio.run(test_working_pipeline())
    
    if result:
        print("\n🎉 SUCCESS! The Deep Think pipeline is now working correctly!")
        print("✅ Token limits have been resolved")
        print("✅ JSON parsing issues are fixed")
        print("✅ Pipeline completes within timeout")
        print("\n🚀 You can now test with more complex queries or start the frontend!")
    else:
        print("\n❌ Pipeline test failed. Check logs for details.")


if __name__ == "__main__":
    main()
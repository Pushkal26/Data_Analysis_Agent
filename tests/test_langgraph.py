"""
Test script for LangGraph Pipeline
===================================
Tests the analysis pipeline with sample data.

Usage:
    # Set your API key first
    export OPENAI_API_KEY="sk-..."
    
    # Run the test
    cd pushkal
    python -m tests.test_langgraph
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")


def test_pipeline():
    """Test the analysis pipeline with sample data."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        print("   You can also use Ollama by setting LLM_PROVIDER=ollama")
        return False
    
    from pipeline import run_analysis_sync
    
    # Sample file metadata (as would come from database)
    sample_files = [
        {
            "id": 1,
            "filename": "sales_nov_2024.csv",
            "filepath": str(project_root / "data" / "sales_nov_2024.csv"),
            "time_period": "Nov 2024",
            "time_period_type": "monthly",
            "row_count": 10,
            "columns": ["Order ID", "Customer ID", "Order Date", "Region", "Product", 
                       "Units", "Unit Price", "Discount", "Revenue", "Delivery Date", "Meta"],
            "numeric_columns": ["Order ID", "Units", "Unit Price", "Discount", "Revenue"],
            "categorical_columns": ["Customer ID", "Region", "Product", "Meta"],
            "date_columns": ["Order Date", "Delivery Date"],
        },
        {
            "id": 2,
            "filename": "sales_dec_2024.csv",
            "filepath": str(project_root / "data" / "sales_dec_2024.csv"),
            "time_period": "Dec 2024",
            "time_period_type": "monthly",
            "row_count": 12,
            "columns": ["Order ID", "Customer ID", "Order Date", "Region", "Product", 
                       "Units", "Unit Price", "Discount", "Revenue", "Delivery Date", "Meta"],
            "numeric_columns": ["Order ID", "Units", "Unit Price", "Discount", "Revenue"],
            "categorical_columns": ["Customer ID", "Region", "Product", "Meta"],
            "date_columns": ["Order Date", "Delivery Date"],
        },
    ]
    
    # Test query
    test_queries = [
        "What is the average revenue by region for November 2024?",
        # "Compare revenue between Nov and Dec 2024 by region",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        try:
            result = run_analysis_sync(
                session_id="test-session",
                user_query=query,
                available_files=sample_files,
                chat_history=[],
            )
            
            print(f"\n✅ Analysis Complete!")
            print(f"\n📊 Intent: {result.get('intent')}")
            print(f"📊 Operation Type: {result.get('operation_type')}")
            print(f"📊 Files Used: {result.get('files_to_use')}")
            
            if result.get('generated_code'):
                print(f"\n📝 Generated Code:")
                print("-" * 40)
                print(result.get('generated_code')[:500] + "..." if len(result.get('generated_code', '')) > 500 else result.get('generated_code'))
            
            if result.get('result_data'):
                print(f"\n📈 Result Data:")
                print("-" * 40)
                import json
                print(json.dumps(result.get('result_data'), indent=2, default=str)[:500])
            
            print(f"\n💬 Response:")
            print("-" * 40)
            print(result.get('final_response', result.get('explanation', 'No response generated')))
            
            if result.get('errors'):
                print(f"\n⚠️ Errors: {result.get('errors')}")
            
            print(f"\n🔍 Node History: {result.get('node_history', [])}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    print("🧪 Testing LangGraph Pipeline...")
    print(f"📁 Project Root: {project_root}")
    print(f"🤖 LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    
    success = test_pipeline()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


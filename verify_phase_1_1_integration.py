"""
Verification test for LEARNING_GAPS Phase 1.1: PromptEnhancer Integration

Tests that PromptEnhancer can be imported and initialized.
"""
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

def test_prompt_enhancer_import():
    """Test that PromptEnhancer can be imported."""
    print("\n--- Test 1: PromptEnhancer Import ---")
    
    try:
        from src.learning.prompt_enhancer import get_prompt_enhancer, GenerationPromptEnhancer
        print("✅ PromptEnhancer imports available")
        return True
    except ImportError as e:
        print(f"❌ PromptEnhancer imports not available: {e}")
        return False

def test_prompt_enhancer_singleton():
    """Test that PromptEnhancer singleton can be created."""
    print("\n--- Test 2: PromptEnhancer Singleton ---")
    
    try:
        from src.learning.prompt_enhancer import get_prompt_enhancer
        enhancer = get_prompt_enhancer()
        print(f"✅ PromptEnhancer singleton created: {type(enhancer).__name__}")
        return True
    except Exception as e:
        print(f"❌ PromptEnhancer initialization failed: {e}")
        return False

def test_code_generation_service_integration():
    """Test that CodeGenerationService has PromptEnhancer integration."""
    print("\n--- Test 3: CodeGenerationService Integration ---")
    
    try:
        # Just check if the methods exist (don't instantiate service)
        from src.services.code_generation_service import CodeGenerationService
        
        # Check if helper methods exist
        assert hasattr(CodeGenerationService, '_extract_entity_name_from_task'), \
            "❌ _extract_entity_name_from_task method missing"
        assert hasattr(CodeGenerationService, '_extract_endpoint_pattern_from_task'), \
            "❌ _extract_endpoint_pattern_from_task method missing"
        assert hasattr(CodeGenerationService, '_extract_schema_name_from_task'), \
            "❌ _extract_schema_name_from_task method missing"
        
        print("✅ All helper methods present in CodeGenerationService")
        return True
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("LEARNING_GAPS Phase 1.1 Verification Test")
    print("=" * 70)
    
    results = []
    results.append(("PromptEnhancer Import", test_prompt_enhancer_import()))
    results.append(("PromptEnhancer Singleton", test_prompt_enhancer_singleton()))
    results.append(("CodeGenerationService Integration", test_code_generation_service_integration()))
    
    print("\n" + "=" * 70)
    print("RESULTS:")
    print("=" * 70)
    
    all_passed = all(result for _, result in results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print("=" * 70)
    if all_passed:
        print("✅ Phase 1.1 Integration: VERIFIED")
        print("\nNext Steps:")
        print("1. Run E2E pipeline: python tests/e2e/real_e2e_full_pipeline.py")
        print("2. Check logs for '🎓 Prompt enhanced' messages")
        print("3. Verify anti-patterns are injected into prompts")
    else:
        print("❌ Phase 1.1 Integration: FAILED")
        print("\nFix the failing tests before proceeding.")
    print("=" * 70)

#!/usr/bin/env python3
"""Simple validation script for keyword modules."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_imports():
    """Test that modules can be imported successfully."""
    print("Testing basic imports...")
    
    try:
        from seo_bot.keywords.score import SearchIntent, IntentClassifier, KeywordScorer
        print("✓ Score module imports work")
    except Exception as e:
        print(f"✗ Score module import failed: {e}")
        return False
    
    return True

def test_intent_classification():
    """Test intent classification without external dependencies."""
    print("Testing intent classification...")
    
    try:
        from seo_bot.keywords.score import IntentClassifier, SearchIntent
        
        classifier = IntentClassifier()
        
        # Test informational queries
        intent, confidence = classifier.classify_intent("how to bake bread")
        print(f"  'how to bake bread' -> {intent.value} ({confidence:.2f})")
        assert intent == SearchIntent.INFORMATIONAL
        
        # Test transactional queries
        intent, confidence = classifier.classify_intent("buy organic bread near me")
        print(f"  'buy organic bread near me' -> {intent.value} ({confidence:.2f})")
        assert intent == SearchIntent.TRANSACTIONAL
        
        # Test commercial queries
        intent, confidence = classifier.classify_intent("best bread maker reviews")
        print(f"  'best bread maker reviews' -> {intent.value} ({confidence:.2f})")
        # Should be commercial or informational
        assert intent in [SearchIntent.COMMERCIAL, SearchIntent.INFORMATIONAL]
        
        print("✓ Intent classification works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Intent classification failed: {e}")
        return False

def test_keyword_scoring():
    """Test keyword scoring functionality."""
    print("Testing keyword scoring...")
    
    try:
        from seo_bot.keywords.score import KeywordScorer
        
        scorer = KeywordScorer()
        
        # Test scoring without external data
        result = scorer.score_keyword("plumber near me")
        print(f"  Scored 'plumber near me':")
        print(f"    Intent: {result.intent.value} (confidence: {result.intent_confidence:.2f})")
        print(f"    Value score: {result.value_score:.2f}")
        print(f"    Difficulty: {result.difficulty_proxy:.2f} ({result.competition_level})")
        print(f"    Final score: {result.final_score:.2f}")
        
        # Verify reasonable values
        assert 0 <= result.value_score <= 10
        assert 0 <= result.difficulty_proxy <= 1
        assert 0 <= result.final_score <= 10
        
        print("✓ Keyword scoring works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Keyword scoring failed: {e}")
        return False

def test_module_structure():
    """Test that module structure is correct."""
    print("Testing module structure...")
    
    expected_files = [
        "src/seo_bot/keywords/__init__.py",
        "src/seo_bot/keywords/score.py",
        "src/seo_bot/keywords/discover.py", 
        "src/seo_bot/keywords/serp_gap.py",
    ]
    
    all_exist = True
    for file_path in expected_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all validation tests."""
    print("SEO-Bot Keywords Module Validation")
    print("=" * 40)
    
    tests = [
        test_module_structure,
        test_basic_imports,
        test_intent_classification,
        test_keyword_scoring,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()
    
    print("=" * 40)
    print(f"Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed!")
        print("\nThe keyword modules are ready for use. To use them:")
        print("1. Install dependencies: pip install -r requirements.txt (if exists) or poetry install")
        print("2. Set up environment variables for APIs (optional)")
        print("3. Initialize database: python -c 'from src.seo_bot.db import init_db; init_db()'")
        return 0
    else:
        print("❌ Some validation tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
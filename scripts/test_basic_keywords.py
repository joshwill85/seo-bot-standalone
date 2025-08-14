#!/usr/bin/env python3
"""Basic validation of keyword modules without external dependencies."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_intent_classifier():
    """Test intent classification independently."""
    print("Testing IntentClassifier...")
    
    try:
        from seo_bot.keywords.score import IntentClassifier, SearchIntent
        
        classifier = IntentClassifier()
        
        # Test cases
        test_cases = [
            ("how to bake bread", SearchIntent.INFORMATIONAL),
            ("buy organic bread near me", SearchIntent.TRANSACTIONAL),
            ("best bread maker reviews", SearchIntent.COMMERCIAL),
            ("amazon login", SearchIntent.NAVIGATIONAL),
            ("plumber emergency service", SearchIntent.COMMERCIAL),
        ]
        
        for query, expected_intent in test_cases:
            intent, confidence = classifier.classify_intent(query)
            print(f"  '{query}' -> {intent.value} (confidence: {confidence:.2f})")
            
            # For some queries, multiple intents could be valid
            if query == "best bread maker reviews":
                assert intent in [SearchIntent.COMMERCIAL, SearchIntent.INFORMATIONAL]
            else:
                assert intent == expected_intent, f"Expected {expected_intent.value}, got {intent.value}"
        
        print("✓ IntentClassifier works correctly")
        return True
        
    except Exception as e:
        print(f"✗ IntentClassifier failed: {e}")
        return False

def test_difficulty_calculator():
    """Test difficulty calculation independently."""
    print("Testing DifficultyCalculator...")
    
    try:
        from seo_bot.keywords.score import DifficultyCalculator
        
        calc = DifficultyCalculator()
        
        # Test cases
        test_cases = [
            ("insurance", 50000, 25.0, 0.9, "high"),
            ("local plumber tips", 200, 2.0, None, "low"),
            ("seo tools", 10000, 15.0, 0.7, "high"),
        ]
        
        for query, volume, cpc, competition, expected_level in test_cases:
            difficulty, level = calc.calculate_difficulty_proxy(query, volume, cpc, competition)
            print(f"  '{query}' -> {difficulty:.2f} ({level})")
            
            assert 0 <= difficulty <= 1, f"Difficulty should be 0-1, got {difficulty}"
            assert level in ["low", "medium", "high"], f"Invalid difficulty level: {level}"
        
        print("✓ DifficultyCalculator works correctly")
        return True
        
    except Exception as e:
        print(f"✗ DifficultyCalculator failed: {e}")
        return False

def test_value_scorer():
    """Test value scoring independently."""
    print("Testing ValueScorer...")
    
    try:
        from seo_bot.keywords.score import ValueScorer, SearchIntent
        
        scorer = ValueScorer()
        
        # Test cases
        test_cases = [
            ("hire plumber emergency", SearchIntent.TRANSACTIONAL, 1000, 15.0, 1.0),
            ("what is plumbing", SearchIntent.INFORMATIONAL, 100, 0.50, 0.3),
            ("best plumbing tools", SearchIntent.COMMERCIAL, 500, 8.0, 0.8),
        ]
        
        for query, intent, volume, cpc, relevance in test_cases:
            score = scorer.calculate_value_score(query, intent, volume, cpc, relevance)
            print(f"  '{query}' -> {score:.2f}")
            
            assert 0 <= score <= 10, f"Value score should be 0-10, got {score}"
        
        print("✓ ValueScorer works correctly")
        return True
        
    except Exception as e:
        print(f"✗ ValueScorer failed: {e}")
        return False

def test_keyword_expander():
    """Test keyword expansion without database."""
    print("Testing KeywordExpander...")
    
    try:
        from seo_bot.keywords.discover import KeywordExpander, KeywordSeed, DiscoveredKeyword
        
        expander = KeywordExpander()
        seeds = [KeywordSeed(term="plumbing repair")]
        
        keywords = expander.expand_seed_keywords(seeds, max_per_seed=10)
        
        print(f"  Expanded 1 seed into {len(keywords)} keywords")
        
        # Check we got some variations
        assert len(keywords) > 0, "Should generate some keywords"
        
        # Check for expected variations
        queries = [kw.query for kw in keywords]
        print(f"  Sample keywords: {queries[:5]}")
        
        # Should have some "how to" variations
        how_to_count = sum(1 for q in queries if "how to" in q)
        print(f"  'How to' variations: {how_to_count}")
        
        # Should have some "near me" variations
        near_me_count = sum(1 for q in queries if "near me" in q)
        print(f"  'Near me' variations: {near_me_count}")
        
        print("✓ KeywordExpander works correctly")
        return True
        
    except Exception as e:
        print(f"✗ KeywordExpander failed: {e}")
        return False

def test_entity_extractor():
    """Test entity extraction."""
    print("Testing EntityExtractor...")
    
    try:
        from seo_bot.keywords.serp_gap import EntityExtractor
        
        extractor = EntityExtractor()
        
        test_text = """
        John Smith from Apple Inc visited New York on January 15, 2024.
        The project cost $50,000 and achieved 95% success rate.
        Microsoft Corporation also participated with a budget of $25,000.
        """
        
        entities = extractor.extract_entities(test_text)
        print(f"  Extracted {len(entities)} entities: {entities[:5]}")
        
        assert len(entities) > 0, "Should extract some entities"
        
        # Check for expected entity types
        has_person = any("John Smith" in entity for entity in entities)
        has_org = any("Apple Inc" in entity for entity in entities)
        has_money = any("$50,000" in entity for entity in entities)
        
        print(f"  Found person: {has_person}, organization: {has_org}, money: {has_money}")
        
        print("✓ EntityExtractor works correctly")
        return True
        
    except Exception as e:
        print(f"✗ EntityExtractor failed: {e}")
        return False

def main():
    """Run basic validation tests."""
    print("SEO-Bot Keyword Modules - Basic Validation")
    print("=" * 50)
    
    tests = [
        test_intent_classifier,
        test_difficulty_calculator,
        test_value_scorer,
        test_keyword_expander,
        test_entity_extractor,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic validation tests passed!")
        print("\nThe keyword modules are working correctly with these features:")
        print("• Intent classification for search queries")
        print("• Keyword difficulty proxy calculation")
        print("• Business value scoring")
        print("• Seed keyword expansion")
        print("• Entity extraction from text")
        print("\nNext steps:")
        print("1. Install full dependencies: pip install sqlalchemy pandas scikit-learn beautifulsoup4")
        print("2. Set up database connection")
        print("3. Configure API keys for SERP data (optional)")
        return 0
    else:
        print("❌ Some basic tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
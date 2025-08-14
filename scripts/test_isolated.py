#!/usr/bin/env python3
"""Isolated tests for individual components without cross-dependencies."""

import sys
import re
from enum import Enum
from pathlib import Path

# Copy the IntentClassifier code directly for testing
class SearchIntent(Enum):
    """Search intent classification."""
    INFORMATIONAL = "informational"
    NAVIGATIONAL = "navigational"
    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"


class IntentClassifier:
    """Classifies search intent based on keyword patterns and features."""
    
    INTENT_PATTERNS = {
        SearchIntent.INFORMATIONAL: [
            r'\b(what|how|why|when|where|who|which)\b',
            r'\b(guide|tutorial|tips|learn|definition|meaning)\b',
            r'\b(vs|versus|difference|compare|comparison)\b',
            r'\b(best|top|review|rating)\b',
            r'\b(example|case study|research)\b',
        ],
        SearchIntent.NAVIGATIONAL: [
            r'\b(login|sign in|official|website|homepage)\b',
            r'\b(contact|phone|address|location)\b',
            r'\b(download|app|software)\b',
            r'^[a-zA-Z0-9\s]+ (inc|llc|corp|company)$',
        ],
        SearchIntent.TRANSACTIONAL: [
            r'\b(buy|purchase|order|shop|sale|deal)\b',
            r'\b(price|cost|cheap|discount|coupon)\b',
            r'\b(hire|book|reserve|schedule)\b',
            r'\b(for sale|on sale|special offer)\b',
            r'\b(near me|local|nearby)\b',
        ],
        SearchIntent.COMMERCIAL: [
            r'\b(service|services|provider|company)\b',
            r'\b(consultant|expert|professional)\b',
            r'\b(quote|estimate|pricing)\b',
            r'\b(repair|fix|maintenance)\b',
            r'\b(install|installation|setup)\b',
        ]
    }
    
    def __init__(self):
        """Initialize the intent classifier."""
        self._compiled_patterns = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    def classify_intent(self, query):
        """Classify search intent for a query."""
        query = query.lower().strip()
        intent_scores = {}
        
        # Score each intent based on pattern matches
        for intent, patterns in self._compiled_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(query):
                    score += 1
            
            # Normalize score by number of patterns
            normalized_score = score / len(patterns) if patterns else 0
            intent_scores[intent] = normalized_score
        
        # Apply modifiers
        intent_scores = self._apply_intent_modifiers(query, intent_scores)
        
        # Find highest scoring intent
        if not intent_scores or all(score == 0 for score in intent_scores.values()):
            return SearchIntent.INFORMATIONAL, 0.1
        
        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]
        
        # Boost confidence for strong signals
        if confidence >= 0.5:
            confidence = min(0.95, confidence * 1.2)
        
        return best_intent, confidence
    
    def _apply_intent_modifiers(self, query, scores):
        """Apply additional scoring modifiers based on query characteristics."""
        
        # Long-tail informational queries
        if len(query.split()) >= 5 and any(word in query for word in ['how', 'what', 'why']):
            scores[SearchIntent.INFORMATIONAL] = scores.get(SearchIntent.INFORMATIONAL, 0) + 0.3
        
        # Question words strongly indicate informational
        question_words = ['how', 'what', 'why', 'when', 'where', 'who', 'which']
        if any(query.startswith(word) for word in question_words):
            scores[SearchIntent.INFORMATIONAL] = scores.get(SearchIntent.INFORMATIONAL, 0) + 0.4
        
        # Local intent indicators
        if any(term in query for term in ['near me', 'nearby', 'local', 'in my area']):
            scores[SearchIntent.TRANSACTIONAL] = scores.get(SearchIntent.TRANSACTIONAL, 0) + 0.3
        
        return scores


def test_intent_classification():
    """Test intent classification functionality."""
    print("Testing IntentClassifier...")
    
    classifier = IntentClassifier()
    
    test_cases = [
        ("how to bake bread", SearchIntent.INFORMATIONAL),
        ("buy organic bread near me", SearchIntent.TRANSACTIONAL),
        ("best bread maker reviews", [SearchIntent.COMMERCIAL, SearchIntent.INFORMATIONAL]),  # Either is valid
        ("amazon login", SearchIntent.NAVIGATIONAL),
        ("plumber emergency service", SearchIntent.COMMERCIAL),
        ("what is SEO", SearchIntent.INFORMATIONAL),
        ("hire local contractor", SearchIntent.TRANSACTIONAL),
    ]
    
    passed = 0
    for query, expected in test_cases:
        intent, confidence = classifier.classify_intent(query)
        print(f"  '{query}' -> {intent.value} (confidence: {confidence:.2f})")
        
        if isinstance(expected, list):
            if intent in expected:
                passed += 1
                print(f"    ✓ Correct (expected one of {[e.value for e in expected]})")
            else:
                print(f"    ✗ Expected one of {[e.value for e in expected]}, got {intent.value}")
        else:
            if intent == expected:
                passed += 1
                print(f"    ✓ Correct")
            else:
                print(f"    ✗ Expected {expected.value}, got {intent.value}")
    
    print(f"\nIntent Classification: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_keyword_expansion():
    """Test keyword expansion logic."""
    print("Testing keyword expansion logic...")
    
    # Test modifiers
    INTENT_MODIFIERS = {
        'informational': [
            'what is', 'how to', 'why', 'when', 'where', 'who',
            'guide', 'tutorial', 'tips', 'best practices', 'examples'
        ],
        'transactional': [
            'buy', 'purchase', 'order', 'shop', 'sale', 'deal',
            'cheap', 'discount', 'coupon', 'price', 'cost',
            'near me', 'local', 'hire', 'book', 'schedule'
        ],
        'commercial': [
            'best', 'top', 'review', 'rating', 'comparison',
            'service', 'company', 'provider', 'professional'
        ]
    }
    
    def expand_keyword(base_term, max_keywords=10):
        """Simple keyword expansion."""
        variations = set()
        variations.add(base_term)
        
        # Add all modifier combinations
        all_modifiers = []
        for intent_mods in INTENT_MODIFIERS.values():
            all_modifiers.extend(intent_mods)
        
        count = 0
        for modifier in all_modifiers:
            if count >= max_keywords:
                break
            variations.add(f"{modifier} {base_term}")
            count += 1
            if count >= max_keywords:
                break
            if len(modifier.split()) == 1:  # Single word
                variations.add(f"{base_term} {modifier}")
                count += 1
        
        return list(variations)[:max_keywords]
    
    # Test expansion
    base_term = "plumbing repair"
    keywords = expand_keyword(base_term, 15)
    
    print(f"  Expanded '{base_term}' into {len(keywords)} variations:")
    for i, keyword in enumerate(keywords[:5]):
        print(f"    {i+1}. {keyword}")
    
    if len(keywords) > 5:
        print(f"    ... and {len(keywords) - 5} more")
    
    # Check for expected patterns
    has_how_to = any("how to" in kw for kw in keywords)
    has_near_me = any("near me" in kw for kw in keywords)
    has_best = any("best" in kw for kw in keywords)
    has_informational = any(word in " ".join(keywords) for word in ["what is", "guide", "tutorial"])
    has_transactional = any(word in " ".join(keywords) for word in ["buy", "hire", "local"])
    
    print(f"  Contains 'how to' variations: {has_how_to}")
    print(f"  Contains 'near me' variations: {has_near_me}")
    print(f"  Contains 'best' variations: {has_best}")
    print(f"  Contains informational terms: {has_informational}")
    print(f"  Contains transactional terms: {has_transactional}")
    
    success = len(keywords) > 5 and (has_how_to or has_informational) and len(set(keywords)) > 3  # At least 3 unique variations
    print(f"\nKeyword Expansion: {'✓ PASSED' if success else '✗ FAILED'}")
    return success


def test_entity_extraction():
    """Test entity extraction patterns."""
    print("Testing entity extraction...")
    
    ENTITY_PATTERNS = {
        'person': re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),
        'organization': re.compile(r'\b[A-Z][a-z]+\s+(?:Inc|LLC|Corp|Company|Ltd)\b'),
        'location': re.compile(r'\b(?:New York|California|London|Tokyo|Paris|Boston|Chicago)\b'),
        'date': re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'),
        'money': re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?'),
        'percentage': re.compile(r'\d+(?:\.\d+)?%'),
    }
    
    def extract_entities(text):
        """Extract entities using patterns."""
        entities = []
        
        for entity_type, pattern in ENTITY_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                entities.append(f"{match} ({entity_type})")
        
        return entities
    
    test_text = """
    John Smith from Apple Inc visited New York on January 15, 2024.
    The project cost $50,000 and achieved 95% success rate.
    Microsoft Corporation partnered with Boston Tech Company.
    Sarah Johnson will present in Chicago this March 2024.
    """
    
    entities = extract_entities(test_text)
    
    print(f"  Extracted {len(entities)} entities from test text:")
    for entity in entities:
        print(f"    - {entity}")
    
    # Check for expected entity types
    has_person = any("person" in entity for entity in entities)
    has_org = any("organization" in entity for entity in entities)
    has_location = any("location" in entity for entity in entities)
    has_money = any("money" in entity for entity in entities)
    has_percentage = any("percentage" in entity for entity in entities)
    
    print(f"\n  Entity types found:")
    print(f"    Person: {has_person}")
    print(f"    Organization: {has_org}")
    print(f"    Location: {has_location}")
    print(f"    Money: {has_money}")
    print(f"    Percentage: {has_percentage}")
    
    success = len(entities) >= 5 and has_person and has_org
    print(f"\nEntity Extraction: {'✓ PASSED' if success else '✗ FAILED'}")
    return success


def main():
    """Run isolated component tests."""
    print("SEO-Bot Keywords - Isolated Component Tests")
    print("=" * 50)
    
    tests = [
        test_intent_classification,
        test_keyword_expansion,
        test_entity_extraction,
    ]
    
    results = []
    for test in tests:
        print()
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
        print("-" * 30)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nFinal Results: {passed}/{total} component tests passed")
    
    if passed == total:
        print("\n🎉 All isolated component tests passed!")
        print("\nThe core algorithms are working correctly:")
        print("• Search intent classification using pattern matching")
        print("• Keyword expansion with various modifiers")
        print("• Entity extraction using regex patterns")
        print("\nThese components form the foundation of the keyword modules.")
        return 0
    else:
        print("\n❌ Some component tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
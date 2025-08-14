#!/usr/bin/env python3
"""
Test script to demonstrate SEO bot functionality.
"""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set PYTHONPATH for this script
import os
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "src")

from seo_bot.keywords.score import KeywordScorer, SearchIntent
from seo_bot.keywords.cluster import KeywordClusterManager
from seo_bot.keywords.discover import KeywordDiscoverer, KeywordSeed


def test_keyword_scoring():
    """Test keyword intent classification and scoring."""
    print("🎯 Testing Keyword Scoring...")
    print("-" * 40)
    
    scorer = KeywordScorer()
    
    test_keywords = [
        "how to fix plumbing leak",
        "buy plumbing tools online",
        "best plumber near me",
        "plumbing installation guide",
        "emergency plumber services"
    ]
    
    for keyword in test_keywords:
        result = scorer.score_keyword(keyword)
        print(f"'{keyword}':")
        print(f"  Intent: {result.intent.value} (confidence: {result.intent_confidence:.2f})")
        print(f"  Value Score: {result.value_score:.1f}/10")
        print(f"  Difficulty: {result.difficulty_proxy:.2f}")
        print(f"  Final Score: {result.final_score:.1f}/10")
        print()


def test_keyword_discovery():
    """Test keyword discovery and expansion."""
    print("🔍 Testing Keyword Discovery...")
    print("-" * 40)
    
    discoverer = KeywordDiscoverer()
    seeds = [
        KeywordSeed(term="plumbing repair", priority=1.0),
        KeywordSeed(term="water heater", priority=0.8)
    ]
    
    print("Expanding seed keywords...")
    keywords = discoverer.expander.expand_seed_keywords(seeds)
    
    print(f"Generated {len(keywords)} keyword variations:")
    for i, keyword in enumerate(keywords[:15]):
        print(f"  {i+1:2d}. {keyword.query}")
    
    if len(keywords) > 15:
        print(f"       ... and {len(keywords) - 15} more")
    
    print()


def test_keyword_clustering():
    """Test keyword clustering functionality."""
    print("📊 Testing Keyword Clustering...")
    print("-" * 40)
    
    # Sample keywords for clustering
    keywords = [
        "how to fix leaky faucet",
        "leaky faucet repair guide",
        "stop dripping faucet",
        "faucet won't turn off",
        "water heater not working",
        "electric water heater repair",
        "gas water heater problems",
        "water heater replacement cost",
        "toilet won't flush",
        "toilet repair guide",
        "fix running toilet",
        "replace toilet parts",
        "bathroom plumbing issues",
        "kitchen sink problems",
        "garbage disposal repair",
        "unclog kitchen drain"
    ]
    
    manager = KeywordClusterManager(min_cluster_size=2)
    
    print(f"Clustering {len(keywords)} keywords...")
    results = manager.cluster_keywords(keywords)
    
    print(f"\nFound {results['total_clusters']} clusters:")
    print(f"Noise keywords: {len(results['noise_keywords'])}")
    
    for cluster_id, keywords_list in results['clusters'].items():
        cluster_name = results['labels'].get(cluster_id, f"Cluster {cluster_id}")
        hub_spoke = results['hub_spoke_relationships'].get(cluster_id, {})
        
        print(f"\n📂 {cluster_name} ({len(keywords_list)} keywords)")
        
        if hub_spoke:
            hub = hub_spoke.get('hub_keyword', '')
            spokes = hub_spoke.get('spoke_keywords', [])
            coverage = hub_spoke.get('hub_coverage', 0)
            
            print(f"  🎯 Hub: {hub} (coverage: {coverage:.1%})")
            if spokes:
                print(f"  🔗 Spokes: {', '.join(spokes[:3])}")
                if len(spokes) > 3:
                    print(f"         ... and {len(spokes) - 3} more")
        
        print(f"  📝 All: {', '.join(keywords_list)}")
    
    if results['noise_keywords']:
        print(f"\n🔍 Uncategorized: {', '.join(results['noise_keywords'])}")
    
    print()


def main():
    """Run all tests."""
    print("🚀 SEO Bot Functionality Test")
    print("=" * 50)
    print()
    
    try:
        test_keyword_scoring()
        test_keyword_discovery()
        test_keyword_clustering()
        
        print("✅ All tests completed successfully!")
        print("\nSEO Bot is ready for use. Try these commands:")
        print("  export PYTHONPATH=/Users/petpawlooza/seo-bot/src:$PYTHONPATH")
        print("  python -m seo_bot.cli score 'how to fix plumbing'")
        print("  python -m seo_bot.cli discover --seeds 'plumbing,repair'")
        print("  python -m seo_bot.cli cluster 'fix faucet' 'repair faucet' 'leaky tap' 'water heater' 'boiler repair'")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
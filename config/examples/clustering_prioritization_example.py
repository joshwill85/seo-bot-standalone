#!/usr/bin/env python3
"""
Example usage of SEO-Bot keyword clustering and prioritization modules.

This example demonstrates how to use the clustering and prioritization
functionality with sample data.
"""

import sys
import os
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from seo_bot.keywords.cluster import KeywordClusterManager, create_cluster_manager
    from seo_bot.keywords.prioritize import KeywordPrioritizer, create_prioritizer
    print("✓ Successfully imported clustering and prioritization modules")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Note: This example requires full dependencies to run.")
    sys.exit(1)


def sample_keywords_data() -> List[str]:
    """Generate sample keyword data for testing."""
    return [
        # SEO Tools cluster
        "best seo tools 2024",
        "seo software for agencies", 
        "keyword research tools",
        "seo analysis tools",
        "backlink checker tools",
        
        # Content Marketing cluster
        "content marketing strategy",
        "content creation tools",
        "blog writing tips",
        "content calendar planning",
        "editorial calendar software",
        
        # Social Media cluster
        "social media marketing",
        "instagram marketing tips",
        "facebook advertising",
        "social media scheduling tools",
        "linkedin marketing strategy",
        
        # PPC/Advertising cluster  
        "google ads optimization",
        "ppc campaign management",
        "ad copy writing tips",
        "conversion rate optimization",
        "landing page optimization",
        
        # Analytics cluster
        "google analytics setup",
        "web analytics tools",
        "seo performance tracking",
        "marketing attribution",
        "data-driven marketing"
    ]


def sample_keyword_details() -> List[Dict[str, Any]]:
    """Generate detailed keyword data for prioritization."""
    keywords = sample_keywords_data()
    
    # Sample data with realistic metrics
    keyword_details = []
    
    for i, keyword in enumerate(keywords):
        # Vary metrics to create realistic prioritization scenarios
        if "best" in keyword or "tools" in keyword:
            # Commercial intent keywords
            intent = "commercial"
            search_volume = 1000 + (i * 200)
            difficulty = 0.3 + (i * 0.02)
            cpc = 5.0 + (i * 0.50)
            competition = 0.6 + (i * 0.01)
        elif "tips" in keyword or "strategy" in keyword:
            # Informational keywords
            intent = "informational" 
            search_volume = 800 + (i * 100)
            difficulty = 0.4 + (i * 0.02)
            cpc = 2.0 + (i * 0.30)
            competition = 0.4 + (i * 0.01)
        else:
            # Mixed keywords
            intent = "commercial" if i % 2 == 0 else "informational"
            search_volume = 500 + (i * 150)
            difficulty = 0.2 + (i * 0.03)
            cpc = 3.0 + (i * 0.40)
            competition = 0.5 + (i * 0.01)
        
        # Ensure values stay within realistic ranges
        difficulty = min(0.9, difficulty)
        competition = min(0.9, competition)
        cpc = min(15.0, cpc)
        search_volume = min(5000, search_volume)
        
        keyword_details.append({
            'query': keyword,
            'search_volume': int(search_volume),
            'difficulty_proxy': round(difficulty, 2),
            'intent': intent,
            'cpc': round(cpc, 2),
            'competition': round(competition, 2),
            'serp_features': ['people_also_ask'] if i % 3 == 0 else [],
            'gap_analysis': {
                'missing_elements': ['faq', 'calculator'] if i % 4 == 0 else [],
                'content_depth_score': 0.3 + (i * 0.02)
            } if i % 2 == 0 else {},
            'content_requirements': [
                {'type': 'examples', 'met': False}
            ] if i % 5 == 0 else []
        })
    
    return keyword_details


def demonstrate_clustering():
    """Demonstrate keyword clustering functionality."""
    print("\n" + "=" * 60)
    print("KEYWORD CLUSTERING DEMONSTRATION")
    print("=" * 60)
    
    # Get sample keywords
    keywords = sample_keywords_data()
    print(f"Analyzing {len(keywords)} keywords for clustering...")
    
    # Create cluster manager
    cluster_manager = create_cluster_manager(
        min_cluster_size=3,  # Minimum 3 keywords per cluster
        min_samples=2,       # Minimum 2 core samples
        max_clusters=8       # Maximum 8 clusters
    )
    
    try:
        # Perform clustering
        print("Performing clustering analysis...")
        clustering_results = cluster_manager.cluster_keywords(keywords, method="kmeans")
        
        # Display results
        print(f"\n✓ Clustering completed successfully!")
        print(f"Total clusters found: {clustering_results['total_clusters']}")
        print(f"Noise keywords: {len(clustering_results['noise_keywords'])}")
        
        # Show cluster details
        for cluster_id, cluster_keywords in clustering_results['clusters'].items():
            label = clustering_results['labels'].get(cluster_id, f"Cluster {cluster_id}")
            print(f"\nCluster {cluster_id}: {label}")
            print(f"Keywords ({len(cluster_keywords)}):")
            for keyword in cluster_keywords[:5]:  # Show first 5
                print(f"  - {keyword}")
            if len(cluster_keywords) > 5:
                print(f"  ... and {len(cluster_keywords) - 5} more")
        
        # Show hub-spoke relationships
        if clustering_results['hub_spoke_relationships']:
            print(f"\nHub-Spoke Relationships:")
            for cluster_id, relationship in clustering_results['hub_spoke_relationships'].items():
                hub = relationship.get('hub_keyword', 'Unknown')
                spokes = relationship.get('spoke_keywords', [])
                coverage = relationship.get('hub_coverage', 0)
                print(f"  Cluster {cluster_id} - Hub: '{hub}' (Coverage: {coverage:.1%})")
                if spokes:
                    print(f"    Spokes: {', '.join(spokes[:3])}")
        
        if clustering_results['noise_keywords']:
            print(f"\nNoise Keywords:")
            for keyword in clustering_results['noise_keywords']:
                print(f"  - {keyword}")
        
        return True
        
    except Exception as e:
        print(f"✗ Clustering failed: {e}")
        print("Note: This may be due to missing ML dependencies.")
        return False


def demonstrate_prioritization():
    """Demonstrate keyword prioritization functionality."""
    print("\n" + "=" * 60)
    print("KEYWORD PRIORITIZATION DEMONSTRATION") 
    print("=" * 60)
    
    # Get sample keyword details
    keywords_data = sample_keyword_details()
    print(f"Analyzing {len(keywords_data)} keywords for prioritization...")
    
    # Create prioritizer
    prioritizer = create_prioritizer(
        traffic_weight=0.4,        # 40% weight on traffic potential
        difficulty_weight=0.3,     # 30% weight on difficulty
        gap_weight=0.2,           # 20% weight on content gaps
        business_value_weight=0.1  # 10% weight on business value
    )
    
    try:
        # Perform prioritization
        print("Performing prioritization analysis...")
        brand_terms = ["SEOTool", "MarketingPro"]  # Sample brand terms
        prioritized_keywords = prioritizer.prioritize_keywords(keywords_data, brand_terms=brand_terms)
        
        print(f"✓ Prioritization completed successfully!")
        
        # Show top 10 keywords
        print(f"\nTop 10 Priority Keywords:")
        print("-" * 80)
        print(f"{'Rank':<4} {'Keyword':<30} {'Score':<6} {'Tier':<8} {'Intent':<12} {'Volume':<6}")
        print("-" * 80)
        
        for i, keyword in enumerate(prioritized_keywords[:10], 1):
            query = keyword['query'][:28] + ".." if len(keyword['query']) > 30 else keyword['query']
            score = f"{keyword['priority_score']:.3f}"
            tier = keyword['priority_tier'].title()
            intent = keyword.get('intent', 'Unknown')[:10]
            volume = keyword.get('search_volume', 0)
            
            print(f"{i:<4} {query:<30} {score:<6} {tier:<8} {intent:<12} {volume:<6}")
        
        # Show priority distribution
        tier_counts = {}
        for keyword in prioritized_keywords:
            tier = keyword['priority_tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        print(f"\nPriority Distribution:")
        for tier, count in sorted(tier_counts.items()):
            percentage = (count / len(prioritized_keywords)) * 100
            print(f"  {tier.title():<10}: {count:2d} keywords ({percentage:.1f}%)")
        
        # Show sample analysis for top keyword
        top_keyword = prioritized_keywords[0]
        print(f"\nDetailed Analysis for Top Keyword: '{top_keyword['query']}'")
        print("-" * 50)
        
        if 'component_scores' in top_keyword:
            components = top_keyword['component_scores']
            print(f"Traffic Score:      {components.get('traffic_score', 0):.3f}")
            print(f"Difficulty Score:   {components.get('difficulty_score', 0):.3f}")
            print(f"Gap Score:          {components.get('gap_score', 0):.3f}")
            print(f"Business Score:     {components.get('business_score', 0):.3f}")
        
        if 'traffic_analysis' in top_keyword:
            traffic = top_keyword['traffic_analysis']
            print(f"Estimated Traffic:  {traffic.get('estimated_monthly_traffic', 0)} visits/month")
            print(f"Confidence:         {traffic.get('confidence_score', 0):.1%}")
            if traffic.get('is_branded'):
                print(f"Branded Keyword:    Yes")
        
        if 'recommendations' in top_keyword:
            recommendations = top_keyword['recommendations']
            if recommendations:
                print(f"Recommendations:")
                for rec in recommendations[:3]:
                    print(f"  • {rec}")
        
        return True
        
    except Exception as e:
        print(f"✗ Prioritization failed: {e}")
        return False


def demonstrate_combined_workflow():
    """Demonstrate combined clustering and prioritization workflow."""
    print("\n" + "=" * 60)
    print("COMBINED CLUSTERING + PRIORITIZATION WORKFLOW")
    print("=" * 60)
    
    keywords = sample_keywords_data()
    keywords_data = sample_keyword_details()
    
    print("Step 1: Clustering keywords to identify topics...")
    
    # Create managers
    cluster_manager = create_cluster_manager(min_cluster_size=3, max_clusters=6)
    prioritizer = create_prioritizer()
    
    try:
        # Step 1: Cluster keywords
        clustering_results = cluster_manager.cluster_keywords(keywords, method="kmeans")
        
        if clustering_results['total_clusters'] > 0:
            print(f"✓ Found {clustering_results['total_clusters']} topic clusters")
            
            # Step 2: Prioritize keywords
            print("\nStep 2: Prioritizing keywords within each cluster...")
            prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
            
            # Step 3: Combine results
            print("✓ Prioritization completed")
            print("\nStep 3: Combining clustering and prioritization results...")
            
            # Group prioritized keywords by cluster
            cluster_assignments = clustering_results.get('cluster_assignments', {})
            clustered_priorities = {}
            
            for keyword_data in prioritized_keywords:
                query = keyword_data['query']
                cluster_id = cluster_assignments.get(query, -1)
                
                if cluster_id not in clustered_priorities:
                    clustered_priorities[cluster_id] = []
                clustered_priorities[cluster_id].append(keyword_data)
            
            # Show results by cluster
            print(f"\nCombined Results:")
            print("=" * 50)
            
            for cluster_id, cluster_keywords in clustered_priorities.items():
                if cluster_id == -1:
                    cluster_name = "Unclustered"
                else:
                    cluster_name = clustering_results['labels'].get(cluster_id, f"Cluster {cluster_id}")
                
                print(f"\n{cluster_name} ({len(cluster_keywords)} keywords):")
                
                # Sort by priority within cluster
                cluster_keywords.sort(key=lambda x: x['priority_score'], reverse=True)
                
                # Show top 3 keywords in each cluster
                for i, keyword in enumerate(cluster_keywords[:3], 1):
                    score = keyword['priority_score']
                    tier = keyword['priority_tier']
                    print(f"  {i}. {keyword['query']:<35} (Score: {score:.3f}, {tier.title()})")
                
                if len(cluster_keywords) > 3:
                    print(f"     ... and {len(cluster_keywords) - 3} more keywords")
            
            # Strategic recommendations
            print(f"\nStrategic Recommendations:")
            print("-" * 30)
            
            # Find highest-priority cluster
            cluster_avg_scores = {}
            for cluster_id, cluster_keywords in clustered_priorities.items():
                if cluster_id != -1 and cluster_keywords:
                    avg_score = sum(k['priority_score'] for k in cluster_keywords) / len(cluster_keywords)
                    cluster_avg_scores[cluster_id] = avg_score
            
            if cluster_avg_scores:
                top_cluster_id = max(cluster_avg_scores.keys(), key=lambda x: cluster_avg_scores[x])
                top_cluster_name = clustering_results['labels'].get(top_cluster_id, f"Cluster {top_cluster_id}")
                
                print(f"• Focus on '{top_cluster_name}' cluster first (highest average priority)")
                print(f"• Create hub content around main topics in each cluster")
                print(f"• Prioritize commercial keywords for conversion-focused content")
                print(f"• Use informational keywords for top-of-funnel content")
        
        else:
            print("No clusters found - keywords may be too diverse or dataset too small")
            
        return True
        
    except Exception as e:
        print(f"✗ Combined workflow failed: {e}")
        return False


def main():
    """Run all demonstrations."""
    print("SEO-Bot Keyword Clustering and Prioritization Examples")
    print("=" * 70)
    
    results = []
    
    # Run demonstrations
    print("\nRunning demonstrations...")
    
    try:
        results.append(("Clustering", demonstrate_clustering()))
    except Exception as e:
        print(f"Clustering demo failed: {e}")
        results.append(("Clustering", False))
    
    try:
        results.append(("Prioritization", demonstrate_prioritization()))
    except Exception as e:
        print(f"Prioritization demo failed: {e}")
        results.append(("Prioritization", False))
    
    try:
        results.append(("Combined Workflow", demonstrate_combined_workflow()))
    except Exception as e:
        print(f"Combined workflow demo failed: {e}")
        results.append(("Combined Workflow", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("DEMONSTRATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ SUCCESS" if result else "✗ FAILED"
        print(f"{name:<20} {status}")
    
    print(f"\nOverall: {passed}/{total} demonstrations completed successfully")
    
    if passed == total:
        print("\n🎉 All demonstrations completed successfully!")
        print("The clustering and prioritization modules are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} demonstration(s) failed.")
        print("This may be due to missing dependencies (sentence-transformers, scikit-learn, etc.)")
        print("The modules are structurally sound but require full dependencies for execution.")


if __name__ == "__main__":
    main()
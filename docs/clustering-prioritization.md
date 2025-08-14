# SEO-Bot Keyword Clustering and Prioritization System

This document provides comprehensive documentation for the keyword clustering and prioritization modules added to SEO-Bot.

## Overview

The clustering and prioritization system provides advanced keyword analysis capabilities:

- **Clustering**: Groups semantically similar keywords into topics using ML algorithms
- **Prioritization**: Scores keywords based on traffic potential, difficulty, content gaps, and business value
- **Hub/Spoke Analysis**: Identifies primary keywords and supporting terms within clusters
- **Database Integration**: Seamlessly updates keyword and cluster data in the database

## Architecture

### Core Modules

1. **`cluster.py`** - Keyword clustering functionality
2. **`prioritize.py`** - Keyword prioritization and scoring
3. **Tests** - Comprehensive test coverage for all functionality

### Key Components

```
seo_bot/keywords/
├── cluster.py              # Clustering algorithms and analysis
├── prioritize.py            # Priority scoring and ranking
├── __init__.py             # Updated exports
└── tests/
    ├── test_clustering.py          # Clustering tests
    ├── test_prioritization.py      # Prioritization tests
    └── test_keywords_integration.py # Database integration tests
```

## Installation and Dependencies

### Required Dependencies

The modules require the following Python packages (already in `pyproject.toml`):

```toml
# Core dependencies
numpy = "^1.26.2"
scikit-learn = "^1.3.2"
sentence-transformers = "^2.2.2"  # Optional, with fallback
hdbscan = "^0.8.33"               # Optional, with fallback
nltk = "^3.8.1"                   # Optional, with fallback
sqlalchemy = "^2.0.23"

# Existing dependencies
pandas = "^2.1.4"
```

### Fallback Options

The system provides graceful fallbacks when ML libraries aren't available:

- **No `sentence-transformers`**: Falls back to TF-IDF with SVD embeddings
- **No `hdbscan`**: Falls back to K-means clustering  
- **No `scikit-learn`**: Falls back to Agglomerative clustering
- **No `nltk`**: Uses built-in stopword list

## Usage

### Basic Clustering

```python
from seo_bot.keywords import KeywordClusterManager

# Create cluster manager
cluster_manager = KeywordClusterManager(
    min_cluster_size=3,      # Minimum keywords per cluster
    min_samples=2,           # Minimum core samples for HDBSCAN
    max_clusters=50          # Maximum number of clusters
)

# Cluster keywords
keywords = [
    "best seo tools",
    "seo software reviews", 
    "keyword research tools",
    "content marketing strategy",
    "social media marketing"
]

results = cluster_manager.cluster_keywords(keywords)

print(f"Found {results['total_clusters']} clusters")
print(f"Hub-spoke relationships: {results['hub_spoke_relationships']}")
```

### Basic Prioritization

```python
from seo_bot.keywords import KeywordPrioritizer

# Create prioritizer
prioritizer = KeywordPrioritizer(
    traffic_weight=0.4,        # 40% weight on traffic potential
    difficulty_weight=0.3,     # 30% weight on difficulty
    gap_weight=0.2,           # 20% weight on content gaps  
    business_value_weight=0.1  # 10% weight on business value
)

# Prepare keyword data
keywords_data = [
    {
        'query': 'buy seo software',
        'search_volume': 1500,
        'difficulty_proxy': 0.3,
        'intent': 'transactional',
        'cpc': 8.50,
        'competition': 0.6
    },
    # ... more keywords
]

# Prioritize keywords
prioritized = prioritizer.prioritize_keywords(keywords_data)

for keyword in prioritized[:5]:  # Top 5
    print(f"{keyword['query']}: {keyword['priority_score']:.3f} ({keyword['priority_tier']})")
```

### Database Integration

```python
from sqlalchemy.orm import Session
from seo_bot.keywords import KeywordClusterManager, KeywordPrioritizer

# Clustering with database update
cluster_manager = KeywordClusterManager()
clustering_results = cluster_manager.cluster_keywords(keywords)

# Update database with clusters
created_clusters = cluster_manager.update_database_clusters(
    db=db_session,
    project_id="your-project-id", 
    clustering_results=clustering_results
)

# Prioritization with database update
prioritizer = KeywordPrioritizer()
prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)

updated_count = prioritizer.update_database_priorities(
    db=db_session,
    prioritized_keywords=prioritized_keywords
)
```

### Factory Functions

For convenience, use factory functions with custom configurations:

```python
from seo_bot.keywords import create_cluster_manager, create_prioritizer

# Custom cluster manager
cluster_manager = create_cluster_manager(
    min_cluster_size=5,
    max_clusters=20
)

# Custom prioritizer  
prioritizer = create_prioritizer(
    traffic_weight=0.5,
    difficulty_weight=0.2,
    gap_weight=0.2,
    business_value_weight=0.1
)
```

## Clustering Features

### Embedding Generation

- **Primary**: sentence-transformers for semantic embeddings
- **Fallback**: TF-IDF with SVD dimensionality reduction
- **Output**: 384-dimensional vectors (compatible with sentence-transformers)

### Clustering Algorithms

1. **HDBSCAN** (Primary)
   - Density-based clustering
   - Handles noise and varying cluster sizes
   - Parameters: `min_cluster_size`, `min_samples`, `cluster_selection_epsilon`

2. **K-means** (Fallback)
   - Centroid-based clustering
   - Uses silhouette score for optimal K selection
   - Good for spherical clusters

3. **Agglomerative** (Fallback)
   - Hierarchical clustering
   - Ward linkage for compact clusters
   - Deterministic results

### Cluster Labeling

- **N-gram Analysis**: Extracts meaningful terms from cluster keywords
- **Stopword Filtering**: Removes common words for better labels
- **Frequency Weighting**: Prioritizes common terms within clusters
- **Fallback Logic**: Uses first keyword if no good label found

### Hub-Spoke Analysis

- **Similarity Matrix**: Calculates cosine similarity between keywords
- **Hub Detection**: Identifies keyword with highest average similarity  
- **Spoke Identification**: Finds keywords similar to hub above threshold
- **Coverage Metrics**: Measures how well hub represents cluster

## Prioritization Features

### Traffic Estimation

- **CTR by Position**: Uses industry-standard click-through rates
- **Branded Keywords**: Applies multiplier for brand-related terms
- **Volume Estimation**: Provides fallback estimates when data unavailable
- **Opportunity Calculation**: Accounts for current vs target rankings

### Content Gap Analysis

- **SERP Feature Analysis**: Identifies content opportunities from features
- **Missing Elements**: Detects gaps in existing content
- **Content Depth**: Evaluates content comprehensiveness
- **Gap Weighting**: Applies multiplier for high-opportunity keywords

### Business Value Calculation

- **Intent Detection**: Classifies keywords by search intent
- **Commercial Indicators**: Identifies high-value terms and phrases  
- **CPC Integration**: Uses cost-per-click as value signal
- **Competition Analysis**: Balances competition with opportunity

### Priority Scoring

Final priority score combines:
```
Priority = (Traffic × W₁) + (Difficulty × W₂) + (Gaps × W₃) + (Business × W₄)
```

Where weights (W₁, W₂, W₃, W₄) are customizable and sum to 1.0.

#### Priority Tiers

- **Critical** (0.8+): Immediate action required
- **High** (0.6-0.8): High priority for next phase
- **Medium** (0.4-0.6): Standard priority queue
- **Low** (0.2-0.4): Lower priority opportunities  
- **Minimal** (<0.2): Limited value or high difficulty

## Database Integration

### Cluster Model Updates

The system updates the `Cluster` table with:

- **Cluster Names**: Generated from n-gram analysis
- **Cluster Types**: Hub/spoke classification
- **Entities**: Key topics and hub keywords
- **Priority Scores**: Aggregate metrics for clusters

### Keyword Model Updates

The system updates the `Keyword` table with:

- **Value Scores**: Priority scores as `value_score`
- **Content Requirements**: Recommendations from gap analysis
- **Cluster Assignment**: Links keywords to their clusters

### Error Handling

- **Transaction Safety**: Uses database transactions with rollback
- **Partial Updates**: Handles individual keyword failures gracefully
- **Logging**: Comprehensive error logging and recovery

## Configuration Options

### Clustering Configuration

```python
KeywordClusterManager(
    min_cluster_size=3,           # Minimum keywords per cluster
    min_samples=2,                # HDBSCAN core point threshold
    cluster_selection_epsilon=0.5, # HDBSCAN cluster selection 
    max_clusters=50               # Maximum clusters to create
)
```

### Prioritization Configuration

```python
KeywordPrioritizer(
    traffic_weight=0.4,           # Traffic potential weight
    difficulty_weight=0.3,        # Keyword difficulty weight  
    gap_weight=0.2,              # Content gap weight
    business_value_weight=0.1     # Business value weight
)
```

### Content Gap Configuration

```python
ContentGapAnalyzer(
    gap_weight_multiplier=1.2     # Multiplier for gap opportunities
)
```

### Traffic Estimation Configuration

```python
TrafficEstimator(
    base_ctr=0.25,               # Base click-through rate
    position_decay=0.5,           # CTR decay for lower positions
    branded_multiplier=1.5        # Multiplier for branded keywords
)
```

## Performance Considerations

### Scalability

- **Embedding Generation**: O(n) complexity, batched processing
- **Clustering**: O(n²) for similarity calculations, optimized algorithms
- **Database Updates**: Batched operations with transaction management
- **Memory Usage**: Efficient numpy arrays, garbage collection

### Optimization Tips

1. **Batch Size**: Process keywords in batches of 100-1000
2. **Clustering Method**: Use K-means for speed, HDBSCAN for quality  
3. **Embedding Cache**: Cache embeddings for repeated analyses
4. **Database Indexing**: Ensure proper indexes on query fields

## Testing

### Test Coverage

- **Unit Tests**: Individual component testing
- **Integration Tests**: Database interaction testing  
- **End-to-End Tests**: Complete workflow testing
- **Error Handling**: Exception and edge case testing

### Running Tests

```bash
# Run all tests
pytest tests/test_clustering.py tests/test_prioritization.py tests/test_keywords_integration.py

# Run specific test categories
pytest tests/test_clustering.py -k "TestEmbeddingGenerator"
pytest tests/test_prioritization.py -k "TestTrafficEstimator"
pytest tests/test_keywords_integration.py -k "TestClusteringIntegration"

# Run with coverage
pytest --cov=seo_bot.keywords tests/
```

## Error Handling and Logging

### Exception Types

- **`ClusteringError`**: Clustering operation failures
- **`PrioritizationError`**: Prioritization operation failures  
- **Standard Exceptions**: Import errors, validation errors

### Logging Levels

- **INFO**: Successful operations, progress updates
- **WARNING**: Fallback usage, non-critical issues
- **ERROR**: Operation failures, exception details
- **DEBUG**: Detailed execution flow (when enabled)

### Common Issues and Solutions

1. **Missing Dependencies**
   - **Issue**: ImportError for ML libraries
   - **Solution**: System automatically falls back to simpler algorithms

2. **Empty Clusters**
   - **Issue**: No clusters found for keyword set
   - **Solution**: Lower `min_cluster_size` or increase keyword diversity

3. **Low Priority Scores**
   - **Issue**: All keywords get low priority scores
   - **Solution**: Check input data quality, adjust weight parameters

4. **Database Conflicts**
   - **Issue**: Cluster slug conflicts in database
   - **Solution**: System reuses existing clusters with same slug

## Examples

### Complete Workflow Example

```python
from seo_bot.keywords import KeywordClusterManager, KeywordPrioritizer
from sqlalchemy.orm import Session

def analyze_project_keywords(db: Session, project_id: str):
    """Complete keyword analysis workflow."""
    
    # 1. Get keywords from database
    keywords = db.query(Keyword).filter_by(project_id=project_id).all()
    keyword_queries = [kw.query for kw in keywords]
    
    # 2. Cluster keywords
    cluster_manager = KeywordClusterManager(min_cluster_size=3)
    clustering_results = cluster_manager.cluster_keywords(keyword_queries)
    
    # 3. Update database with clusters  
    created_clusters = cluster_manager.update_database_clusters(
        db, project_id, clustering_results
    )
    
    # 4. Prepare prioritization data
    keywords_data = []
    for kw in keywords:
        keywords_data.append({
            'query': kw.query,
            'search_volume': kw.search_volume,
            'difficulty_proxy': kw.difficulty_proxy,
            'intent': kw.intent,
            'cpc': kw.cpc,
            'competition': kw.competition,
            'serp_features': kw.serp_features or [],
            'gap_analysis': kw.gap_analysis or {},
            'content_requirements': kw.content_requirements or []
        })
    
    # 5. Prioritize keywords
    prioritizer = KeywordPrioritizer()
    prioritized_keywords = prioritizer.prioritize_keywords(keywords_data)
    
    # 6. Update database with priorities
    updated_count = prioritizer.update_database_priorities(db, prioritized_keywords)
    
    return {
        'clusters_created': len(created_clusters),
        'keywords_prioritized': updated_count,
        'top_keywords': prioritized_keywords[:10]
    }
```

## Advanced Usage

### Custom Embedding Models

```python
from seo_bot.keywords.cluster import EmbeddingGenerator

# Use custom sentence-transformer model
generator = EmbeddingGenerator("paraphrase-multilingual-MiniLM-L12-v2")
embeddings = generator.generate_embeddings(keywords)
```

### Custom Business Rules

```python
from seo_bot.keywords.prioritize import BusinessValueCalculator

# Custom intent weights for specific business model
calculator = BusinessValueCalculator(
    intent_weights={
        'transactional': 1.2,  # Higher weight for e-commerce
        'commercial': 1.0,
        'informational': 0.3,  # Lower weight for lead-gen
        'navigational': 0.1
    },
    business_multipliers={
        'buy': 1.5, 'purchase': 1.5, 'order': 1.5,
        'free': 0.8, 'cheap': 1.1, 'discount': 1.2
    }
)
```

### Iterative Refinement

```python
def refine_clusters(keywords, initial_results):
    """Refine clusters based on business rules."""
    
    # Start with initial clustering
    cluster_manager = KeywordClusterManager(min_cluster_size=5)
    
    # If too many small clusters, reduce granularity
    if initial_results['total_clusters'] > 15:
        cluster_manager = KeywordClusterManager(min_cluster_size=8)
    
    # If too few clusters, increase granularity  
    elif initial_results['total_clusters'] < 3:
        cluster_manager = KeywordClusterManager(min_cluster_size=2)
    
    return cluster_manager.cluster_keywords(keywords)
```

## Best Practices

### Keyword Selection

1. **Quality over Quantity**: Better to cluster 50 high-quality keywords than 500 poor ones
2. **Semantic Diversity**: Include varied topics for meaningful clusters
3. **Data Completeness**: Ensure search volume and difficulty data for accurate prioritization

### Clustering Optimization

1. **Parameter Tuning**: Adjust `min_cluster_size` based on dataset size
2. **Method Selection**: Use HDBSCAN for varied cluster sizes, K-means for uniformity  
3. **Embedding Quality**: Ensure good text preprocessing for better embeddings

### Prioritization Tuning

1. **Weight Adjustment**: Customize weights based on business goals
2. **Intent Classification**: Verify intent detection for accurate business value
3. **Gap Analysis**: Include comprehensive SERP and content data

### Database Management

1. **Transaction Boundaries**: Group related operations in transactions
2. **Error Recovery**: Implement retry logic for temporary failures
3. **Data Validation**: Validate input data before processing

## Monitoring and Maintenance

### Performance Metrics

- **Clustering Quality**: Silhouette score, cluster cohesion
- **Prioritization Accuracy**: Validation against known high-value keywords
- **Processing Speed**: Time per keyword for batch operations
- **Database Performance**: Query execution times, update success rates

### Regular Maintenance

1. **Model Updates**: Update sentence-transformer models periodically
2. **Parameter Tuning**: Adjust parameters based on performance metrics
3. **Data Cleanup**: Remove outdated keywords and clusters
4. **Index Optimization**: Maintain database indexes for performance

## Conclusion

The SEO-Bot clustering and prioritization system provides sophisticated keyword analysis capabilities with robust fallback options and comprehensive database integration. The modular design allows for easy customization and extension while maintaining high performance and reliability.

For questions or issues, refer to the test files for usage examples and expected behaviors.
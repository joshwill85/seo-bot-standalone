# SEO-Bot Keywords Module

The keyword discovery and SERP gap analysis modules for SEO-Bot provide comprehensive functionality for finding, scoring, and analyzing keywords for SEO optimization.

## Overview

The keywords package consists of four main modules:

1. **`score.py`** - Intent classification, value scoring, and difficulty calculation
2. **`discover.py`** - Seed keyword expansion, GSC integration, and SERP API integration
3. **`serp_gap.py`** - SERP result fetching, content gap analysis, and entity extraction
4. **`__init__.py`** - Package initialization and exports

## Features

### Keyword Scoring (`score.py`)

- **Intent Classification**: Automatically classifies search queries into informational, navigational, transactional, or commercial intent
- **Value Scoring**: Calculates keyword value based on business relevance, search volume, and commercial indicators
- **Difficulty Proxy**: Estimates keyword difficulty using multiple factors including query length, competition terms, and CPC data
- **Batch Processing**: Efficiently score multiple keywords at once

### Keyword Discovery (`discover.py`)

- **Seed Expansion**: Expands seed keywords using intent-based modifiers and variations
- **Google Search Console Integration**: Fetches existing query data from GSC API and database
- **SERP API Integration**: Optional integration with SerpAPI and DataForSEO for keyword suggestions
- **Quality Filtering**: Filters keywords based on length, character composition, and branding signals
- **Database Storage**: Saves discovered keywords to the project database with scoring
- **CSV Export**: Exports keyword lists to CSV format for analysis

### SERP Gap Analysis (`serp_gap.py`)

- **SERP Result Fetching**: Retrieves search results from SERP APIs or fallback methods
- **Content Analysis**: Analyzes competitor content including word count, headings, and structure
- **Entity Extraction**: Identifies named entities (people, organizations, locations, dates, money, percentages)
- **Topic Modeling**: Extracts common topics and themes from competitor content
- **Gap Identification**: Identifies content gaps and differentiation opportunities
- **Content Clustering**: Groups similar SERP results for competitive analysis

## Usage Examples

### Basic Intent Classification

```python
from seo_bot.keywords.score import IntentClassifier, SearchIntent

classifier = IntentClassifier()
intent, confidence = classifier.classify_intent("how to fix a leaky faucet")
print(f"Intent: {intent.value}, Confidence: {confidence:.2f}")
# Output: Intent: informational, Confidence: 0.72
```

### Keyword Scoring

```python
from seo_bot.keywords.score import KeywordScorer

scorer = KeywordScorer()
result = scorer.score_keyword(
    query="plumber near me",
    search_volume=1500,
    cpc=12.0,
    business_relevance=1.0
)

print(f"Final Score: {result.final_score:.2f}")
print(f"Intent: {result.intent.value}")
print(f"Value: {result.value_score:.2f}")
print(f"Difficulty: {result.difficulty_proxy:.2f}")
```

### Keyword Discovery

```python
from seo_bot.keywords.discover import KeywordDiscoverer, KeywordSeed

discoverer = KeywordDiscoverer()

# Define seed keywords
seeds = [
    KeywordSeed(term="local plumbing", priority=1.0),
    KeywordSeed(term="emergency plumber", priority=0.8)
]

# Discover keywords
keywords = discoverer.discover_keywords(
    project_id="your-project-id",
    seeds=seeds,
    use_gsc=True,
    max_keywords=500
)

print(f"Discovered {len(keywords)} keywords")
```

### SERP Gap Analysis

```python
from seo_bot.keywords.serp_gap import SERPGapAnalyzer

analyzer = SERPGapAnalyzer(api_key="your-serp-api-key")

analysis = analyzer.analyze_serp_gaps(
    query="best plumbing tools",
    target_domain="yoursite.com",
    num_results=10,
    analyze_content=True
)

print(f"Found {len(analysis.content_gaps)} content gaps")
print(f"Differentiation opportunities: {len(analysis.differentiation_opportunities)}")

for gap in analysis.content_gaps:
    print(f"- {gap.gap_type}: {gap.description}")
```

## Configuration

The keyword modules use the `KeywordsConfig` from the main configuration system:

```python
from seo_bot.config import KeywordsConfig

config = KeywordsConfig(
    seed_terms=["plumbing", "hvac", "electrical"],
    min_intent_score=0.6,
    difficulty_proxy_max=0.7,
    value_score_min=1.0,
    max_keywords_per_run=5000
)
```

## Dependencies

### Required
- `httpx` - HTTP client for API requests
- `sqlalchemy` - Database operations
- `dataclasses` - Data structures
- `re` - Regular expressions

### Optional (with fallbacks)
- `pandas` - CSV export (fallback to standard `csv` module)
- `scikit-learn` - Advanced topic modeling (fallback to simple frequency analysis)
- `beautifulsoup4` - HTML parsing for content analysis
- `google-api-python-client` - Google Search Console integration

### SERP API Integrations
- **SerpAPI**: Set `SERP_API_KEY` environment variable
- **DataForSEO**: Set `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD`

### Google Search Console
- Set `GOOGLE_SEARCH_CONSOLE_CREDENTIALS_FILE` to service account JSON path

## Database Integration

The modules integrate with SQLAlchemy models:

- **Project**: Links keywords to specific SEO projects
- **Keyword**: Stores discovered keywords with scoring data
- **GSCData**: Integrates with existing GSC performance data

## Error Handling

All modules include comprehensive error handling:

- Graceful degradation when optional dependencies are missing
- Fallback methods for API failures
- Detailed logging of errors and warnings
- Continuation of processing when individual items fail

## Testing

Run the validation tests:

```bash
# Basic component tests (no external dependencies)
python3 test_isolated.py

# Full validation (requires dependencies)
python3 validate_keywords.py
```

## Performance Considerations

- **Batch Processing**: Use batch methods for scoring multiple keywords
- **Rate Limiting**: SERP API calls are subject to provider rate limits
- **Caching**: GSC data and SERP results can be cached in the database
- **Memory Usage**: Large keyword sets are processed in chunks

## Integration with SEO-Bot

The keyword modules integrate with the broader SEO-Bot ecosystem:

1. **Content Planning**: Discovered keywords feed into content brief generation
2. **Clustering**: Keywords are grouped into topic clusters for content strategy
3. **Performance Tracking**: Keyword performance is monitored via GSC integration
4. **Link Building**: SERP analysis informs internal linking strategies

## Future Enhancements

Planned improvements include:

- Advanced NLP models for intent classification
- Integration with additional SERP API providers
- Real-time keyword difficulty tracking
- Automated competitor monitoring
- Machine learning for value score optimization

## Support

For issues or questions:

1. Check the error logs for specific error messages
2. Verify API credentials and rate limits
3. Ensure database connectivity
4. Review configuration settings

The modules are designed to work with minimal configuration and degrade gracefully when optional services are unavailable.
# SEO Bot - Installation Guide

## Quick Installation

### Prerequisites
- Python 3.9 or higher
- Git (optional, for development)

### Option 1: Direct Installation (Recommended)

```bash
# 1. Clone or download this directory
cd seo-bot-standalone

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install as editable package (for development)
pip install -e .

# 4. Set up environment (optional)
cp .env.example .env
# Edit .env with your API keys

# 5. Test installation
python -m seo_bot.cli --help
```

### Option 2: Using Poetry (Alternative)

```bash
# 1. Install Poetry if not already installed
pip install poetry

# 2. Install dependencies with Poetry
poetry install

# 3. Activate virtual environment
poetry shell

# 4. Test installation
seo-bot --help
```

## Verification

Test the installation with these commands:

```bash
# Score some keywords
python -m seo_bot.cli score "keyword research" "seo tools"

# Discover keyword variations
python -m seo_bot.cli discover --seeds "seo,marketing" --max-keywords 20

# Cluster keywords
python -m seo_bot.cli cluster "seo tools" "keyword research" "content optimization" --min-cluster-size 2
```

## Project Setup

### Initialize Your First Project

```bash
# Create a new SEO project
python -m seo_bot.cli init --project my-website --domain example.com

# Check project status
python -m seo_bot.cli status --project my-website
```

### Environment Configuration

1. Copy `.env.example` to `.env`
2. Add your API keys:
   - Google Search Console credentials
   - PageSpeed Insights API key
   - OpenAI API key (optional)
   - SERP API keys (optional)

## Dependencies

### Required Dependencies
- typer[all] - CLI interface
- pydantic - Configuration management
- sqlalchemy - Database ORM
- pandas - Data manipulation
- scikit-learn - Machine learning
- hdbscan - Clustering
- nltk - Natural language processing
- rich - Terminal formatting

### Optional Dependencies
- sentence-transformers - Advanced embeddings
- playwright - Web scraping
- google-api-python-client - Google APIs
- openai - AI content generation

## Architecture

The SEO Bot is organized as follows:

```
seo-bot-standalone/
├── src/seo_bot/           # Core application
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration management
│   ├── models.py          # Database models
│   ├── keywords/          # Keyword analysis modules
│   ├── content/           # Content generation (planned)
│   ├── monitor/           # Performance monitoring (planned)
│   └── adapters/          # External API integrations (planned)
├── tests/                 # Test suite
├── templates/             # Content templates
├── projects/              # Project configurations
└── requirements.txt       # Python dependencies
```

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure you've installed all dependencies and the package is properly installed
2. **Permission errors**: Ensure you have write permissions in the project directory
3. **API errors**: Check your API keys in the `.env` file
4. **Clustering errors**: If you get metric errors, the system will fall back to simpler algorithms

### Getting Help

- Check the `GETTING_STARTED.md` guide
- Run `python -m seo_bot.cli --help` for command help
- Review the test files for usage examples

## Development Setup

For development work:

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff src/

# Type checking
mypy src/
```

The SEO Bot is designed to be self-contained and work out of the box with minimal configuration. All core functionality (keyword scoring, discovery, clustering) works without any external APIs.
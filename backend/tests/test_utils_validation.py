"""Unit tests for validation utilities."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import os

from src.seo_bot.utils.validation import (
    ConfigValidator,
    URLValidator,
    DataValidator,
    ValidationError
)


class TestConfigValidator:
    """Test configuration validation functionality."""
    
    def test_validate_project_config_valid(self):
        """Test validating a valid project configuration."""
        valid_config = {
            "site": {
                "domain": "example.com",
                "base_url": "https://example.com",
                "language": "en-US",
                "cms": "markdown"
            },
            "content_quality": {
                "min_info_gain_points": 5,
                "task_completers_required": 3,
                "unique_value_threshold": 0.7,
                "similarity_threshold": 0.8,
                "min_readability_score": 60,
                "max_keyword_density": 0.03,
                "word_count_bounds": [300, 3000]
            },
            "performance_budgets": {
                "article": {
                    "lcp_ms": 2500,
                    "inp_ms": 200,
                    "cls": 0.1,
                    "js_kb": 300,
                    "css_kb": 100,
                    "image_kb": 500
                }
            }
        }
        
        errors = ConfigValidator.validate_project_config(valid_config)
        assert len(errors) == 0
    
    def test_validate_project_config_missing_sections(self):
        """Test validating config with missing required sections."""
        invalid_config = {
            "site": {
                "domain": "example.com",
                "base_url": "https://example.com"
            }
            # Missing content_quality and performance_budgets
        }
        
        errors = ConfigValidator.validate_project_config(invalid_config)
        assert len(errors) >= 2
        assert any("content_quality" in error for error in errors)
        assert any("performance_budgets" in error for error in errors)
    
    def test_validate_site_config_invalid_domain(self):
        """Test site config validation with invalid domain."""
        config = {
            "site": {
                "domain": "invalid..domain",
                "base_url": "https://example.com"
            },
            "content_quality": {},
            "performance_budgets": {}
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert any("domain" in error and "valid domain" in error for error in errors)
    
    def test_validate_site_config_invalid_url(self):
        """Test site config validation with invalid URL."""
        config = {
            "site": {
                "domain": "example.com",
                "base_url": "not-a-url"
            },
            "content_quality": {},
            "performance_budgets": {}
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert any("base_url" in error and "valid URL" in error for error in errors)
    
    def test_validate_site_config_invalid_language(self):
        """Test site config validation with invalid language code."""
        config = {
            "site": {
                "domain": "example.com", 
                "base_url": "https://example.com",
                "language": "invalid-lang"
            },
            "content_quality": {},
            "performance_budgets": {}
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert any("language" in error and "valid language code" in error for error in errors)
    
    def test_validate_content_quality_config_invalid_ranges(self):
        """Test content quality config validation with invalid ranges."""
        config = {
            "site": {
                "domain": "example.com",
                "base_url": "https://example.com"
            },
            "content_quality": {
                "min_info_gain_points": 25,  # Too high (max 20)
                "similarity_threshold": 1.5,  # Too high (max 1.0)
                "min_readability_score": -10,  # Too low (min 0)
                "word_count_bounds": [1000, 500]  # Min > Max
            },
            "performance_budgets": {}
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert len(errors) >= 4
        assert any("min_info_gain_points" in error for error in errors)
        assert any("similarity_threshold" in error for error in errors)
        assert any("min_readability_score" in error for error in errors)
        assert any("word_count_bounds" in error for error in errors)
    
    def test_validate_performance_budgets_invalid_values(self):
        """Test performance budgets validation with invalid values."""
        config = {
            "site": {
                "domain": "example.com",
                "base_url": "https://example.com"
            },
            "content_quality": {},
            "performance_budgets": {
                "article": {
                    "lcp_ms": 50000,  # Too high
                    "inp_ms": 10,     # Too low
                    "cls": 2.0,       # Too high
                    "js_kb": 10,      # Too low
                    "css_kb": 1000,   # Too high
                    "image_kb": 10000 # Too high
                }
            }
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert len(errors) >= 6
        assert any("lcp_ms" in error for error in errors)
        assert any("inp_ms" in error for error in errors)
        assert any("cls" in error for error in errors)
    
    def test_validate_ctr_testing_config(self):
        """Test CTR testing config validation."""
        config = {
            "site": {"domain": "example.com", "base_url": "https://example.com"},
            "content_quality": {},
            "performance_budgets": {},
            "ctr_testing": {
                "statistical_significance": 0.5,  # Too low
                "min_sample_size": 100000,         # Too high
                "test_duration_days": 200          # Too high
            }
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert any("statistical_significance" in error for error in errors)
        assert any("min_sample_size" in error for error in errors)
        assert any("test_duration_days" in error for error in errors)
    
    def test_validate_governance_config(self):
        """Test governance config validation."""
        config = {
            "site": {"domain": "example.com", "base_url": "https://example.com"},
            "content_quality": {},
            "performance_budgets": {},
            "governance": {
                "similarity_threshold": 0.3,  # Too low
                "quality_score_minimum": 15.0,  # Too high
                "human_review_required": ["invalid_category"]  # Invalid category
            }
        }
        
        errors = ConfigValidator.validate_project_config(config)
        assert any("similarity_threshold" in error for error in errors)
        assert any("quality_score_minimum" in error for error in errors)
        assert any("invalid_category" in error for error in errors)
    
    def test_validate_environment_settings_valid(self):
        """Test validating valid environment settings."""
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            settings = {
                "google_search_console_credentials_file": tmp_path,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "slack_webhook_url": "https://hooks.slack.com/test",
                "log_level": "INFO"
            }
            
            errors = ConfigValidator.validate_environment_settings(settings)
            assert len(errors) == 0
        finally:
            os.unlink(tmp_path)
    
    def test_validate_environment_settings_missing_files(self):
        """Test environment settings validation with missing files."""
        settings = {
            "google_search_console_credentials_file": "/nonexistent/file.json"
        }
        
        errors = ConfigValidator.validate_environment_settings(settings)
        assert any("File not found" in error for error in errors)
    
    def test_validate_environment_settings_invalid_urls(self):
        """Test environment settings validation with invalid URLs."""
        settings = {
            "slack_webhook_url": "not-a-url",
            "redis_url": "invalid://url"
        }
        
        errors = ConfigValidator.validate_environment_settings(settings)
        assert any("slack_webhook_url" in error for error in errors)
    
    def test_validate_environment_settings_invalid_port(self):
        """Test environment settings validation with invalid port."""
        settings = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 99999  # Invalid port
        }
        
        errors = ConfigValidator.validate_environment_settings(settings)
        assert any("smtp_port" in error for error in errors)


class TestURLValidator:
    """Test URL validation functionality."""
    
    def test_is_valid_url_valid_urls(self):
        """Test valid URL detection."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://sub.example.com/path",
            "https://example.com/path?query=value",
            "https://example.com:8080/path"
        ]
        
        for url in valid_urls:
            assert URLValidator.is_valid_url(url), f"Should be valid: {url}"
    
    def test_is_valid_url_invalid_urls(self):
        """Test invalid URL detection."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Invalid scheme
            "https://",           # Missing netloc
            "example.com",        # Missing scheme
            ""                    # Empty string
        ]
        
        for url in invalid_urls:
            assert not URLValidator.is_valid_url(url), f"Should be invalid: {url}"
    
    def test_is_valid_domain_valid_domains(self):
        """Test valid domain detection."""
        valid_domains = [
            "example.com",
            "sub.example.com",
            "my-site.com",
            "test123.org",
            "a.b.c.d.example.com"
        ]
        
        for domain in valid_domains:
            assert URLValidator.is_valid_domain(domain), f"Should be valid: {domain}"
    
    def test_is_valid_domain_invalid_domains(self):
        """Test invalid domain detection."""
        invalid_domains = [
            "invalid..domain",
            "-example.com",
            "example-.com",
            "example.com-",
            "",
            "space in domain.com"
        ]
        
        for domain in invalid_domains:
            assert not URLValidator.is_valid_domain(domain), f"Should be invalid: {domain}"
    
    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        test_cases = [
            ("https://example.com/path", "example.com"),
            ("http://sub.example.com:8080", "sub.example.com:8080"),
            ("https://Example.COM/Path", "example.com:8080"),  # Case normalization
            ("invalid-url", None)
        ]
        
        for url, expected in test_cases[:-1]:  # Skip the invalid case
            result = URLValidator.extract_domain(url)
            if expected:
                assert result == expected.lower()
        
        # Test invalid URL
        assert URLValidator.extract_domain("invalid-url") is None
    
    def test_normalize_url(self):
        """Test URL normalization."""
        test_cases = [
            ("https://Example.com/Path/", "https://example.com/path"),
            ("https://example.com/path?query=value", "https://example.com/path?query=value"),
            ("https://example.com/", "https://example.com/"),
            ("https://example.com", "https://example.com")
        ]
        
        for input_url, expected in test_cases:
            result = URLValidator.normalize_url(input_url)
            assert result == expected
    
    def test_is_internal_link(self):
        """Test internal link detection."""
        domain = "example.com"
        
        internal_urls = [
            "https://example.com/page",
            "http://example.com/other"
        ]
        
        external_urls = [
            "https://other.com/page",
            "https://sub.example.com/page"  # Subdomain counts as external
        ]
        
        for url in internal_urls:
            assert URLValidator.is_internal_link(url, domain)
        
        for url in external_urls:
            assert not URLValidator.is_internal_link(url, domain)
    
    def test_validate_sitemap_urls(self):
        """Test sitemap URL validation."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "invalid-url",
            "https://example.com/page3",
            "not-a-url"
        ]
        
        result = URLValidator.validate_sitemap_urls(urls)
        
        assert len(result["valid"]) == 3
        assert len(result["invalid"]) == 2
        assert "invalid-url" in result["invalid"]
        assert "not-a-url" in result["invalid"]
    
    def test_check_url_patterns(self):
        """Test URL pattern analysis."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page1",  # Duplicate
            "http://example.com/insecure",  # HTTP
            "https://example.com/very-long-url-that-exceeds-normal-length" + "x" * 2000,  # Long URL
            "https://example.com/page?" + "&".join([f"param{i}=value{i}" for i in range(15)])  # Many params
        ]
        
        result = URLValidator.check_url_patterns(urls)
        
        assert result["total"] == 5
        assert result["duplicates"] > 0
        assert "duplicate URLs" in " ".join(result["issues"])
        assert "non-HTTPS URLs" in " ".join(result["issues"])
        assert "longer than 2000 characters" in " ".join(result["issues"])
        assert "more than 10 parameters" in " ".join(result["issues"])


class TestDataValidator:
    """Test data validation functionality."""
    
    def test_validate_gsc_data_valid(self):
        """Test validating valid GSC data."""
        valid_gsc_data = {
            "rows": [
                {
                    "keys": ["https://example.com/page1"],
                    "clicks": 100,
                    "impressions": 1000,
                    "ctr": 0.1,
                    "position": 5.5
                },
                {
                    "keys": ["https://example.com/page2"],
                    "clicks": 50,
                    "impressions": 800,
                    "ctr": 0.0625,
                    "position": 8.2
                }
            ]
        }
        
        errors = DataValidator.validate_gsc_data(valid_gsc_data)
        assert len(errors) == 0
    
    def test_validate_gsc_data_missing_fields(self):
        """Test GSC data validation with missing fields."""
        invalid_gsc_data = {
            "rows": [
                {
                    "keys": ["https://example.com/page1"],
                    "clicks": 100,
                    # Missing impressions, ctr, position
                }
            ]
        }
        
        errors = DataValidator.validate_gsc_data(invalid_gsc_data)
        assert len(errors) >= 3  # Missing impressions, ctr, position
        assert any("impressions" in error for error in errors)
        assert any("ctr" in error for error in errors)
        assert any("position" in error for error in errors)
    
    def test_validate_gsc_data_invalid_values(self):
        """Test GSC data validation with invalid values."""
        invalid_gsc_data = {
            "rows": [
                {
                    "keys": ["https://example.com/page1"],
                    "clicks": -10,      # Negative clicks
                    "impressions": -5,  # Negative impressions
                    "ctr": 1.5,        # CTR > 1
                    "position": 0      # Position < 1
                }
            ]
        }
        
        errors = DataValidator.validate_gsc_data(invalid_gsc_data)
        assert len(errors) >= 4
        assert any("clicks" in error and "non-negative" in error for error in errors)
        assert any("impressions" in error and "non-negative" in error for error in errors)
        assert any("ctr" in error and "between 0 and 1" in error for error in errors)
        assert any("position" in error and ">= 1" in error for error in errors)
    
    def test_validate_content_data_valid(self):
        """Test validating valid content data."""
        content = "This is a good piece of content with sufficient length and quality information."
        metadata = {
            "title": "A Good SEO Title",
            "meta_description": "This is a well-crafted meta description that provides good information about the content and is within the recommended length."
        }
        
        errors = DataValidator.validate_content_data(content, metadata)
        assert len(errors) == 0
    
    def test_validate_content_data_short_content(self):
        """Test content validation with short content."""
        short_content = "Too short content"
        
        errors = DataValidator.validate_content_data(short_content)
        assert any("too short" in error.lower() for error in errors)
    
    def test_validate_content_data_bad_metadata(self):
        """Test content validation with bad metadata."""
        content = "This is good content with sufficient length to pass the word count test."
        bad_metadata = {
            "title": "Bad",  # Too short
            "meta_description": "Short desc"  # Too short
        }
        
        errors = DataValidator.validate_content_data(content, bad_metadata)
        assert any("title" in error and "10 characters" in error for error in errors)
        assert any("meta description" in error.lower() and "120 characters" in error for error in errors)
    
    def test_validate_metric_data_valid(self):
        """Test validating valid metric data."""
        valid_metrics = [
            {
                "timestamp": datetime.now(timezone.utc),
                "value": 0.05,
                "metric_name": "error_rate"
            },
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "value": 100,
                "metric_name": "total_clicks"
            }
        ]
        
        errors = DataValidator.validate_metric_data(valid_metrics)
        assert len(errors) == 0
    
    def test_validate_metric_data_invalid_timestamp(self):
        """Test metric validation with invalid timestamp."""
        invalid_metrics = [
            {
                "timestamp": "invalid-timestamp",
                "value": 0.05,
                "metric_name": "error_rate"
            }
        ]
        
        errors = DataValidator.validate_metric_data(invalid_metrics)
        assert any("timestamp" in error.lower() for error in errors)
    
    def test_validate_metric_data_missing_fields(self):
        """Test metric validation with missing fields."""
        invalid_metrics = [
            {
                "timestamp": datetime.now(timezone.utc),
                # Missing value and metric_name
            }
        ]
        
        errors = DataValidator.validate_metric_data(invalid_metrics)
        assert any("value" in error for error in errors)
        assert any("metric_name" in error for error in errors)
    
    def test_validate_metric_data_invalid_value(self):
        """Test metric validation with invalid value."""
        invalid_metrics = [
            {
                "timestamp": datetime.now(timezone.utc),
                "value": "not-a-number",
                "metric_name": "error_rate"
            }
        ]
        
        errors = DataValidator.validate_metric_data(invalid_metrics)
        assert any("value" in error and "number" in error for error in errors)


class TestValidationError:
    """Test validation error functionality."""
    
    def test_validation_error_creation(self):
        """Test creating a validation error."""
        error = ValidationError("Test validation error")
        
        assert str(error) == "Test validation error"
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__])
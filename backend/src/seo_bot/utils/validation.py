"""Validation utilities for configuration and data."""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class ConfigValidator:
    """Validates configuration files and settings."""
    
    @staticmethod
    def validate_project_config(config_data: Dict[str, Any]) -> List[str]:
        """Validate project configuration structure and values."""
        errors = []
        
        # Required top-level sections
        required_sections = ['site', 'content_quality', 'performance_budgets']
        for section in required_sections:
            if section not in config_data:
                errors.append(f"Missing required section: {section}")
        
        # Validate site section
        if 'site' in config_data:
            site_errors = ConfigValidator._validate_site_config(config_data['site'])
            errors.extend(site_errors)
        
        # Validate content quality section
        if 'content_quality' in config_data:
            quality_errors = ConfigValidator._validate_content_quality_config(config_data['content_quality'])
            errors.extend(quality_errors)
        
        # Validate performance budgets
        if 'performance_budgets' in config_data:
            budget_errors = ConfigValidator._validate_performance_budgets_config(config_data['performance_budgets'])
            errors.extend(budget_errors)
        
        # Validate CTR testing config if present
        if 'ctr_testing' in config_data:
            ctr_errors = ConfigValidator._validate_ctr_testing_config(config_data['ctr_testing'])
            errors.extend(ctr_errors)
        
        # Validate governance config if present
        if 'governance' in config_data:
            gov_errors = ConfigValidator._validate_governance_config(config_data['governance'])
            errors.extend(gov_errors)
        
        return errors
    
    @staticmethod
    def _validate_site_config(site_config: Dict[str, Any]) -> List[str]:
        """Validate site configuration."""
        errors = []
        
        # Required fields
        required_fields = ['domain', 'base_url']
        for field in required_fields:
            if field not in site_config:
                errors.append(f"site.{field} is required")
            elif not site_config[field]:
                errors.append(f"site.{field} cannot be empty")
        
        # Validate domain format
        if 'domain' in site_config:
            domain = site_config['domain']
            if not URLValidator.is_valid_domain(domain):
                errors.append(f"site.domain '{domain}' is not a valid domain")
        
        # Validate base_url format
        if 'base_url' in site_config:
            base_url = site_config['base_url']
            if not URLValidator.is_valid_url(base_url):
                errors.append(f"site.base_url '{base_url}' is not a valid URL")
        
        # Validate language code
        if 'language' in site_config:
            language = site_config['language']
            if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', language):
                errors.append(f"site.language '{language}' is not a valid language code (use ISO 639-1)")
        
        # Validate CMS type
        if 'cms' in site_config:
            cms = site_config['cms']
            valid_cms = ['markdown', 'wordpress', 'contentful']
            if cms not in valid_cms:
                errors.append(f"site.cms '{cms}' is not valid. Must be one of: {valid_cms}")
        
        return errors
    
    @staticmethod
    def _validate_content_quality_config(quality_config: Dict[str, Any]) -> List[str]:
        """Validate content quality configuration."""
        errors = []
        
        # Validate numeric ranges
        numeric_validations = [
            ('min_info_gain_points', 1, 20),
            ('task_completers_required', 1, 10),
            ('unique_value_threshold', 0.0, 1.0),
            ('similarity_threshold', 0.0, 1.0),
            ('min_readability_score', 0, 100),
            ('max_keyword_density', 0.0, 0.1)
        ]
        
        for field, min_val, max_val in numeric_validations:
            if field in quality_config:
                value = quality_config[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"content_quality.{field} must be a number")
                elif not (min_val <= value <= max_val):
                    errors.append(f"content_quality.{field} must be between {min_val} and {max_val}")
        
        # Validate word count bounds
        if 'word_count_bounds' in quality_config:
            bounds = quality_config['word_count_bounds']
            if not isinstance(bounds, list) or len(bounds) != 2:
                errors.append("content_quality.word_count_bounds must be a list of two numbers [min, max]")
            elif not all(isinstance(x, int) and x > 0 for x in bounds):
                errors.append("content_quality.word_count_bounds must contain positive integers")
            elif bounds[0] >= bounds[1]:
                errors.append("content_quality.word_count_bounds min must be less than max")
        
        return errors
    
    @staticmethod
    def _validate_performance_budgets_config(budgets_config: Dict[str, Any]) -> List[str]:
        """Validate performance budgets configuration."""
        errors = []
        
        # Expected budget types
        budget_types = ['article', 'product', 'comparison', 'calculator']
        
        for budget_type in budget_types:
            if budget_type in budgets_config:
                budget_errors = ConfigValidator._validate_single_budget(
                    budgets_config[budget_type], f"performance_budgets.{budget_type}"
                )
                errors.extend(budget_errors)
        
        return errors
    
    @staticmethod
    def _validate_single_budget(budget_config: Dict[str, Any], prefix: str) -> List[str]:
        """Validate a single performance budget."""
        errors = []
        
        # Validate numeric fields with reasonable ranges
        budget_validations = [
            ('lcp_ms', 500, 10000),      # 0.5s to 10s
            ('inp_ms', 50, 2000),        # 50ms to 2s
            ('cls', 0.0, 1.0),           # 0 to 1
            ('js_kb', 50, 2000),         # 50KB to 2MB
            ('css_kb', 10, 500),         # 10KB to 500KB
            ('image_kb', 100, 5000)      # 100KB to 5MB
        ]
        
        for field, min_val, max_val in budget_validations:
            if field in budget_config:
                value = budget_config[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"{prefix}.{field} must be a number")
                elif not (min_val <= value <= max_val):
                    errors.append(f"{prefix}.{field} must be between {min_val} and {max_val}")
        
        return errors
    
    @staticmethod
    def _validate_ctr_testing_config(ctr_config: Dict[str, Any]) -> List[str]:
        """Validate CTR testing configuration."""
        errors = []
        
        # Validate numeric fields
        ctr_validations = [
            ('statistical_significance', 0.8, 0.99),
            ('min_sample_size', 50, 10000),
            ('max_tests_per_week', 1, 50),
            ('min_improvement_threshold', 0.01, 1.0),
            ('test_duration_days', 3, 90),
            ('position_stability_threshold', 0.5, 10.0)
        ]
        
        for field, min_val, max_val in ctr_validations:
            if field in ctr_config:
                value = ctr_config[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"ctr_testing.{field} must be a number")
                elif not (min_val <= value <= max_val):
                    errors.append(f"ctr_testing.{field} must be between {min_val} and {max_val}")
        
        return errors
    
    @staticmethod
    def _validate_governance_config(gov_config: Dict[str, Any]) -> List[str]:
        """Validate governance configuration."""
        errors = []
        
        # Validate numeric fields
        gov_validations = [
            ('max_programmatic_per_week', 1, 10000),
            ('similarity_threshold', 0.5, 1.0),
            ('quality_score_minimum', 1.0, 10.0),
            ('content_velocity_limit', 1, 1000)
        ]
        
        for field, min_val, max_val in gov_validations:
            if field in gov_config:
                value = gov_config[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"governance.{field} must be a number")
                elif not (min_val <= value <= max_val):
                    errors.append(f"governance.{field} must be between {min_val} and {max_val}")
        
        # Validate human review required list
        if 'human_review_required' in gov_config:
            review_list = gov_config['human_review_required']
            if not isinstance(review_list, list):
                errors.append("governance.human_review_required must be a list")
            else:
                valid_categories = ['ymyl', 'legal', 'medical', 'financial']
                for category in review_list:
                    if category not in valid_categories:
                        errors.append(f"governance.human_review_required contains invalid category '{category}'")
        
        return errors
    
    @staticmethod
    def validate_environment_settings(settings_dict: Dict[str, Any]) -> List[str]:
        """Validate environment settings."""
        errors = []
        
        # Check file paths exist
        file_path_fields = [
            'google_search_console_credentials_file'
        ]
        
        for field in file_path_fields:
            if field in settings_dict and settings_dict[field]:
                file_path = Path(settings_dict[field])
                if not file_path.exists():
                    errors.append(f"{field}: File not found at {file_path}")
                elif not file_path.is_file():
                    errors.append(f"{field}: Path is not a file: {file_path}")
        
        # Validate URL fields
        url_fields = [
            'wordpress_url',
            'slack_webhook_url',
            'redis_url',
            'celery_broker_url'
        ]
        
        for field in url_fields:
            if field in settings_dict and settings_dict[field]:
                url = settings_dict[field]
                if not URLValidator.is_valid_url(url):
                    errors.append(f"{field}: Invalid URL format: {url}")
        
        # Validate email settings
        if 'smtp_host' in settings_dict and settings_dict['smtp_host']:
            smtp_port = settings_dict.get('smtp_port', 587)
            if not isinstance(smtp_port, int) or not (1 <= smtp_port <= 65535):
                errors.append("smtp_port must be a valid port number (1-65535)")
        
        # Validate log level
        if 'log_level' in settings_dict:
            log_level = settings_dict['log_level']
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                errors.append(f"log_level must be one of: {valid_levels}")
        
        return errors


class URLValidator:
    """Validates URLs and domains."""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL is valid."""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except Exception:
            return False
    
    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """Check if domain is valid."""
        # Basic domain validation
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        return bool(domain_pattern.match(domain))
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for consistent comparison."""
        try:
            parsed = urlparse(url.lower())
            
            # Remove trailing slash from path
            path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
            
            # Reconstruct URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
            
            if parsed.query:
                normalized += f"?{parsed.query}"
                
            return normalized
            
        except Exception:
            return url
    
    @staticmethod
    def is_internal_link(url: str, domain: str) -> bool:
        """Check if URL is an internal link for the given domain."""
        try:
            url_domain = URLValidator.extract_domain(url)
            return url_domain == domain.lower() if url_domain else False
        except Exception:
            return False
    
    @staticmethod
    def validate_sitemap_urls(urls: List[str]) -> Dict[str, List[str]]:
        """Validate a list of sitemap URLs."""
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            if URLValidator.is_valid_url(url):
                valid_urls.append(URLValidator.normalize_url(url))
            else:
                invalid_urls.append(url)
        
        return {
            "valid": valid_urls,
            "invalid": invalid_urls
        }
    
    @staticmethod
    def check_url_patterns(urls: List[str]) -> Dict[str, Any]:
        """Analyze URL patterns for potential issues."""
        
        if not urls:
            return {"total": 0, "issues": []}
        
        issues = []
        
        # Check for duplicate URLs
        url_counts = {}
        for url in urls:
            normalized = URLValidator.normalize_url(url)
            url_counts[normalized] = url_counts.get(normalized, 0) + 1
        
        duplicates = [url for url, count in url_counts.items() if count > 1]
        if duplicates:
            issues.append(f"Found {len(duplicates)} duplicate URLs")
        
        # Check for very long URLs
        long_urls = [url for url in urls if len(url) > 2000]
        if long_urls:
            issues.append(f"Found {len(long_urls)} URLs longer than 2000 characters")
        
        # Check for URLs with many parameters
        high_param_urls = []
        for url in urls:
            parsed = urlparse(url)
            if parsed.query and len(parsed.query.split('&')) > 10:
                high_param_urls.append(url)
        
        if high_param_urls:
            issues.append(f"Found {len(high_param_urls)} URLs with more than 10 parameters")
        
        # Check for non-HTTPS URLs
        http_urls = [url for url in urls if url.startswith('http://')]
        if http_urls:
            issues.append(f"Found {len(http_urls)} non-HTTPS URLs")
        
        return {
            "total": len(urls),
            "unique": len(url_counts),
            "duplicates": len(duplicates),
            "issues": issues,
            "patterns": {
                "long_urls": len(long_urls),
                "high_param_urls": len(high_param_urls),
                "http_urls": len(http_urls)
            }
        }


class DataValidator:
    """Validates data structures and content."""
    
    @staticmethod
    def validate_gsc_data(gsc_data: Dict[str, Any]) -> List[str]:
        """Validate Google Search Console data structure."""
        errors = []
        
        # Check required fields
        required_fields = ['rows']
        for field in required_fields:
            if field not in gsc_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate rows structure
        if 'rows' in gsc_data:
            rows = gsc_data['rows']
            if not isinstance(rows, list):
                errors.append("'rows' must be a list")
            else:
                for i, row in enumerate(rows[:10]):  # Check first 10 rows
                    row_errors = DataValidator._validate_gsc_row(row, i)
                    errors.extend(row_errors)
        
        return errors
    
    @staticmethod
    def _validate_gsc_row(row: Dict[str, Any], row_index: int) -> List[str]:
        """Validate a single GSC data row."""
        errors = []
        
        # Check required fields
        required_fields = ['keys', 'clicks', 'impressions', 'ctr', 'position']
        for field in required_fields:
            if field not in row:
                errors.append(f"Row {row_index}: Missing field '{field}'")
        
        # Validate data types and ranges
        if 'clicks' in row:
            clicks = row['clicks']
            if not isinstance(clicks, (int, float)) or clicks < 0:
                errors.append(f"Row {row_index}: 'clicks' must be a non-negative number")
        
        if 'impressions' in row:
            impressions = row['impressions']
            if not isinstance(impressions, (int, float)) or impressions < 0:
                errors.append(f"Row {row_index}: 'impressions' must be a non-negative number")
        
        if 'ctr' in row:
            ctr = row['ctr']
            if not isinstance(ctr, (int, float)) or not (0 <= ctr <= 1):
                errors.append(f"Row {row_index}: 'ctr' must be between 0 and 1")
        
        if 'position' in row:
            position = row['position']
            if not isinstance(position, (int, float)) or position < 1:
                errors.append(f"Row {row_index}: 'position' must be >= 1")
        
        return errors
    
    @staticmethod
    def validate_content_data(content: str, metadata: Dict[str, Any] = None) -> List[str]:
        """Validate content data."""
        errors = []
        
        if not content or not isinstance(content, str):
            errors.append("Content must be a non-empty string")
            return errors
        
        # Basic content checks
        word_count = len(content.split())
        if word_count < 50:
            errors.append(f"Content is too short ({word_count} words)")
        
        # Check for metadata if provided
        if metadata:
            if 'title' in metadata:
                title = metadata['title']
                if not title or len(title) < 10:
                    errors.append("Title must be at least 10 characters")
                elif len(title) > 60:
                    errors.append("Title should be under 60 characters for SEO")
            
            if 'meta_description' in metadata:
                meta_desc = metadata['meta_description']
                if meta_desc:
                    if len(meta_desc) < 120:
                        errors.append("Meta description should be at least 120 characters")
                    elif len(meta_desc) > 160:
                        errors.append("Meta description should be under 160 characters")
        
        return errors
    
    @staticmethod
    def validate_metric_data(metrics: List[Dict[str, Any]]) -> List[str]:
        """Validate metric data structure."""
        errors = []
        
        if not isinstance(metrics, list):
            errors.append("Metrics must be a list")
            return errors
        
        for i, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                errors.append(f"Metric {i}: Must be a dictionary")
                continue
            
            # Check required fields
            required_fields = ['timestamp', 'value', 'metric_name']
            for field in required_fields:
                if field not in metric:
                    errors.append(f"Metric {i}: Missing field '{field}'")
            
            # Validate timestamp
            if 'timestamp' in metric:
                timestamp = metric['timestamp']
                if isinstance(timestamp, str):
                    try:
                        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(f"Metric {i}: Invalid timestamp format")
                elif not isinstance(timestamp, datetime):
                    errors.append(f"Metric {i}: Timestamp must be datetime or ISO string")
            
            # Validate value
            if 'value' in metric:
                value = metric['value']
                if not isinstance(value, (int, float)):
                    errors.append(f"Metric {i}: Value must be a number")
        
        return errors
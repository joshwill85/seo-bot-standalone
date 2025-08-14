"""Technical SEO audit system with HTML validation, schema markup, and resource optimization."""

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup, Comment

from ..config import Settings
from ..models import Project


logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    """Severity levels for technical SEO issues."""
    CRITICAL = "critical"  # Blocks indexing or severely impacts SEO
    HIGH = "high"         # Significantly impacts SEO performance
    MEDIUM = "medium"     # Moderate impact on SEO
    LOW = "low"          # Minor optimization opportunity
    INFO = "info"        # Best practice recommendation


class AuditCategory(Enum):
    """Categories of technical SEO issues."""
    HTML_VALIDATION = "html_validation"
    META_TAGS = "meta_tags"
    SCHEMA_MARKUP = "schema_markup"
    INTERNAL_LINKS = "internal_links"
    IMAGES = "images"
    MOBILE_USABILITY = "mobile_usability"
    PAGE_SPEED = "page_speed"
    CRAWLABILITY = "crawlability"
    INDEXABILITY = "indexability"
    SECURITY = "security"
    INTERNATIONALIZATION = "internationalization"


@dataclass
class AuditResult:
    """Represents a technical SEO audit finding."""
    
    result_id: str
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    
    # Element/location information
    element_selector: str
    element_html: str
    xpath: str
    page_location: str
    
    # SEO impact
    seo_impact: str
    fix_suggestion: str
    fix_priority: int  # 1-10, higher is more important
    estimated_fix_time: int  # minutes
    
    # Technical details
    current_value: str
    recommended_value: str
    test_method: str
    
    # Context
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_blocking(self) -> bool:
        """Check if issue blocks SEO performance."""
        return self.severity in [AuditSeverity.CRITICAL, AuditSeverity.HIGH]


@dataclass
class SchemaValidationResult:
    """Results from schema markup validation."""
    
    schema_types: List[str]
    valid_schemas: int
    invalid_schemas: int
    missing_required_properties: List[str]
    validation_errors: List[str]
    structured_data_count: int
    schema_completeness_score: float  # 0-1


@dataclass
class TechnicalSEOAuditResult:
    """Comprehensive technical SEO audit results."""
    
    page_url: str
    audit_timestamp: datetime
    
    # Overall metrics
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    
    # Category breakdown
    issues_by_category: Dict[AuditCategory, int]
    
    # Specific validations
    html_validation_errors: int
    meta_tags_score: float  # 0-100
    schema_validation: SchemaValidationResult
    internal_links_count: int
    orphaned_pages_detected: bool
    
    # Technical metrics
    page_size_kb: Optional[float]
    load_time_ms: Optional[int]
    mobile_friendly: bool
    https_enabled: bool
    
    # SEO fundamentals
    title_tag_present: bool
    meta_description_present: bool
    canonical_tag_present: bool
    robots_meta_present: bool
    
    # All issues found
    issues: List[AuditResult]
    
    # Recommendations
    priority_fixes: List[str]
    quick_wins: List[str]
    optimization_suggestions: List[str]
    
    @property
    def seo_health_score(self) -> float:
        """Calculate overall SEO health score (0-100)."""
        if self.total_issues == 0:
            return 100.0
        
        # Weight issues by severity
        weighted_score = (
            self.critical_issues * 25 +
            self.high_issues * 15 +
            self.medium_issues * 5 +
            self.low_issues * 1
        )
        
        # Base score starts at 100, deduct points for issues
        score = max(0, 100 - weighted_score)
        
        # Apply bonuses for good practices
        if self.title_tag_present:
            score += 2
        if self.meta_description_present:
            score += 2
        if self.canonical_tag_present:
            score += 1
        if self.https_enabled:
            score += 3
        if self.mobile_friendly:
            score += 2
        
        return min(100.0, round(score, 1))


class TechnicalSEOAuditor:
    """Comprehensive technical SEO auditor with validation and optimization recommendations."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the technical SEO auditor."""
        self.settings = settings or Settings()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # SEO validation rules
        self.meta_tag_rules = self._initialize_meta_tag_rules()
        self.schema_validation_rules = self._initialize_schema_rules()
        self.html_validation_rules = self._initialize_html_rules()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _initialize_meta_tag_rules(self) -> Dict[str, Any]:
        """Initialize meta tag validation rules."""
        return {
            "title": {
                "required": True,
                "min_length": 30,
                "max_length": 60,
                "unique_per_page": True
            },
            "description": {
                "required": True,
                "min_length": 120,
                "max_length": 160,
                "unique_per_page": True
            },
            "canonical": {
                "required": True,
                "must_be_absolute": True,
                "no_parameters_preferred": True
            },
            "robots": {
                "recommended": True,
                "valid_values": ["index", "noindex", "follow", "nofollow", "noarchive", "nosnippet"]
            },
            "viewport": {
                "required_for_mobile": True,
                "recommended_value": "width=device-width, initial-scale=1"
            },
            "charset": {
                "required": True,
                "recommended_value": "UTF-8"
            }
        }
    
    def _initialize_schema_rules(self) -> Dict[str, Any]:
        """Initialize schema markup validation rules."""
        return {
            "article": {
                "required_properties": ["headline", "author", "datePublished", "image"],
                "recommended_properties": ["dateModified", "publisher", "description"]
            },
            "product": {
                "required_properties": ["name", "image", "description"],
                "recommended_properties": ["offers", "aggregateRating", "brand"]
            },
            "organization": {
                "required_properties": ["name", "url"],
                "recommended_properties": ["logo", "contactPoint", "sameAs"]
            },
            "webpage": {
                "required_properties": ["name", "url"],
                "recommended_properties": ["description", "author", "datePublished"]
            },
            "breadcrumblist": {
                "required_properties": ["itemListElement"],
                "recommended_properties": ["numberOfItems"]
            }
        }
    
    def _initialize_html_rules(self) -> Dict[str, Any]:
        """Initialize HTML validation rules."""
        return {
            "doctype": {
                "required": True,
                "recommended": "<!DOCTYPE html>"
            },
            "lang_attribute": {
                "required": True,
                "element": "html"
            },
            "meta_charset": {
                "required": True,
                "position": "head_start"
            },
            "duplicate_ids": {
                "allowed": False
            },
            "nested_headings": {
                "proper_hierarchy": True
            }
        }
    
    async def audit_page_technical_seo(
        self,
        page_url: str,
        check_internal_links: bool = True,
        validate_schema: bool = True,
        user_agent: str = None
    ) -> TechnicalSEOAuditResult:
        """Perform comprehensive technical SEO audit on a page."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        logger.info(f"Starting technical SEO audit for: {page_url}")
        
        # Fetch page content and response headers
        html_content, response_headers = await self._fetch_page_with_headers(page_url, user_agent)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Run all technical SEO checks
        issues = []
        
        # HTML validation
        issues.extend(await self._validate_html_structure(soup, page_url))
        
        # Meta tags validation
        issues.extend(await self._validate_meta_tags(soup, page_url))
        
        # Schema markup validation
        schema_result = None
        if validate_schema:
            schema_result, schema_issues = await self._validate_schema_markup(soup, page_url)
            issues.extend(schema_issues)
        
        # Image optimization
        issues.extend(await self._validate_images(soup, page_url))
        
        # Internal linking
        internal_links_count = 0
        if check_internal_links:
            internal_link_issues, internal_links_count = await self._validate_internal_links(soup, page_url)
            issues.extend(internal_link_issues)
        
        # Mobile usability
        issues.extend(await self._validate_mobile_usability(soup, page_url))
        
        # Security and technical factors
        issues.extend(await self._validate_security_factors(response_headers, page_url))
        
        # Crawlability and indexability
        issues.extend(await self._validate_crawlability(soup, page_url))
        
        # Generate comprehensive audit result
        return self._generate_audit_result(
            page_url=page_url,
            issues=issues,
            soup=soup,
            response_headers=response_headers,
            schema_result=schema_result,
            internal_links_count=internal_links_count
        )
    
    async def _fetch_page_with_headers(self, url: str, user_agent: str = None) -> Tuple[str, Dict[str, str]]:
        """Fetch page content and response headers."""
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (compatible; SEO-Bot/1.0; +https://example.com/bot)'
        }
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Non-200 status code {response.status} for {url}")
                
                content = await response.text()
                response_headers = dict(response.headers)
                
                return content, response_headers
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {url}: {e}")
            raise RuntimeError(f"Network error: {e}")
    
    async def _validate_html_structure(self, soup: BeautifulSoup, page_url: str) -> List[AuditResult]:
        """Validate HTML structure and markup."""
        issues = []
        
        # Check DOCTYPE
        if not soup.find(string=re.compile(r'<!DOCTYPE html>', re.IGNORECASE)):
            issues.append(AuditResult(
                result_id="missing_doctype",
                category=AuditCategory.HTML_VALIDATION,
                severity=AuditSeverity.MEDIUM,
                title="Missing or incorrect DOCTYPE",
                description="Page lacks proper HTML5 DOCTYPE declaration.",
                element_selector="html",
                element_html="",
                xpath="//html",
                page_location="document",
                seo_impact="May affect rendering consistency across browsers",
                fix_suggestion="Add '<!DOCTYPE html>' at the beginning of the document",
                fix_priority=5,
                estimated_fix_time=1,
                current_value="Missing",
                recommended_value="<!DOCTYPE html>",
                test_method="automated"
            ))
        
        # Check lang attribute
        html_element = soup.find('html')
        if not html_element or not html_element.get('lang'):
            issues.append(AuditResult(
                result_id="missing_lang_attribute",
                category=AuditCategory.HTML_VALIDATION,
                severity=AuditSeverity.MEDIUM,
                title="Missing lang attribute on html element",
                description="HTML element lacks lang attribute for language declaration.",
                element_selector="html",
                element_html=str(html_element)[:100] if html_element else "",
                xpath="//html",
                page_location="document",
                seo_impact="Search engines may not understand page language",
                fix_suggestion="Add lang='en' (or appropriate language code) to html element",
                fix_priority=6,
                estimated_fix_time=1,
                current_value="Missing",
                recommended_value="en",
                test_method="automated"
            ))
        
        # Check for duplicate IDs
        ids_found = []
        elements_with_ids = soup.find_all(attrs={'id': True})
        for element in elements_with_ids:
            element_id = element.get('id')
            if element_id in ids_found:
                issues.append(AuditResult(
                    result_id=f"duplicate_id_{element_id}",
                    category=AuditCategory.HTML_VALIDATION,
                    severity=AuditSeverity.MEDIUM,
                    title=f"Duplicate ID '{element_id}'",
                    description="Multiple elements share the same ID, violating HTML standards.",
                    element_selector=f"#{element_id}",
                    element_html=str(element)[:200],
                    xpath=f"//*[@id='{element_id}']",
                    page_location=self._get_page_location(element),
                    seo_impact="May confuse search engine crawlers and break JavaScript",
                    fix_suggestion="Ensure each ID is unique across the page",
                    fix_priority=4,
                    estimated_fix_time=5,
                    current_value=f"Duplicate: {element_id}",
                    recommended_value="Unique ID",
                    test_method="automated"
                ))
            else:
                ids_found.append(element_id)
        
        # Check meta charset
        charset_meta = soup.find('meta', charset=True) or soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if not charset_meta:
            issues.append(AuditResult(
                result_id="missing_charset",
                category=AuditCategory.HTML_VALIDATION,
                severity=AuditSeverity.MEDIUM,
                title="Missing character encoding declaration",
                description="Page lacks meta charset declaration.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="May cause character encoding issues",
                fix_suggestion="Add <meta charset='UTF-8'> in head section",
                fix_priority=5,
                estimated_fix_time=1,
                current_value="Missing",
                recommended_value="UTF-8",
                test_method="automated"
            ))
        
        return issues
    
    async def _validate_meta_tags(self, soup: BeautifulSoup, page_url: str) -> List[AuditResult]:
        """Validate essential meta tags."""
        issues = []
        
        # Title tag validation
        title_tag = soup.find('title')
        if not title_tag:
            issues.append(AuditResult(
                result_id="missing_title_tag",
                category=AuditCategory.META_TAGS,
                severity=AuditSeverity.CRITICAL,
                title="Missing title tag",
                description="Page lacks a title tag, which is critical for SEO.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="Major negative impact on search rankings",
                fix_suggestion="Add a descriptive, unique title tag (30-60 characters)",
                fix_priority=10,
                estimated_fix_time=10,
                current_value="Missing",
                recommended_value="Descriptive page title",
                test_method="automated"
            ))
        else:
            title_text = title_tag.get_text().strip()
            title_length = len(title_text)
            
            if title_length == 0:
                issues.append(AuditResult(
                    result_id="empty_title_tag",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.CRITICAL,
                    title="Empty title tag",
                    description="Title tag is present but contains no text.",
                    element_selector="title",
                    element_html=str(title_tag),
                    xpath="//title",
                    page_location="head",
                    seo_impact="Major negative impact on search rankings",
                    fix_suggestion="Add descriptive text to the title tag",
                    fix_priority=10,
                    estimated_fix_time=10,
                    current_value="Empty",
                    recommended_value="Descriptive page title",
                    test_method="automated"
                ))
            elif title_length < 30:
                issues.append(AuditResult(
                    result_id="title_too_short",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.MEDIUM,
                    title="Title tag too short",
                    description=f"Title tag is {title_length} characters. Recommended: 30-60 characters.",
                    element_selector="title",
                    element_html=str(title_tag),
                    xpath="//title",
                    page_location="head",
                    seo_impact="May not utilize full search snippet space",
                    fix_suggestion="Expand title to 30-60 characters with relevant keywords",
                    fix_priority=6,
                    estimated_fix_time=15,
                    current_value=f"{title_length} characters",
                    recommended_value="30-60 characters",
                    test_method="automated"
                ))
            elif title_length > 60:
                issues.append(AuditResult(
                    result_id="title_too_long",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.MEDIUM,
                    title="Title tag too long",
                    description=f"Title tag is {title_length} characters. May be truncated in search results.",
                    element_selector="title",
                    element_html=str(title_tag),
                    xpath="//title",
                    page_location="head",
                    seo_impact="Title may be truncated in search results",
                    fix_suggestion="Shorten title to 60 characters or less",
                    fix_priority=5,
                    estimated_fix_time=10,
                    current_value=f"{title_length} characters",
                    recommended_value="≤60 characters",
                    test_method="automated"
                ))
        
        # Meta description validation
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            issues.append(AuditResult(
                result_id="missing_meta_description",
                category=AuditCategory.META_TAGS,
                severity=AuditSeverity.HIGH,
                title="Missing meta description",
                description="Page lacks meta description tag for search snippets.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="Search engines will generate description automatically",
                fix_suggestion="Add compelling meta description (120-160 characters)",
                fix_priority=8,
                estimated_fix_time=15,
                current_value="Missing",
                recommended_value="Compelling description",
                test_method="automated"
            ))
        else:
            desc_content = meta_desc.get('content', '').strip()
            desc_length = len(desc_content)
            
            if desc_length == 0:
                issues.append(AuditResult(
                    result_id="empty_meta_description",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.HIGH,
                    title="Empty meta description",
                    description="Meta description is present but contains no content.",
                    element_selector="meta[name='description']",
                    element_html=str(meta_desc),
                    xpath="//meta[@name='description']",
                    page_location="head",
                    seo_impact="Search engines will generate description automatically",
                    fix_suggestion="Add compelling content to meta description",
                    fix_priority=8,
                    estimated_fix_time=15,
                    current_value="Empty",
                    recommended_value="Compelling description",
                    test_method="automated"
                ))
            elif desc_length < 120:
                issues.append(AuditResult(
                    result_id="meta_description_too_short",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.MEDIUM,
                    title="Meta description too short",
                    description=f"Meta description is {desc_length} characters. Recommended: 120-160.",
                    element_selector="meta[name='description']",
                    element_html=str(meta_desc),
                    xpath="//meta[@name='description']",
                    page_location="head",
                    seo_impact="May not utilize full search snippet space",
                    fix_suggestion="Expand meta description to 120-160 characters",
                    fix_priority=5,
                    estimated_fix_time=10,
                    current_value=f"{desc_length} characters",
                    recommended_value="120-160 characters",
                    test_method="automated"
                ))
            elif desc_length > 160:
                issues.append(AuditResult(
                    result_id="meta_description_too_long",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.MEDIUM,
                    title="Meta description too long",
                    description=f"Meta description is {desc_length} characters. May be truncated.",
                    element_selector="meta[name='description']",
                    element_html=str(meta_desc),
                    xpath="//meta[@name='description']",
                    page_location="head",
                    seo_impact="Description may be truncated in search results",
                    fix_suggestion="Shorten meta description to 160 characters or less",
                    fix_priority=4,
                    estimated_fix_time=10,
                    current_value=f"{desc_length} characters",
                    recommended_value="≤160 characters",
                    test_method="automated"
                ))
        
        # Canonical tag validation
        canonical_tag = soup.find('link', rel='canonical')
        if not canonical_tag:
            issues.append(AuditResult(
                result_id="missing_canonical_tag",
                category=AuditCategory.META_TAGS,
                severity=AuditSeverity.HIGH,
                title="Missing canonical tag",
                description="Page lacks canonical URL declaration for duplicate content prevention.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="May cause duplicate content issues",
                fix_suggestion="Add canonical tag pointing to preferred URL version",
                fix_priority=7,
                estimated_fix_time=5,
                current_value="Missing",
                recommended_value="Canonical URL",
                test_method="automated"
            ))
        else:
            canonical_url = canonical_tag.get('href', '')
            if not canonical_url.startswith(('http://', 'https://')):
                issues.append(AuditResult(
                    result_id="relative_canonical_url",
                    category=AuditCategory.META_TAGS,
                    severity=AuditSeverity.MEDIUM,
                    title="Canonical URL is not absolute",
                    description="Canonical URL should be absolute, not relative.",
                    element_selector="link[rel='canonical']",
                    element_html=str(canonical_tag),
                    xpath="//link[@rel='canonical']",
                    page_location="head",
                    seo_impact="May confuse search engines about preferred URL",
                    fix_suggestion="Use absolute URL in canonical tag",
                    fix_priority=6,
                    estimated_fix_time=3,
                    current_value="Relative URL",
                    recommended_value="Absolute URL",
                    test_method="automated"
                ))
        
        # Viewport meta tag (for mobile)
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        if not viewport_tag:
            issues.append(AuditResult(
                result_id="missing_viewport_tag",
                category=AuditCategory.META_TAGS,
                severity=AuditSeverity.HIGH,
                title="Missing viewport meta tag",
                description="Page lacks viewport meta tag for mobile optimization.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="Poor mobile user experience affects mobile rankings",
                fix_suggestion="Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
                fix_priority=8,
                estimated_fix_time=2,
                current_value="Missing",
                recommended_value="width=device-width, initial-scale=1",
                test_method="automated"
            ))
        
        return issues
    
    async def _validate_schema_markup(self, soup: BeautifulSoup, page_url: str) -> Tuple[SchemaValidationResult, List[AuditResult]]:
        """Validate structured data/schema markup."""
        issues = []
        
        # Find JSON-LD structured data
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        microdata_elements = soup.find_all(attrs={'itemtype': True})
        
        schema_types = []
        valid_schemas = 0
        invalid_schemas = 0
        validation_errors = []
        missing_required_properties = []
        
        # Validate JSON-LD schemas
        for i, script in enumerate(json_ld_scripts):
            try:
                schema_data = json.loads(script.get_text())
                schema_type = schema_data.get('@type', '').lower()
                
                if schema_type:
                    schema_types.append(schema_type)
                    
                    # Validate against known schema requirements
                    if schema_type in self.schema_validation_rules:
                        rules = self.schema_validation_rules[schema_type]
                        
                        # Check required properties
                        for prop in rules['required_properties']:
                            if prop not in schema_data:
                                missing_required_properties.append(f"{schema_type}.{prop}")
                                validation_errors.append(f"Missing required property: {prop}")
                        
                        # If all required properties present, mark as valid
                        missing_required = [p for p in rules['required_properties'] if p not in schema_data]
                        if not missing_required:
                            valid_schemas += 1
                        else:
                            invalid_schemas += 1
                    else:
                        valid_schemas += 1  # Unknown schema type assumed valid
                        
            except json.JSONDecodeError as e:
                invalid_schemas += 1
                validation_errors.append(f"Invalid JSON-LD syntax: {str(e)}")
                issues.append(AuditResult(
                    result_id=f"invalid_json_ld_{i}",
                    category=AuditCategory.SCHEMA_MARKUP,
                    severity=AuditSeverity.HIGH,
                    title="Invalid JSON-LD schema markup",
                    description=f"JSON-LD script contains invalid JSON syntax: {str(e)}",
                    element_selector=f"script[type='application/ld+json']:nth-of-type({i+1})",
                    element_html=str(script)[:200],
                    xpath=f"//script[@type='application/ld+json'][{i+1}]",
                    page_location="head",
                    seo_impact="Invalid schema markup ignored by search engines",
                    fix_suggestion="Fix JSON syntax errors in structured data",
                    fix_priority=7,
                    estimated_fix_time=15,
                    current_value="Invalid JSON",
                    recommended_value="Valid JSON-LD",
                    test_method="automated"
                ))
        
        # Basic microdata validation
        for element in microdata_elements:
            itemtype = element.get('itemtype', '')
            if itemtype:
                schema_type = itemtype.split('/')[-1].lower()
                schema_types.append(schema_type)
                valid_schemas += 1  # Basic count, would need deeper validation
        
        total_schemas = valid_schemas + invalid_schemas
        structured_data_count = len(json_ld_scripts) + len(microdata_elements)
        
        # Calculate completeness score
        schema_completeness_score = 0.0
        if total_schemas > 0:
            schema_completeness_score = valid_schemas / total_schemas
        
        # Check for missing essential schemas
        if not schema_types:
            issues.append(AuditResult(
                result_id="no_structured_data",
                category=AuditCategory.SCHEMA_MARKUP,
                severity=AuditSeverity.MEDIUM,
                title="No structured data found",
                description="Page lacks structured data markup for enhanced search results.",
                element_selector="head",
                element_html="<head>",
                xpath="//head",
                page_location="head",
                seo_impact="Missing enhanced search result features",
                fix_suggestion="Add relevant schema markup (Article, Organization, etc.)",
                fix_priority=5,
                estimated_fix_time=30,
                current_value="None",
                recommended_value="Relevant schema types",
                test_method="automated"
            ))
        
        # Check for missing recommended schemas based on content type
        content_indicators = {
            'article': ['article', 'blog', 'post', 'news'],
            'product': ['product', 'shop', 'buy', 'price'],
            'organization': ['about', 'contact', 'company'],
            'breadcrumblist': ['breadcrumb', 'navigation']
        }
        
        page_content = soup.get_text().lower()
        for schema_type, indicators in content_indicators.items():
            if any(indicator in page_content for indicator in indicators):
                if schema_type not in [s.lower() for s in schema_types]:
                    issues.append(AuditResult(
                        result_id=f"missing_{schema_type}_schema",
                        category=AuditCategory.SCHEMA_MARKUP,
                        severity=AuditSeverity.LOW,
                        title=f"Missing {schema_type} schema markup",
                        description=f"Page appears to be {schema_type}-related but lacks corresponding schema.",
                        element_selector="body",
                        element_html="",
                        xpath="//body",
                        page_location="content",
                        seo_impact="Missing enhanced search result opportunities",
                        fix_suggestion=f"Add {schema_type} schema markup",
                        fix_priority=3,
                        estimated_fix_time=20,
                        current_value="Missing",
                        recommended_value=f"{schema_type} schema",
                        test_method="automated"
                    ))
        
        schema_result = SchemaValidationResult(
            schema_types=list(set(schema_types)),
            valid_schemas=valid_schemas,
            invalid_schemas=invalid_schemas,
            missing_required_properties=missing_required_properties,
            validation_errors=validation_errors,
            structured_data_count=structured_data_count,
            schema_completeness_score=schema_completeness_score
        )
        
        return schema_result, issues
    
    async def _validate_images(self, soup: BeautifulSoup, page_url: str) -> List[AuditResult]:
        """Validate image optimization and SEO factors."""
        issues = []
        
        images = soup.find_all('img')
        for i, img in enumerate(images):
            src = img.get('src', '')
            alt = img.get('alt')
            width = img.get('width')
            height = img.get('height')
            loading = img.get('loading')
            
            # Missing alt attribute
            if alt is None:
                issues.append(AuditResult(
                    result_id=f"img_missing_alt_{i}",
                    category=AuditCategory.IMAGES,
                    severity=AuditSeverity.HIGH,
                    title="Image missing alt attribute",
                    description=f"Image with src '{src}' lacks alt attribute for accessibility and SEO.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    seo_impact="Images not indexed properly, accessibility issues",
                    fix_suggestion="Add descriptive alt text that describes image content",
                    fix_priority=7,
                    estimated_fix_time=3,
                    current_value="Missing",
                    recommended_value="Descriptive alt text",
                    test_method="automated"
                ))
            
            # Missing dimensions
            if not width or not height:
                issues.append(AuditResult(
                    result_id=f"img_missing_dimensions_{i}",
                    category=AuditCategory.IMAGES,
                    severity=AuditSeverity.MEDIUM,
                    title="Image missing width/height attributes",
                    description="Image lacks dimensions which can cause layout shift.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    seo_impact="May cause cumulative layout shift affecting Core Web Vitals",
                    fix_suggestion="Add width and height attributes to prevent layout shift",
                    fix_priority=5,
                    estimated_fix_time=2,
                    current_value="Missing dimensions",
                    recommended_value="Width and height specified",
                    test_method="automated"
                ))
            
            # Missing lazy loading
            if i > 2 and loading != 'lazy':  # Skip first few images (above fold)
                issues.append(AuditResult(
                    result_id=f"img_missing_lazy_loading_{i}",
                    category=AuditCategory.IMAGES,
                    severity=AuditSeverity.LOW,
                    title="Image not using lazy loading",
                    description="Below-fold image could benefit from lazy loading.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    seo_impact="Minor impact on page load speed",
                    fix_suggestion="Add loading='lazy' to below-fold images",
                    fix_priority=3,
                    estimated_fix_time=1,
                    current_value="Eager loading",
                    recommended_value="loading='lazy'",
                    test_method="automated"
                ))
            
            # Check for old image formats
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                issues.append(AuditResult(
                    result_id=f"img_old_format_{i}",
                    category=AuditCategory.IMAGES,
                    severity=AuditSeverity.LOW,
                    title="Image using old format",
                    description="Consider using modern image formats like WebP or AVIF for better compression.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    seo_impact="Larger file sizes affect page load speed",
                    fix_suggestion="Convert to WebP or AVIF format with fallbacks",
                    fix_priority=2,
                    estimated_fix_time=10,
                    current_value="Legacy format",
                    recommended_value="WebP/AVIF format",
                    test_method="automated"
                ))
        
        return issues
    
    async def _validate_internal_links(self, soup: BeautifulSoup, page_url: str) -> Tuple[List[AuditResult], int]:
        """Validate internal linking structure."""
        issues = []
        
        # Get all links
        links = soup.find_all('a', href=True)
        internal_links = []
        external_links = []
        
        parsed_base_url = urlparse(page_url)
        base_domain = parsed_base_url.netloc
        
        for link in links:
            href = link.get('href', '')
            
            # Skip anchor links and javascript
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            # Determine if internal or external
            if href.startswith('http'):
                parsed_href = urlparse(href)
                if parsed_href.netloc == base_domain:
                    internal_links.append(link)
                else:
                    external_links.append(link)
            else:
                # Relative URL assumed to be internal
                internal_links.append(link)
        
        internal_links_count = len(internal_links)
        
        # Check for insufficient internal linking
        if internal_links_count < 3:
            issues.append(AuditResult(
                result_id="insufficient_internal_links",
                category=AuditCategory.INTERNAL_LINKS,
                severity=AuditSeverity.MEDIUM,
                title="Insufficient internal linking",
                description=f"Page has only {internal_links_count} internal links. Recommended: 3-8.",
                element_selector="body",
                element_html="",
                xpath="//body",
                page_location="content",
                seo_impact="Reduced link equity distribution and crawlability",
                fix_suggestion="Add relevant internal links to related content",
                fix_priority=5,
                estimated_fix_time=20,
                current_value=f"{internal_links_count} links",
                recommended_value="3-8 internal links",
                test_method="automated"
            ))
        
        # Check for links without descriptive anchor text
        vague_anchors = ['click here', 'read more', 'more', 'here', 'link']
        for i, link in enumerate(internal_links):
            anchor_text = link.get_text().strip().lower()
            if anchor_text in vague_anchors:
                issues.append(AuditResult(
                    result_id=f"vague_anchor_text_{i}",
                    category=AuditCategory.INTERNAL_LINKS,
                    severity=AuditSeverity.MEDIUM,
                    title="Vague anchor text",
                    description=f"Link uses non-descriptive anchor text: '{anchor_text}'",
                    element_selector=self._generate_selector(link),
                    element_html=str(link)[:200],
                    xpath=self._generate_xpath(link, soup),
                    page_location=self._get_page_location(link),
                    seo_impact="Reduced context for search engines and users",
                    fix_suggestion="Use descriptive anchor text that indicates link destination",
                    fix_priority=4,
                    estimated_fix_time=5,
                    current_value=f"'{anchor_text}'",
                    recommended_value="Descriptive anchor text",
                    test_method="automated"
                ))
        
        # Check external links without nofollow (when appropriate)
        for link in external_links:
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = rel.split()
            
            # This is a simplified check - in practice you'd want more nuanced rules
            if 'nofollow' not in rel and 'sponsored' not in rel:
                href = link.get('href', '')
                # Skip well-known trusted domains
                trusted_domains = ['wikipedia.org', 'mozilla.org', 'w3.org']
                if not any(domain in href for domain in trusted_domains):
                    issues.append(AuditResult(
                        result_id=f"external_link_no_nofollow_{hash(href)}",
                        category=AuditCategory.INTERNAL_LINKS,
                        severity=AuditSeverity.LOW,
                        title="External link without rel attribute",
                        description="Consider adding rel='nofollow' to untrusted external links.",
                        element_selector=self._generate_selector(link),
                        element_html=str(link)[:200],
                        xpath=self._generate_xpath(link, soup),
                        page_location=self._get_page_location(link),
                        seo_impact="May pass link equity to external sites unnecessarily",
                        fix_suggestion="Add rel='nofollow' or rel='sponsored' as appropriate",
                        fix_priority=2,
                        estimated_fix_time=2,
                        current_value="No rel attribute",
                        recommended_value="rel='nofollow'",
                        test_method="automated"
                    ))
        
        return issues, internal_links_count
    
    async def _validate_mobile_usability(self, soup: BeautifulSoup, page_url: str) -> List[AuditResult]:
        """Validate mobile usability factors."""
        issues = []
        
        # Check viewport meta tag
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        if viewport_tag:
            content = viewport_tag.get('content', '')
            if 'user-scalable=no' in content:
                issues.append(AuditResult(
                    result_id="viewport_blocks_scaling",
                    category=AuditCategory.MOBILE_USABILITY,
                    severity=AuditSeverity.MEDIUM,
                    title="Viewport blocks user scaling",
                    description="Viewport meta tag prevents users from zooming, affecting accessibility.",
                    element_selector="meta[name='viewport']",
                    element_html=str(viewport_tag),
                    xpath="//meta[@name='viewport']",
                    page_location="head",
                    seo_impact="Poor mobile user experience affects mobile rankings",
                    fix_suggestion="Remove 'user-scalable=no' from viewport content",
                    fix_priority=6,
                    estimated_fix_time=2,
                    current_value="user-scalable=no",
                    recommended_value="Allow user scaling",
                    test_method="automated"
                ))
        
        # Check for fixed width elements
        elements_with_style = soup.find_all(attrs={'style': True})
        for element in elements_with_style:
            style = element.get('style', '')
            if 'width:' in style and 'px' in style:
                # Extract width value
                width_match = re.search(r'width:\s*(\d+)px', style)
                if width_match:
                    width = int(width_match.group(1))
                    if width > 320:  # Wider than narrow mobile screens
                        issues.append(AuditResult(
                            result_id=f"fixed_width_element_{hash(str(element))}",
                            category=AuditCategory.MOBILE_USABILITY,
                            severity=AuditSeverity.LOW,
                            title="Element with fixed width",
                            description=f"Element has fixed width of {width}px which may not be mobile-friendly.",
                            element_selector=self._generate_selector(element),
                            element_html=str(element)[:200],
                            xpath=self._generate_xpath(element, soup),
                            page_location=self._get_page_location(element),
                            seo_impact="May cause horizontal scrolling on mobile devices",
                            fix_suggestion="Use relative widths (%, max-width) for responsive design",
                            fix_priority=3,
                            estimated_fix_time=10,
                            current_value=f"{width}px fixed width",
                            recommended_value="Responsive width",
                            test_method="automated"
                        ))
        
        return issues
    
    async def _validate_security_factors(self, response_headers: Dict[str, str], page_url: str) -> List[AuditResult]:
        """Validate security-related factors affecting SEO."""
        issues = []
        
        parsed_url = urlparse(page_url)
        
        # Check HTTPS
        if parsed_url.scheme != 'https':
            issues.append(AuditResult(
                result_id="not_using_https",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.HIGH,
                title="Site not using HTTPS",
                description="Page served over HTTP instead of secure HTTPS.",
                element_selector="html",
                element_html="",
                xpath="//html",
                page_location="protocol",
                seo_impact="HTTPS is a ranking factor; HTTP sites may be penalized",
                fix_suggestion="Implement SSL certificate and redirect HTTP to HTTPS",
                fix_priority=9,
                estimated_fix_time=60,
                current_value="HTTP",
                recommended_value="HTTPS",
                test_method="automated"
            ))
        
        # Check security headers
        security_headers = {
            'X-Frame-Options': 'Prevents clickjacking attacks',
            'X-Content-Type-Options': 'Prevents MIME type sniffing',
            'X-XSS-Protection': 'Provides XSS protection',
            'Strict-Transport-Security': 'Enforces HTTPS connections'
        }
        
        for header, description in security_headers.items():
            if header not in response_headers:
                issues.append(AuditResult(
                    result_id=f"missing_security_header_{header.lower().replace('-', '_')}",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.LOW,
                    title=f"Missing {header} header",
                    description=f"Response lacks {header} security header. {description}.",
                    element_selector="html",
                    element_html="",
                    xpath="//html",
                    page_location="headers",
                    seo_impact="Minor security concerns, may affect user trust",
                    fix_suggestion=f"Add {header} security header to server response",
                    fix_priority=2,
                    estimated_fix_time=15,
                    current_value="Missing",
                    recommended_value=f"{header} header present",
                    test_method="automated"
                ))
        
        return issues
    
    async def _validate_crawlability(self, soup: BeautifulSoup, page_url: str) -> List[AuditResult]:
        """Validate crawlability and indexability factors."""
        issues = []
        
        # Check robots meta tag
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        if robots_meta:
            content = robots_meta.get('content', '').lower()
            if 'noindex' in content:
                issues.append(AuditResult(
                    result_id="page_blocked_from_indexing",
                    category=AuditCategory.INDEXABILITY,
                    severity=AuditSeverity.CRITICAL,
                    title="Page blocked from indexing",
                    description="Robots meta tag contains 'noindex' directive.",
                    element_selector="meta[name='robots']",
                    element_html=str(robots_meta),
                    xpath="//meta[@name='robots']",
                    page_location="head",
                    seo_impact="Page will not appear in search results",
                    fix_suggestion="Remove 'noindex' if page should be indexed",
                    fix_priority=10,
                    estimated_fix_time=2,
                    current_value="noindex",
                    recommended_value="index (or remove meta tag)",
                    test_method="automated"
                ))
            
            if 'nofollow' in content:
                issues.append(AuditResult(
                    result_id="page_blocks_link_following",
                    category=AuditCategory.CRAWLABILITY,
                    severity=AuditSeverity.HIGH,
                    title="Page blocks link following",
                    description="Robots meta tag contains 'nofollow' directive.",
                    element_selector="meta[name='robots']",
                    element_html=str(robots_meta),
                    xpath="//meta[@name='robots']",
                    page_location="head",
                    seo_impact="Search engines won't follow links from this page",
                    fix_suggestion="Remove 'nofollow' if links should be followed",
                    fix_priority=7,
                    estimated_fix_time=2,
                    current_value="nofollow",
                    recommended_value="follow (or remove meta tag)",
                    test_method="automated"
                ))
        
        # Check for excessive use of JavaScript for content
        script_tags = soup.find_all('script')
        if len(script_tags) > 10:
            issues.append(AuditResult(
                result_id="excessive_javascript",
                category=AuditCategory.CRAWLABILITY,
                severity=AuditSeverity.MEDIUM,
                title="Excessive JavaScript usage",
                description=f"Page contains {len(script_tags)} script tags, which may affect crawlability.",
                element_selector="body",
                element_html="",
                xpath="//body",
                page_location="head",
                seo_impact="Heavy JavaScript may prevent proper content indexing",
                fix_suggestion="Minimize JavaScript and ensure critical content is in HTML",
                fix_priority=4,
                estimated_fix_time=120,
                current_value=f"{len(script_tags)} script tags",
                recommended_value="Minimal JavaScript usage",
                test_method="automated"
            ))
        
        return issues
    
    def _generate_selector(self, element) -> str:
        """Generate CSS selector for element."""
        if element.get('id'):
            return f"#{element['id']}"
        elif element.get('class'):
            classes = '.'.join(element['class'])
            return f"{element.name}.{classes}"
        else:
            return element.name
    
    def _generate_xpath(self, element, soup: BeautifulSoup) -> str:
        """Generate XPath for element."""
        if element.get('id'):
            return f"//{element.name}[@id='{element['id']}']"
        else:
            return f"//{element.name}"
    
    def _get_page_location(self, element) -> str:
        """Determine page location of element."""
        current = element
        while current and hasattr(current, 'parent'):
            if hasattr(current, 'name'):
                if current.name in ['header', 'nav', 'main', 'footer', 'aside']:
                    return current.name
            current = current.parent
        return "content"
    
    def _generate_audit_result(
        self,
        page_url: str,
        issues: List[AuditResult],
        soup: BeautifulSoup,
        response_headers: Dict[str, str],
        schema_result: Optional[SchemaValidationResult],
        internal_links_count: int
    ) -> TechnicalSEOAuditResult:
        """Generate comprehensive technical SEO audit result."""
        
        # Count issues by severity
        critical_issues = len([i for i in issues if i.severity == AuditSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == AuditSeverity.HIGH])
        medium_issues = len([i for i in issues if i.severity == AuditSeverity.MEDIUM])
        low_issues = len([i for i in issues if i.severity == AuditSeverity.LOW])
        
        # Count by category
        issues_by_category = {}
        for category in AuditCategory:
            count = len([i for i in issues if i.category == category])
            if count > 0:
                issues_by_category[category] = count
        
        # Check basic SEO elements
        title_tag_present = bool(soup.find('title'))
        meta_description_present = bool(soup.find('meta', attrs={'name': 'description'}))
        canonical_tag_present = bool(soup.find('link', rel='canonical'))
        robots_meta_present = bool(soup.find('meta', attrs={'name': 'robots'}))
        
        # Technical metrics
        parsed_url = urlparse(page_url)
        https_enabled = parsed_url.scheme == 'https'
        
        # Mobile friendliness (basic check)
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        mobile_friendly = bool(viewport_tag)
        
        # HTML validation error count
        html_validation_errors = len([i for i in issues if i.category == AuditCategory.HTML_VALIDATION])
        
        # Calculate meta tags score
        meta_score = 0
        if title_tag_present:
            meta_score += 25
        if meta_description_present:
            meta_score += 25
        if canonical_tag_present:
            meta_score += 25
        if robots_meta_present:
            meta_score += 15
        
        # Bonus points for proper lengths
        title_tag = soup.find('title')
        if title_tag:
            title_length = len(title_tag.get_text())
            if 30 <= title_length <= 60:
                meta_score += 10
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            desc_length = len(meta_desc.get('content', ''))
            if 120 <= desc_length <= 160:
                meta_score += 10
        
        meta_tags_score = min(100.0, meta_score)
        
        # Generate recommendations
        priority_fixes = []
        quick_wins = []
        optimization_suggestions = []
        
        # Critical issues first
        if critical_issues > 0:
            priority_fixes.append(f"Fix {critical_issues} critical issues immediately")
        
        # High-impact issues
        if not title_tag_present:
            priority_fixes.append("Add title tag - critical for SEO")
        if not meta_description_present:
            priority_fixes.append("Add meta description for better search snippets")
        if not https_enabled:
            priority_fixes.append("Implement HTTPS for security and SEO benefits")
        
        # Quick wins
        if not canonical_tag_present:
            quick_wins.append("Add canonical tag to prevent duplicate content issues")
        if not mobile_friendly:
            quick_wins.append("Add viewport meta tag for mobile optimization")
        if html_validation_errors > 0:
            quick_wins.append(f"Fix {html_validation_errors} HTML validation errors")
        
        # Optimization suggestions
        if internal_links_count < 3:
            optimization_suggestions.append("Add more internal links to improve site navigation")
        if not schema_result or schema_result.structured_data_count == 0:
            optimization_suggestions.append("Implement structured data for enhanced search results")
        
        return TechnicalSEOAuditResult(
            page_url=page_url,
            audit_timestamp=datetime.now(timezone.utc),
            total_issues=len(issues),
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            issues_by_category=issues_by_category,
            html_validation_errors=html_validation_errors,
            meta_tags_score=meta_tags_score,
            schema_validation=schema_result or SchemaValidationResult(
                schema_types=[], valid_schemas=0, invalid_schemas=0,
                missing_required_properties=[], validation_errors=[],
                structured_data_count=0, schema_completeness_score=0.0
            ),
            internal_links_count=internal_links_count,
            orphaned_pages_detected=False,  # Would need site-wide analysis
            page_size_kb=None,  # Would need response size calculation
            load_time_ms=None,  # Would need performance measurement
            mobile_friendly=mobile_friendly,
            https_enabled=https_enabled,
            title_tag_present=title_tag_present,
            meta_description_present=meta_description_present,
            canonical_tag_present=canonical_tag_present,
            robots_meta_present=robots_meta_present,
            issues=issues,
            priority_fixes=priority_fixes,
            quick_wins=quick_wins,
            optimization_suggestions=optimization_suggestions
        )
    
    def export_audit_results(
        self,
        result: TechnicalSEOAuditResult,
        output_path: Path,
        format: str = "json"
    ) -> None:
        """Export technical SEO audit results to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        data = {
            "page_url": result.page_url,
            "audit_timestamp": result.audit_timestamp.isoformat(),
            "summary": {
                "seo_health_score": result.seo_health_score,
                "total_issues": result.total_issues,
                "critical_issues": result.critical_issues,
                "high_issues": result.high_issues,
                "medium_issues": result.medium_issues,
                "low_issues": result.low_issues,
                "meta_tags_score": result.meta_tags_score,
                "mobile_friendly": result.mobile_friendly,
                "https_enabled": result.https_enabled
            },
            "seo_fundamentals": {
                "title_tag_present": result.title_tag_present,
                "meta_description_present": result.meta_description_present,
                "canonical_tag_present": result.canonical_tag_present,
                "robots_meta_present": result.robots_meta_present
            },
            "issues_by_category": {cat.value: count for cat, count in result.issues_by_category.items()},
            "schema_validation": {
                "schema_types": result.schema_validation.schema_types,
                "valid_schemas": result.schema_validation.valid_schemas,
                "invalid_schemas": result.schema_validation.invalid_schemas,
                "structured_data_count": result.schema_validation.structured_data_count,
                "schema_completeness_score": result.schema_validation.schema_completeness_score
            },
            "recommendations": {
                "priority_fixes": result.priority_fixes,
                "quick_wins": result.quick_wins,
                "optimization_suggestions": result.optimization_suggestions
            },
            "issues": [
                {
                    "result_id": issue.result_id,
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "title": issue.title,
                    "description": issue.description,
                    "seo_impact": issue.seo_impact,
                    "fix_suggestion": issue.fix_suggestion,
                    "fix_priority": issue.fix_priority,
                    "estimated_fix_time": issue.estimated_fix_time,
                    "current_value": issue.current_value,
                    "recommended_value": issue.recommended_value
                }
                for issue in result.issues
            ]
        }
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Technical SEO audit results exported to {output_path}")
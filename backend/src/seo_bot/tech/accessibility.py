"""Accessibility and UX optimization system with WCAG compliance checking."""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Comment

from ..config import Settings


logger = logging.getLogger(__name__)


class WCAGLevel(Enum):
    """WCAG compliance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class AccessibilityCategory(Enum):
    """Categories of accessibility issues."""
    KEYBOARD_NAVIGATION = "keyboard_navigation"
    SCREEN_READER = "screen_reader"
    COLOR_CONTRAST = "color_contrast"
    IMAGES_MEDIA = "images_media"
    FORMS_INPUTS = "forms_inputs"
    HEADINGS_STRUCTURE = "headings_structure"
    LINKS_NAVIGATION = "links_navigation"
    FOCUS_MANAGEMENT = "focus_management"
    LAYOUT_SHIFT = "layout_shift"
    MOTION_ANIMATION = "motion_animation"


class IssueSeverity(Enum):
    """Severity levels for accessibility issues."""
    CRITICAL = "critical"  # Blocks users from completing tasks
    HIGH = "high"         # Significantly impacts usability
    MEDIUM = "medium"     # Minor usability impact
    LOW = "low"          # Enhancement opportunity
    INFO = "info"        # Best practice recommendation


@dataclass
class AccessibilityIssue:
    """Represents an accessibility issue found on a page."""
    
    issue_id: str
    category: AccessibilityCategory
    severity: IssueSeverity
    wcag_level: WCAGLevel
    wcag_criteria: str  # e.g., "1.3.1", "2.4.1"
    title: str
    description: str
    
    # Element information
    element_selector: str
    element_html: str
    xpath: str
    
    # Context
    page_location: str  # "header", "main", "footer", etc.
    
    # Fix information
    fix_suggestion: str
    fix_complexity: str  # "easy", "medium", "complex"
    estimated_fix_time: int  # minutes
    
    # Testing details
    test_method: str  # "automated", "manual", "lighthouse"
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_blocking(self) -> bool:
        """Check if issue blocks user task completion."""
        return self.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]


@dataclass
class AccessibilityAuditResult:
    """Results from an accessibility audit."""
    
    page_url: str
    audit_timestamp: datetime
    wcag_target_level: WCAGLevel
    
    # Compliance metrics
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    
    # Category breakdown
    issues_by_category: Dict[AccessibilityCategory, int]
    
    # Compliance status
    wcag_aa_compliant: bool
    lighthouse_accessibility_score: Optional[int]
    blocking_issues_count: int
    
    # Fix estimates
    estimated_fix_time_hours: float
    easy_fixes: int
    medium_fixes: int
    complex_fixes: int
    
    # Issues detail
    issues: List[AccessibilityIssue]
    
    # Recommendations
    priority_fixes: List[str]
    quick_wins: List[str]
    
    @property
    def compliance_percentage(self) -> float:
        """Calculate overall compliance percentage."""
        if self.total_issues == 0:
            return 100.0
        
        # Weight issues by severity
        weighted_issues = (
            self.critical_issues * 4 +
            self.high_issues * 3 +
            self.medium_issues * 2 +
            self.low_issues * 1
        )
        
        # Calculate max possible weight (if all were critical)
        max_weight = self.total_issues * 4
        
        compliance = max(0, (max_weight - weighted_issues) / max_weight * 100)
        return round(compliance, 1)


class AccessibilityChecker:
    """Comprehensive accessibility checker with WCAG compliance validation."""
    
    def __init__(self, settings: Optional[Settings] = None, target_level: WCAGLevel = WCAGLevel.AA):
        """Initialize the accessibility checker."""
        self.settings = settings or Settings()
        self.target_level = target_level
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Color contrast ratios for WCAG compliance
        self.contrast_ratios = {
            WCAGLevel.AA: {"normal": 4.5, "large": 3.0},
            WCAGLevel.AAA: {"normal": 7.0, "large": 4.5}
        }
        
        # Common accessibility patterns and rules
        self.accessibility_rules = self._initialize_accessibility_rules()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _initialize_accessibility_rules(self) -> Dict[str, Any]:
        """Initialize accessibility validation rules."""
        return {
            "required_attributes": {
                "img": ["alt"],
                "input": ["id", "label_or_aria_label"],
                "button": ["accessible_name"],
                "a": ["accessible_name"],
                "iframe": ["title"],
                "object": ["title_or_aria_label"],
                "area": ["alt"],
                "optgroup": ["label"],
                "fieldset": ["legend"]
            },
            "heading_hierarchy": {
                "skip_levels": False,
                "multiple_h1": False,
                "missing_h1": False
            },
            "keyboard_navigation": {
                "focusable_elements": ["a", "button", "input", "select", "textarea", "details", "summary"],
                "skip_links": True,
                "focus_indicators": True
            },
            "color_contrast": {
                "min_ratio_normal": self.contrast_ratios[self.target_level]["normal"],
                "min_ratio_large": self.contrast_ratios[self.target_level]["large"]
            },
            "motion_preferences": {
                "respect_prefers_reduced_motion": True,
                "autoplay_restrictions": True
            }
        }
    
    async def audit_page_accessibility(
        self,
        page_url: str,
        include_lighthouse: bool = True,
        user_agent: str = None
    ) -> AccessibilityAuditResult:
        """Perform comprehensive accessibility audit on a page."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        logger.info(f"Starting accessibility audit for: {page_url}")
        
        # Fetch page content
        html_content = await self._fetch_page_content(page_url, user_agent)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Run all accessibility checks
        issues = []
        
        # Automated checks
        issues.extend(await self._check_images_alt_text(soup, page_url))
        issues.extend(await self._check_form_labels(soup, page_url))
        issues.extend(await self._check_heading_structure(soup, page_url))
        issues.extend(await self._check_keyboard_navigation(soup, page_url))
        issues.extend(await self._check_links_accessibility(soup, page_url))
        issues.extend(await self._check_color_contrast(soup, page_url))
        issues.extend(await self._check_focus_management(soup, page_url))
        issues.extend(await self._check_screen_reader_compatibility(soup, page_url))
        issues.extend(await self._check_layout_shift_prevention(soup, page_url))
        issues.extend(await self._check_motion_accessibility(soup, page_url))
        
        # Get Lighthouse accessibility score if requested
        lighthouse_score = None
        if include_lighthouse and self.settings.pagespeed_api_key:
            try:
                lighthouse_score = await self._get_lighthouse_accessibility_score(page_url)
            except Exception as e:
                logger.warning(f"Could not fetch Lighthouse score: {e}")
        
        # Generate audit result
        return self._generate_audit_result(
            page_url=page_url,
            issues=issues,
            lighthouse_score=lighthouse_score
        )
    
    async def _fetch_page_content(self, url: str, user_agent: str = None) -> str:
        """Fetch page content for analysis."""
        headers = {
            'User-Agent': user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise RuntimeError(f"Failed to fetch page: HTTP {response.status}")
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {url}: {e}")
            raise RuntimeError(f"Network error: {e}")
    
    async def _check_images_alt_text(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check for missing or inadequate alt text on images."""
        issues = []
        
        images = soup.find_all('img')
        for i, img in enumerate(images):
            alt_text = img.get('alt')
            src = img.get('src', '')
            
            # Missing alt attribute
            if alt_text is None:
                issues.append(AccessibilityIssue(
                    issue_id=f"img_missing_alt_{i}",
                    category=AccessibilityCategory.IMAGES_MEDIA,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="1.1.1",
                    title="Image missing alt attribute",
                    description=f"Image with src '{src}' is missing the alt attribute, making it inaccessible to screen readers.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    fix_suggestion="Add descriptive alt text that conveys the purpose and content of the image.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
            
            # Empty alt text for non-decorative images
            elif alt_text == "" and not self._is_decorative_image(img):
                issues.append(AccessibilityIssue(
                    issue_id=f"img_empty_alt_{i}",
                    category=AccessibilityCategory.IMAGES_MEDIA,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="1.1.1",
                    title="Important image has empty alt text",
                    description=f"Image appears to be informative but has empty alt text.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    fix_suggestion="Add descriptive alt text or role='presentation' if truly decorative.",
                    fix_complexity="easy",
                    estimated_fix_time=3,
                    test_method="automated"
                ))
            
            # Alt text quality checks
            elif alt_text and len(alt_text) > 125:
                issues.append(AccessibilityIssue(
                    issue_id=f"img_alt_too_long_{i}",
                    category=AccessibilityCategory.IMAGES_MEDIA,
                    severity=IssueSeverity.LOW,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="1.1.1",
                    title="Alt text is too long",
                    description=f"Alt text is {len(alt_text)} characters. Consider shortening to under 125 characters.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    fix_suggestion="Shorten alt text to be more concise while retaining essential information.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_form_labels(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check for missing form labels and proper labeling."""
        issues = []
        
        # Check input elements
        inputs = soup.find_all(['input', 'textarea', 'select'])
        for i, input_elem in enumerate(inputs):
            input_type = input_elem.get('type', 'text')
            
            # Skip hidden inputs and buttons
            if input_type in ['hidden', 'submit', 'button', 'reset']:
                continue
            
            input_id = input_elem.get('id')
            aria_label = input_elem.get('aria-label')
            aria_labelledby = input_elem.get('aria-labelledby')
            
            # Look for associated label
            label_element = None
            if input_id:
                label_element = soup.find('label', {'for': input_id})
            
            # Check if input has any form of labeling
            has_label = any([label_element, aria_label, aria_labelledby])
            
            if not has_label:
                issues.append(AccessibilityIssue(
                    issue_id=f"input_missing_label_{i}",
                    category=AccessibilityCategory.FORMS_INPUTS,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="3.3.2",
                    title="Form input missing label",
                    description=f"Input element of type '{input_type}' lacks proper labeling.",
                    element_selector=self._generate_selector(input_elem),
                    element_html=str(input_elem)[:200],
                    xpath=self._generate_xpath(input_elem, soup),
                    page_location=self._get_page_location(input_elem),
                    fix_suggestion="Add a <label> element with 'for' attribute, or use aria-label/aria-labelledby.",
                    fix_complexity="easy",
                    estimated_fix_time=3,
                    test_method="automated"
                ))
        
        # Check for fieldsets without legends
        fieldsets = soup.find_all('fieldset')
        for i, fieldset in enumerate(fieldsets):
            legend = fieldset.find('legend')
            if not legend:
                issues.append(AccessibilityIssue(
                    issue_id=f"fieldset_missing_legend_{i}",
                    category=AccessibilityCategory.FORMS_INPUTS,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="1.3.1",
                    title="Fieldset missing legend",
                    description="Fieldset element lacks a legend to describe the group of form controls.",
                    element_selector=self._generate_selector(fieldset),
                    element_html=str(fieldset)[:200],
                    xpath=self._generate_xpath(fieldset, soup),
                    page_location=self._get_page_location(fieldset),
                    fix_suggestion="Add a <legend> element as the first child of the fieldset.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_heading_structure(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check heading hierarchy and structure."""
        issues = []
        
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading_levels = [int(h.name[1]) for h in headings]
        
        # Check for missing H1
        if 1 not in heading_levels:
            issues.append(AccessibilityIssue(
                issue_id="missing_h1",
                category=AccessibilityCategory.HEADINGS_STRUCTURE,
                severity=IssueSeverity.HIGH,
                wcag_level=WCAGLevel.AA,
                wcag_criteria="2.4.1",
                title="Page missing H1 heading",
                description="Page lacks a main H1 heading for proper document structure.",
                element_selector="body",
                element_html="<body>",
                xpath="//body",
                page_location="main",
                fix_suggestion="Add an H1 heading that describes the main topic of the page.",
                fix_complexity="easy",
                estimated_fix_time=5,
                test_method="automated"
            ))
        
        # Check for multiple H1s
        h1_count = heading_levels.count(1)
        if h1_count > 1:
            issues.append(AccessibilityIssue(
                issue_id="multiple_h1",
                category=AccessibilityCategory.HEADINGS_STRUCTURE,
                severity=IssueSeverity.MEDIUM,
                wcag_level=WCAGLevel.AA,
                wcag_criteria="2.4.1",
                title="Multiple H1 headings found",
                description=f"Page has {h1_count} H1 headings. Use only one H1 per page.",
                element_selector="h1",
                element_html="",
                xpath="//h1",
                page_location="main",
                fix_suggestion="Use only one H1 for the main page topic. Convert others to H2 or lower.",
                fix_complexity="medium",
                estimated_fix_time=10,
                test_method="automated"
            ))
        
        # Check for skipped heading levels
        for i in range(len(heading_levels) - 1):
            current_level = heading_levels[i]
            next_level = heading_levels[i + 1]
            
            if next_level > current_level + 1:
                issues.append(AccessibilityIssue(
                    issue_id=f"skipped_heading_level_{i}",
                    category=AccessibilityCategory.HEADINGS_STRUCTURE,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="2.4.1",
                    title="Skipped heading level",
                    description=f"Heading level jumps from H{current_level} to H{next_level}, skipping levels.",
                    element_selector=f"h{next_level}",
                    element_html=str(headings[i + 1])[:200],
                    xpath=self._generate_xpath(headings[i + 1], soup),
                    page_location=self._get_page_location(headings[i + 1]),
                    fix_suggestion="Use sequential heading levels (H1→H2→H3) for proper hierarchy.",
                    fix_complexity="medium",
                    estimated_fix_time=5,
                    test_method="automated"
                ))
        
        # Check for empty headings
        for i, heading in enumerate(headings):
            text_content = heading.get_text(strip=True)
            if not text_content:
                issues.append(AccessibilityIssue(
                    issue_id=f"empty_heading_{i}",
                    category=AccessibilityCategory.HEADINGS_STRUCTURE,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="2.4.6",
                    title="Empty heading element",
                    description=f"H{heading.name[1]} element contains no text content.",
                    element_selector=self._generate_selector(heading),
                    element_html=str(heading)[:200],
                    xpath=self._generate_xpath(heading, soup),
                    page_location=self._get_page_location(heading),
                    fix_suggestion="Add descriptive text to the heading or remove if unnecessary.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_keyboard_navigation(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check keyboard navigation accessibility."""
        issues = []
        
        # Check for skip links
        skip_links = soup.find_all('a', href=re.compile(r'^#'))
        main_skip_link = None
        for link in skip_links:
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in ['skip to main', 'skip to content', 'skip navigation']):
                main_skip_link = link
                break
        
        if not main_skip_link:
            issues.append(AccessibilityIssue(
                issue_id="missing_skip_link",
                category=AccessibilityCategory.KEYBOARD_NAVIGATION,
                severity=IssueSeverity.MEDIUM,
                wcag_level=WCAGLevel.A,
                wcag_criteria="2.4.1",
                title="Missing skip to main content link",
                description="Page lacks a skip link for keyboard users to bypass navigation.",
                element_selector="body",
                element_html="<body>",
                xpath="//body",
                page_location="header",
                fix_suggestion="Add a 'Skip to main content' link at the beginning of the page.",
                fix_complexity="medium",
                estimated_fix_time=15,
                test_method="automated"
            ))
        
        # Check focusable elements without visible focus indicators
        focusable_elements = soup.find_all(['a', 'button', 'input', 'select', 'textarea', 'details'])
        for i, element in enumerate(focusable_elements):
            # Check for custom focus styles that might remove default focus
            style = element.get('style', '')
            if 'outline: none' in style or 'outline:none' in style:
                issues.append(AccessibilityIssue(
                    issue_id=f"removed_focus_outline_{i}",
                    category=AccessibilityCategory.KEYBOARD_NAVIGATION,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="2.4.7",
                    title="Focus outline removed",
                    description="Element has 'outline: none' which removes keyboard focus indicator.",
                    element_selector=self._generate_selector(element),
                    element_html=str(element)[:200],
                    xpath=self._generate_xpath(element, soup),
                    page_location=self._get_page_location(element),
                    fix_suggestion="Provide custom focus styles or remove 'outline: none'.",
                    fix_complexity="medium",
                    estimated_fix_time=5,
                    test_method="automated"
                ))
        
        # Check for elements with tabindex > 0
        high_tabindex_elements = soup.find_all(attrs={'tabindex': re.compile(r'^[1-9]\d*$')})
        for i, element in enumerate(high_tabindex_elements):
            tabindex = element.get('tabindex')
            issues.append(AccessibilityIssue(
                issue_id=f"positive_tabindex_{i}",
                category=AccessibilityCategory.KEYBOARD_NAVIGATION,
                severity=IssueSeverity.MEDIUM,
                wcag_level=WCAGLevel.A,
                wcag_criteria="2.4.3",
                title="Positive tabindex disrupts tab order",
                description=f"Element has tabindex='{tabindex}' which can confuse keyboard navigation.",
                element_selector=self._generate_selector(element),
                element_html=str(element)[:200],
                xpath=self._generate_xpath(element, soup),
                page_location=self._get_page_location(element),
                fix_suggestion="Use tabindex='0' or '-1', or rely on natural tab order.",
                fix_complexity="easy",
                estimated_fix_time=2,
                test_method="automated"
            ))
        
        return issues
    
    async def _check_links_accessibility(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check link accessibility and usability."""
        issues = []
        
        links = soup.find_all('a')
        link_texts = []
        
        for i, link in enumerate(links):
            href = link.get('href')
            text_content = link.get_text(strip=True)
            aria_label = link.get('aria-label')
            title = link.get('title')
            
            # Missing href
            if not href:
                issues.append(AccessibilityIssue(
                    issue_id=f"link_missing_href_{i}",
                    category=AccessibilityCategory.LINKS_NAVIGATION,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="2.1.1",
                    title="Link missing href attribute",
                    description="Link element lacks href attribute, making it non-functional with keyboard.",
                    element_selector=self._generate_selector(link),
                    element_html=str(link)[:200],
                    xpath=self._generate_xpath(link, soup),
                    page_location=self._get_page_location(link),
                    fix_suggestion="Add href attribute or use button element for interactive behavior.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
            
            # Empty link text
            accessible_name = aria_label or text_content or title
            if not accessible_name:
                issues.append(AccessibilityIssue(
                    issue_id=f"link_empty_text_{i}",
                    category=AccessibilityCategory.LINKS_NAVIGATION,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="2.4.4",
                    title="Link has no accessible name",
                    description="Link lacks text content, aria-label, or title for screen readers.",
                    element_selector=self._generate_selector(link),
                    element_html=str(link)[:200],
                    xpath=self._generate_xpath(link, soup),
                    page_location=self._get_page_location(link),
                    fix_suggestion="Add descriptive text content or aria-label attribute.",
                    fix_complexity="easy",
                    estimated_fix_time=3,
                    test_method="automated"
                ))
            
            # Vague link text
            elif text_content.lower() in ['click here', 'read more', 'more', 'here', 'link']:
                issues.append(AccessibilityIssue(
                    issue_id=f"link_vague_text_{i}",
                    category=AccessibilityCategory.LINKS_NAVIGATION,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="2.4.4",
                    title="Link text is not descriptive",
                    description=f"Link text '{text_content}' doesn't describe the link's purpose.",
                    element_selector=self._generate_selector(link),
                    element_html=str(link)[:200],
                    xpath=self._generate_xpath(link, soup),
                    page_location=self._get_page_location(link),
                    fix_suggestion="Use descriptive text that explains where the link goes or what it does.",
                    fix_complexity="medium",
                    estimated_fix_time=5,
                    test_method="automated"
                ))
            
            # Track duplicate link texts for context issues
            if accessible_name:
                link_texts.append((accessible_name, href, i))
        
        # Check for duplicate link texts with different destinations
        text_groups = {}
        for text, href, index in link_texts:
            if text not in text_groups:
                text_groups[text] = []
            text_groups[text].append((href, index))
        
        for text, links_info in text_groups.items():
            if len(links_info) > 1:
                unique_hrefs = set(href for href, _ in links_info)
                if len(unique_hrefs) > 1:
                    issues.append(AccessibilityIssue(
                        issue_id=f"duplicate_link_text_{text[:20]}",
                        category=AccessibilityCategory.LINKS_NAVIGATION,
                        severity=IssueSeverity.MEDIUM,
                        wcag_level=WCAGLevel.AA,
                        wcag_criteria="2.4.4",
                        title="Identical link text for different destinations",
                        description=f"Multiple links with text '{text}' lead to different pages.",
                        element_selector="a",
                        element_html=f"Multiple links with text: {text}",
                        xpath="//a",
                        page_location="various",
                        fix_suggestion="Make link text unique or add aria-label to distinguish purpose.",
                        fix_complexity="medium",
                        estimated_fix_time=10,
                        test_method="automated"
                    ))
        
        return issues
    
    async def _check_color_contrast(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check color contrast compliance (basic checks only)."""
        issues = []
        
        # This is a simplified color contrast check
        # In practice, you'd need to compute actual contrast ratios from CSS
        
        # Check for inline styles with potential contrast issues
        elements_with_style = soup.find_all(attrs={'style': True})
        
        for i, element in enumerate(elements_with_style):
            style = element.get('style', '')
            
            # Basic check for light text on light background patterns
            light_text_patterns = ['color:#fff', 'color:#ffffff', 'color:white', 'color: white']
            light_bg_patterns = ['background:#fff', 'background:#ffffff', 'background:white', 'background: white']
            
            has_light_text = any(pattern in style.lower() for pattern in light_text_patterns)
            has_light_bg = any(pattern in style.lower() for pattern in light_bg_patterns)
            
            if has_light_text and has_light_bg:
                issues.append(AccessibilityIssue(
                    issue_id=f"potential_contrast_issue_{i}",
                    category=AccessibilityCategory.COLOR_CONTRAST,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="1.4.3",
                    title="Potential color contrast issue",
                    description="Element may have insufficient color contrast (manual verification needed).",
                    element_selector=self._generate_selector(element),
                    element_html=str(element)[:200],
                    xpath=self._generate_xpath(element, soup),
                    page_location=self._get_page_location(element),
                    fix_suggestion="Verify color contrast meets WCAG AA ratio (4.5:1 for normal text).",
                    fix_complexity="medium",
                    estimated_fix_time=10,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_focus_management(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check focus management and keyboard interaction."""
        issues = []
        
        # Check for JavaScript that might trap focus
        scripts = soup.find_all('script')
        for i, script in enumerate(scripts):
            script_content = script.get_text()
            if script_content and 'focus()' in script_content:
                # This is a basic check - would need more sophisticated analysis
                issues.append(AccessibilityIssue(
                    issue_id=f"focus_management_review_{i}",
                    category=AccessibilityCategory.FOCUS_MANAGEMENT,
                    severity=IssueSeverity.INFO,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="2.4.3",
                    title="Script modifies focus - manual review needed",
                    description="JavaScript contains focus() calls - verify proper focus management.",
                    element_selector="script",
                    element_html="<script>",
                    xpath=f"//script[{i+1}]",
                    page_location="head",
                    fix_suggestion="Ensure focus changes are logical and users aren't trapped.",
                    fix_complexity="complex",
                    estimated_fix_time=30,
                    test_method="automated"
                ))
        
        # Check for modal dialogs without proper focus management attributes
        modal_indicators = soup.find_all(attrs={'role': 'dialog'})
        modal_indicators.extend(soup.find_all(class_=re.compile(r'modal|dialog|popup')))
        
        for i, modal in enumerate(modal_indicators):
            aria_labelledby = modal.get('aria-labelledby')
            aria_describedby = modal.get('aria-describedby')
            
            if not aria_labelledby:
                issues.append(AccessibilityIssue(
                    issue_id=f"modal_missing_label_{i}",
                    category=AccessibilityCategory.FOCUS_MANAGEMENT,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="4.1.2",
                    title="Modal dialog missing accessible name",
                    description="Modal/dialog lacks aria-labelledby for screen reader users.",
                    element_selector=self._generate_selector(modal),
                    element_html=str(modal)[:200],
                    xpath=self._generate_xpath(modal, soup),
                    page_location=self._get_page_location(modal),
                    fix_suggestion="Add aria-labelledby pointing to modal title or aria-label.",
                    fix_complexity="medium",
                    estimated_fix_time=5,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_screen_reader_compatibility(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check screen reader compatibility."""
        issues = []
        
        # Check for missing language attribute
        html_element = soup.find('html')
        if html_element and not html_element.get('lang'):
            issues.append(AccessibilityIssue(
                issue_id="missing_lang_attribute",
                category=AccessibilityCategory.SCREEN_READER,
                severity=IssueSeverity.HIGH,
                wcag_level=WCAGLevel.A,
                wcag_criteria="3.1.1",
                title="Page missing language declaration",
                description="HTML element lacks lang attribute for screen reader pronunciation.",
                element_selector="html",
                element_html="<html>",
                xpath="//html",
                page_location="document",
                fix_suggestion="Add lang='en' (or appropriate language code) to html element.",
                fix_complexity="easy",
                estimated_fix_time=1,
                test_method="automated"
            ))
        
        # Check for iframes without titles
        iframes = soup.find_all('iframe')
        for i, iframe in enumerate(iframes):
            title = iframe.get('title')
            aria_label = iframe.get('aria-label')
            
            if not title and not aria_label:
                issues.append(AccessibilityIssue(
                    issue_id=f"iframe_missing_title_{i}",
                    category=AccessibilityCategory.SCREEN_READER,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="4.1.2",
                    title="Iframe missing title",
                    description="Iframe lacks title or aria-label to describe its content.",
                    element_selector=self._generate_selector(iframe),
                    element_html=str(iframe)[:200],
                    xpath=self._generate_xpath(iframe, soup),
                    page_location=self._get_page_location(iframe),
                    fix_suggestion="Add descriptive title attribute to iframe element.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_layout_shift_prevention(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check for layout shift prevention measures."""
        issues = []
        
        # Check images without dimensions
        images = soup.find_all('img')
        for i, img in enumerate(images):
            width = img.get('width')
            height = img.get('height')
            style = img.get('style', '')
            
            # Check if dimensions are specified
            has_dimensions = bool(width and height) or ('width:' in style and 'height:' in style)
            
            if not has_dimensions:
                issues.append(AccessibilityIssue(
                    issue_id=f"img_no_dimensions_{i}",
                    category=AccessibilityCategory.LAYOUT_SHIFT,
                    severity=IssueSeverity.MEDIUM,
                    wcag_level=WCAGLevel.AA,
                    wcag_criteria="2.4.7",
                    title="Image without dimensions may cause layout shift",
                    description="Image lacks width/height attributes which can cause cumulative layout shift.",
                    element_selector=self._generate_selector(img),
                    element_html=str(img)[:200],
                    xpath=self._generate_xpath(img, soup),
                    page_location=self._get_page_location(img),
                    fix_suggestion="Add width and height attributes or CSS dimensions to prevent layout shift.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _check_motion_accessibility(self, soup: BeautifulSoup, page_url: str) -> List[AccessibilityIssue]:
        """Check for motion and animation accessibility."""
        issues = []
        
        # Check for CSS animations without prefers-reduced-motion
        style_elements = soup.find_all('style')
        for i, style in enumerate(style_elements):
            style_content = style.get_text()
            if style_content and ('animation:' in style_content or '@keyframes' in style_content):
                if 'prefers-reduced-motion' not in style_content:
                    issues.append(AccessibilityIssue(
                        issue_id=f"animation_no_reduced_motion_{i}",
                        category=AccessibilityCategory.MOTION_ANIMATION,
                        severity=IssueSeverity.MEDIUM,
                        wcag_level=WCAGLevel.AAA,
                        wcag_criteria="2.3.3",
                        title="Animation without reduced motion support",
                        description="CSS animations don't respect prefers-reduced-motion preference.",
                        element_selector="style",
                        element_html="<style>",
                        xpath=f"//style[{i+1}]",
                        page_location="head",
                        fix_suggestion="Add @media (prefers-reduced-motion: reduce) to disable animations for sensitive users.",
                        fix_complexity="medium",
                        estimated_fix_time=10,
                        test_method="automated"
                    ))
        
        # Check for autoplay videos
        videos = soup.find_all(['video', 'audio'])
        for i, media in enumerate(videos):
            if media.get('autoplay') is not None:
                issues.append(AccessibilityIssue(
                    issue_id=f"autoplay_media_{i}",
                    category=AccessibilityCategory.MOTION_ANIMATION,
                    severity=IssueSeverity.HIGH,
                    wcag_level=WCAGLevel.A,
                    wcag_criteria="1.4.2",
                    title="Autoplay media may be disruptive",
                    description=f"{media.name.title()} element has autoplay which can disorient users.",
                    element_selector=self._generate_selector(media),
                    element_html=str(media)[:200],
                    xpath=self._generate_xpath(media, soup),
                    page_location=self._get_page_location(media),
                    fix_suggestion="Remove autoplay or add user controls to pause/stop media.",
                    fix_complexity="easy",
                    estimated_fix_time=2,
                    test_method="automated"
                ))
        
        return issues
    
    async def _get_lighthouse_accessibility_score(self, page_url: str) -> Optional[int]:
        """Get Lighthouse accessibility score from PageSpeed Insights."""
        if not self.settings.pagespeed_api_key:
            return None
        
        psi_url = "https://www.googleapis.com/pagespeedonline/runPagespeed/v5"
        params = {
            "url": page_url,
            "key": self.settings.pagespeed_api_key,
            "category": "accessibility",
            "strategy": "mobile"
        }
        
        try:
            async with self.session.get(psi_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    score = data.get("lighthouseResult", {}).get("categories", {}).get("accessibility", {}).get("score")
                    return int(score * 100) if score is not None else None
        except Exception as e:
            logger.warning(f"Failed to get Lighthouse accessibility score: {e}")
        
        return None
    
    def _is_decorative_image(self, img) -> bool:
        """Determine if an image is decorative based on context."""
        # Simple heuristic - in practice this would be more sophisticated
        src = img.get('src', '').lower()
        classes = ' '.join(img.get('class', [])).lower()
        
        decorative_indicators = [
            'decoration', 'ornament', 'spacer', 'divider',
            'icon', 'bullet', 'arrow', 'background'
        ]
        
        return any(indicator in src or indicator in classes for indicator in decorative_indicators)
    
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
        # Simplified XPath generation
        try:
            if element.get('id'):
                return f"//{element.name}[@id='{element['id']}']"
            else:
                return f"//{element.name}"
        except:
            return f"//{element.name}"
    
    def _get_page_location(self, element) -> str:
        """Determine page location of element."""
        # Walk up the DOM to find semantic location
        current = element
        while current and hasattr(current, 'parent'):
            if hasattr(current, 'name'):
                if current.name in ['header', 'nav', 'main', 'footer', 'aside']:
                    return current.name
            current = current.parent
        
        return "main"
    
    def _generate_audit_result(
        self,
        page_url: str,
        issues: List[AccessibilityIssue],
        lighthouse_score: Optional[int]
    ) -> AccessibilityAuditResult:
        """Generate comprehensive audit result."""
        # Count issues by severity
        critical_issues = len([i for i in issues if i.severity == IssueSeverity.CRITICAL])
        high_issues = len([i for i in issues if i.severity == IssueSeverity.HIGH])
        medium_issues = len([i for i in issues if i.severity == IssueSeverity.MEDIUM])
        low_issues = len([i for i in issues if i.severity == IssueSeverity.LOW])
        
        # Count by category
        issues_by_category = {}
        for category in AccessibilityCategory:
            count = len([i for i in issues if i.category == category])
            if count > 0:
                issues_by_category[category] = count
        
        # Count by fix complexity
        easy_fixes = len([i for i in issues if i.fix_complexity == "easy"])
        medium_fixes = len([i for i in issues if i.fix_complexity == "medium"])
        complex_fixes = len([i for i in issues if i.fix_complexity == "complex"])
        
        # Calculate estimated fix time
        total_fix_time = sum(issue.estimated_fix_time for issue in issues)
        estimated_fix_time_hours = total_fix_time / 60.0
        
        # Determine WCAG AA compliance
        blocking_issues = [i for i in issues if i.is_blocking and i.wcag_level in [WCAGLevel.A, WCAGLevel.AA]]
        wcag_aa_compliant = len(blocking_issues) == 0
        
        # Generate recommendations
        priority_fixes = []
        quick_wins = []
        
        # Priority fixes (critical and high severity)
        critical_and_high = [i for i in issues if i.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]]
        if critical_and_high:
            priority_fixes.append(f"Fix {len(critical_and_high)} critical/high severity issues immediately")
        
        # Quick wins (easy fixes with medium+ impact)
        quick_win_issues = [i for i in issues if i.fix_complexity == "easy" and i.severity != IssueSeverity.LOW]
        if quick_win_issues:
            quick_wins.append(f"Complete {len(quick_win_issues)} easy fixes for immediate impact")
        
        # Category-specific recommendations
        if AccessibilityCategory.IMAGES_MEDIA in issues_by_category:
            quick_wins.append("Add missing alt text to images (high impact, easy fix)")
        
        if AccessibilityCategory.FORMS_INPUTS in issues_by_category:
            priority_fixes.append("Fix form labeling issues to ensure forms are usable")
        
        if AccessibilityCategory.KEYBOARD_NAVIGATION in issues_by_category:
            priority_fixes.append("Address keyboard navigation issues for full accessibility")
        
        return AccessibilityAuditResult(
            page_url=page_url,
            audit_timestamp=datetime.now(timezone.utc),
            wcag_target_level=self.target_level,
            total_issues=len(issues),
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            issues_by_category=issues_by_category,
            wcag_aa_compliant=wcag_aa_compliant,
            lighthouse_accessibility_score=lighthouse_score,
            blocking_issues_count=len(blocking_issues),
            estimated_fix_time_hours=estimated_fix_time_hours,
            easy_fixes=easy_fixes,
            medium_fixes=medium_fixes,
            complex_fixes=complex_fixes,
            issues=issues,
            priority_fixes=priority_fixes,
            quick_wins=quick_wins
        )
    
    def export_audit_results(
        self,
        result: AccessibilityAuditResult,
        output_path: Path,
        format: str = "json"
    ) -> None:
        """Export accessibility audit results to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        data = {
            "page_url": result.page_url,
            "audit_timestamp": result.audit_timestamp.isoformat(),
            "wcag_target_level": result.wcag_target_level.value,
            "summary": {
                "total_issues": result.total_issues,
                "critical_issues": result.critical_issues,
                "high_issues": result.high_issues,
                "medium_issues": result.medium_issues,
                "low_issues": result.low_issues,
                "wcag_aa_compliant": result.wcag_aa_compliant,
                "lighthouse_accessibility_score": result.lighthouse_accessibility_score,
                "compliance_percentage": result.compliance_percentage,
                "estimated_fix_time_hours": result.estimated_fix_time_hours
            },
            "issues_by_category": {cat.value: count for cat, count in result.issues_by_category.items()},
            "fix_breakdown": {
                "easy_fixes": result.easy_fixes,
                "medium_fixes": result.medium_fixes,
                "complex_fixes": result.complex_fixes
            },
            "recommendations": {
                "priority_fixes": result.priority_fixes,
                "quick_wins": result.quick_wins
            },
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "category": issue.category.value,
                    "severity": issue.severity.value,
                    "wcag_level": issue.wcag_level.value,
                    "wcag_criteria": issue.wcag_criteria,
                    "title": issue.title,
                    "description": issue.description,
                    "element_selector": issue.element_selector,
                    "fix_suggestion": issue.fix_suggestion,
                    "fix_complexity": issue.fix_complexity,
                    "estimated_fix_time": issue.estimated_fix_time
                }
                for issue in result.issues
            ]
        }
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Accessibility audit results exported to {output_path}")
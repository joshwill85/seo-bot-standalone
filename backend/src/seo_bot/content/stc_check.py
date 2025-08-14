"""Search Task Completion (STC) system for validating and optimizing task completers."""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import json
from urllib.parse import urljoin, urlparse
import asyncio
import aiohttp
from bs4 import BeautifulSoup, Comment

from ..config import ContentQualityConfig
from ..models import Page, Project


logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of task completion elements."""
    CALCULATOR = "calculator"
    CHECKLIST = "checklist"
    COMPARISON_TABLE = "comparison_table"
    DOWNLOAD = "download"
    FORM = "form"
    INTERACTIVE_TOOL = "interactive_tool"
    QUIZ = "quiz"
    SURVEY = "survey"
    TEMPLATE = "template"
    WORKSHEET = "worksheet"


class CompletionTrigger(Enum):
    """Events that trigger task completion."""
    BUTTON_CLICK = "button_click"
    FORM_SUBMIT = "form_submit"
    DOWNLOAD_START = "download_start"
    CALCULATION_COMPLETE = "calculation_complete"
    CHECKLIST_COMPLETE = "checklist_complete"
    TIME_ON_PAGE = "time_on_page"
    SCROLL_DEPTH = "scroll_depth"


class TaskCompleterValidation(Enum):
    """Validation status for task completers."""
    VALID = "valid"
    MISSING_TRIGGER = "missing_trigger"
    POOR_UX = "poor_ux"
    NOT_FUNCTIONAL = "not_functional"
    ACCESSIBILITY_ISSUES = "accessibility_issues"
    MISSING_ANALYTICS = "missing_analytics"


@dataclass
class TaskCompleter:
    """Represents a task completion element on a page."""
    
    element_id: str
    task_type: TaskType
    title: str
    description: str
    completion_trigger: CompletionTrigger
    
    # Element location and structure
    html_element: str  # The actual HTML element
    xpath: str  # XPath to the element
    css_selector: str  # CSS selector for the element
    position_on_page: str  # "above-fold", "below-fold", "sidebar"
    
    # Functionality validation
    is_functional: bool = True
    has_analytics_tracking: bool = False
    analytics_events: List[str] = field(default_factory=list)
    
    # UX and accessibility
    is_accessible: bool = True
    accessibility_issues: List[str] = field(default_factory=list)
    mobile_friendly: bool = True
    
    # Performance metrics
    load_time_ms: Optional[int] = None
    interaction_delay_ms: Optional[int] = None
    
    # Engagement metrics (when available)
    completion_rate: Optional[float] = None  # 0-1
    avg_time_to_complete: Optional[int] = None  # seconds
    bounce_rate_impact: Optional[float] = None  # Change in bounce rate
    
    # Validation results
    validation_status: TaskCompleterValidation = TaskCompleterValidation.VALID
    validation_issues: List[str] = field(default_factory=list)
    last_validated: Optional[datetime] = None
    
    @property
    def is_valid(self) -> bool:
        """Check if task completer is valid and functional."""
        return (
            self.validation_status == TaskCompleterValidation.VALID and
            self.is_functional and
            self.is_accessible
        )
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score based on completion metrics."""
        if not self.completion_rate:
            return 0.0
        
        base_score = self.completion_rate
        
        # Bonus for quick completion (under 2 minutes)
        if self.avg_time_to_complete and self.avg_time_to_complete < 120:
            base_score += 0.1
        
        # Bonus for positive bounce rate impact
        if self.bounce_rate_impact and self.bounce_rate_impact < 0:
            base_score += abs(self.bounce_rate_impact) * 0.5
        
        return min(base_score, 1.0)


@dataclass
class TaskCompletionAuditResult:
    """Results from a task completion audit."""
    
    page_url: str
    audit_timestamp: datetime
    
    # Task completer inventory
    total_task_completers: int
    valid_task_completers: int
    task_completers_by_type: Dict[TaskType, int]
    
    # Quality metrics
    meets_minimum_requirement: bool
    meets_money_page_requirement: bool  # ≥2 task completers
    avg_completion_rate: float
    total_engagement_score: float
    
    # Issues found
    validation_issues: List[str]
    accessibility_issues: List[str]
    functionality_issues: List[str]
    analytics_issues: List[str]
    
    # Recommendations
    recommendations: List[str]
    priority_fixes: List[str]
    
    # Detailed task completer data
    task_completers: List[TaskCompleter]


class SearchTaskCompletionChecker:
    """Validates and optimizes search task completion elements."""
    
    def __init__(self, content_config: Optional[ContentQualityConfig] = None):
        """Initialize the task completion checker."""
        self.content_config = content_config or ContentQualityConfig()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Task completer patterns and selectors
        self.task_completer_patterns = {
            TaskType.CALCULATOR: {
                "selectors": [
                    "form[data-calculator]",
                    ".calculator",
                    "#calculator",
                    "[data-task='calculator']",
                    "form:has(input[type='number'])",
                    ".calc-form"
                ],
                "keywords": ["calculator", "calculate", "compute", "estimate"]
            },
            TaskType.CHECKLIST: {
                "selectors": [
                    ".checklist",
                    "ul.task-list",
                    "[data-task='checklist']",
                    "form:has(input[type='checkbox'])",
                    ".todo-list"
                ],
                "keywords": ["checklist", "todo", "task list", "steps"]
            },
            TaskType.COMPARISON_TABLE: {
                "selectors": [
                    "table.comparison",
                    ".comparison-table",
                    "[data-task='comparison']",
                    "table:has(.vs)",
                    ".compare-table"
                ],
                "keywords": ["comparison", "compare", "vs", "versus"]
            },
            TaskType.DOWNLOAD: {
                "selectors": [
                    "a[download]",
                    ".download-button",
                    "[data-task='download']",
                    "a[href$='.pdf']",
                    "a[href$='.doc']",
                    "a[href$='.xls']"
                ],
                "keywords": ["download", "get template", "free download"]
            },
            TaskType.FORM: {
                "selectors": [
                    "form.contact",
                    "form.newsletter",
                    "[data-task='form']",
                    "form:has(input[type='email'])",
                    ".signup-form"
                ],
                "keywords": ["contact", "signup", "subscribe", "get started"]
            },
            TaskType.QUIZ: {
                "selectors": [
                    ".quiz",
                    "[data-task='quiz']",
                    "form.quiz",
                    ".questionnaire"
                ],
                "keywords": ["quiz", "test", "assessment", "questionnaire"]
            }
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def audit_page_task_completion(
        self,
        page_url: str,
        is_money_page: bool = False,
        user_agent: str = None
    ) -> TaskCompletionAuditResult:
        """Audit task completion elements on a page."""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        logger.info(f"Auditing task completion for: {page_url}")
        
        # Fetch page content
        html_content = await self._fetch_page_content(page_url, user_agent)
        
        # Parse HTML and detect task completers
        soup = BeautifulSoup(html_content, 'html.parser')
        task_completers = await self._detect_task_completers(soup, page_url)
        
        # Validate each task completer
        for completer in task_completers:
            await self._validate_task_completer(completer, soup)
        
        # Calculate metrics and generate audit result
        return self._generate_audit_result(
            page_url=page_url,
            task_completers=task_completers,
            is_money_page=is_money_page
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
                
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    raise RuntimeError(f"Expected HTML content, got: {content_type}")
                
                return await response.text()
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {url}: {e}")
            raise RuntimeError(f"Network error: {e}")
    
    async def _detect_task_completers(self, soup: BeautifulSoup, base_url: str) -> List[TaskCompleter]:
        """Detect task completion elements in HTML."""
        task_completers = []
        
        for task_type, patterns in self.task_completer_patterns.items():
            # Find elements by CSS selectors
            for selector in patterns["selectors"]:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        completer = await self._create_task_completer(
                            element=element,
                            task_type=task_type,
                            base_url=base_url,
                            soup=soup
                        )
                        if completer:
                            task_completers.append(completer)
                except Exception as e:
                    logger.warning(f"Error processing selector {selector}: {e}")
            
            # Find elements by keyword analysis
            keyword_completers = await self._detect_by_keywords(
                soup=soup,
                task_type=task_type,
                keywords=patterns["keywords"],
                base_url=base_url
            )
            task_completers.extend(keyword_completers)
        
        # Remove duplicates based on xpath
        unique_completers = {}
        for completer in task_completers:
            if completer.xpath not in unique_completers:
                unique_completers[completer.xpath] = completer
        
        return list(unique_completers.values())
    
    async def _create_task_completer(
        self,
        element,
        task_type: TaskType,
        base_url: str,
        soup: BeautifulSoup
    ) -> Optional[TaskCompleter]:
        """Create TaskCompleter from HTML element."""
        try:
            # Generate unique ID
            element_id = element.get('id') or f"{task_type.value}_{hash(str(element))}"
            
            # Extract title and description
            title = self._extract_element_title(element)
            description = self._extract_element_description(element)
            
            # Generate XPath and CSS selector
            xpath = self._generate_xpath(element, soup)
            css_selector = self._generate_css_selector(element)
            
            # Determine completion trigger
            completion_trigger = self._determine_completion_trigger(element, task_type)
            
            # Determine position on page
            position = self._determine_element_position(element, soup)
            
            # Check for analytics tracking
            has_analytics, analytics_events = self._check_analytics_tracking(element)
            
            return TaskCompleter(
                element_id=element_id,
                task_type=task_type,
                title=title,
                description=description,
                completion_trigger=completion_trigger,
                html_element=str(element)[:1000],  # Limit size
                xpath=xpath,
                css_selector=css_selector,
                position_on_page=position,
                has_analytics_tracking=has_analytics,
                analytics_events=analytics_events,
                last_validated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error creating task completer: {e}")
            return None
    
    async def _detect_by_keywords(
        self,
        soup: BeautifulSoup,
        task_type: TaskType,
        keywords: List[str],
        base_url: str
    ) -> List[TaskCompleter]:
        """Detect task completers by keyword analysis."""
        completers = []
        
        # Search for keywords in text content and attributes
        for keyword in keywords:
            # Find elements with keyword in text or attributes
            pattern = re.compile(keyword, re.IGNORECASE)
            
            # Search in headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if pattern.search(heading.get_text()):
                    # Look for interactive elements near this heading
                    interactive_elements = self._find_nearby_interactive_elements(heading)
                    for element in interactive_elements:
                        completer = await self._create_task_completer(
                            element=element,
                            task_type=task_type,
                            base_url=base_url,
                            soup=soup
                        )
                        if completer:
                            completers.append(completer)
            
            # Search in buttons and links
            for element in soup.find_all(['button', 'a', 'input']):
                text = element.get_text() + ' ' + ' '.join(element.get(attr, '') for attr in ['title', 'alt', 'placeholder'])
                if pattern.search(text):
                    completer = await self._create_task_completer(
                        element=element,
                        task_type=task_type,
                        base_url=base_url,
                        soup=soup
                    )
                    if completer:
                        completers.append(completer)
        
        return completers
    
    def _find_nearby_interactive_elements(self, heading_element) -> List:
        """Find interactive elements near a heading."""
        interactive_elements = []
        
        # Look in the next few siblings
        current = heading_element
        for _ in range(10):  # Look at next 10 elements
            current = current.find_next_sibling()
            if not current:
                break
            
            # Check if this element or its children are interactive
            if current.name in ['form', 'button', 'input', 'select', 'textarea']:
                interactive_elements.append(current)
            
            # Check children
            for child in current.find_all(['form', 'button', 'input', 'select', 'textarea']):
                interactive_elements.append(child)
            
            # Stop if we hit another heading
            if current.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
        
        return interactive_elements
    
    def _extract_element_title(self, element) -> str:
        """Extract title from element."""
        # Try various methods to get title
        title = (
            element.get('title') or
            element.get('data-title') or
            element.get('aria-label') or
            element.get('placeholder')
        )
        
        if not title:
            # Look for text content
            text = element.get_text(strip=True)
            if text:
                title = text[:100]  # Limit length
        
        if not title:
            # Look for nearby heading
            heading = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if heading:
                title = heading.get_text(strip=True)[:100]
        
        return title or "Untitled Task Completer"
    
    def _extract_element_description(self, element) -> str:
        """Extract description from element."""
        description = (
            element.get('data-description') or
            element.get('aria-describedby')
        )
        
        if not description:
            # Look for nearby descriptive text
            parent = element.parent
            if parent:
                description = parent.get_text(strip=True)[:200]
        
        return description or ""
    
    def _generate_xpath(self, element, soup: BeautifulSoup) -> str:
        """Generate XPath for element."""
        try:
            # Simple XPath generation
            path_parts = []
            current = element
            
            while current and current.name:
                tag = current.name
                
                # Count siblings with same tag
                siblings = [s for s in current.parent.children if hasattr(s, 'name') and s.name == tag]
                if len(siblings) > 1:
                    index = siblings.index(current) + 1
                    path_parts.append(f"{tag}[{index}]")
                else:
                    path_parts.append(tag)
                
                current = current.parent
                if not current or current.name == '[document]':
                    break
            
            path_parts.reverse()
            return "//" + "/".join(path_parts)
            
        except Exception:
            return f"//*[@id='{element.get('id', 'unknown')}']"
    
    def _generate_css_selector(self, element) -> str:
        """Generate CSS selector for element."""
        try:
            if element.get('id'):
                return f"#{element['id']}"
            
            if element.get('class'):
                classes = ' '.join(element['class'])
                return f"{element.name}.{classes.replace(' ', '.')}"
            
            return element.name
            
        except Exception:
            return element.name or "unknown"
    
    def _determine_completion_trigger(self, element, task_type: TaskType) -> CompletionTrigger:
        """Determine what triggers task completion."""
        element_type = element.name.lower()
        
        if element_type == 'form' or element.find('form'):
            return CompletionTrigger.FORM_SUBMIT
        elif element_type in ['button', 'input'] and element.get('type') == 'submit':
            return CompletionTrigger.FORM_SUBMIT
        elif element.get('download') or 'download' in str(element.get('href', '')):
            return CompletionTrigger.DOWNLOAD_START
        elif task_type == TaskType.CALCULATOR:
            return CompletionTrigger.CALCULATION_COMPLETE
        elif task_type == TaskType.CHECKLIST:
            return CompletionTrigger.CHECKLIST_COMPLETE
        else:
            return CompletionTrigger.BUTTON_CLICK
    
    def _determine_element_position(self, element, soup: BeautifulSoup) -> str:
        """Determine if element is above or below the fold."""
        # Simple heuristic: check if element is in first half of body content
        body = soup.find('body')
        if not body:
            return "unknown"
        
        all_elements = body.find_all()
        if not all_elements:
            return "above-fold"
        
        element_index = -1
        for i, el in enumerate(all_elements):
            if el == element:
                element_index = i
                break
        
        if element_index == -1:
            return "unknown"
        
        # If in first 30% of elements, consider above fold
        position_ratio = element_index / len(all_elements)
        if position_ratio < 0.3:
            return "above-fold"
        elif position_ratio < 0.7:
            return "mid-page"
        else:
            return "below-fold"
    
    def _check_analytics_tracking(self, element) -> Tuple[bool, List[str]]:
        """Check if element has analytics tracking."""
        analytics_events = []
        
        # Check for common analytics attributes
        analytics_attrs = [
            'data-ga-event',
            'data-gtm-event',
            'data-analytics',
            'data-track',
            'onclick',
            'data-fb-pixel',
            'data-mixpanel'
        ]
        
        for attr in analytics_attrs:
            if element.get(attr):
                analytics_events.append(f"{attr}: {element[attr]}")
        
        # Check for Google Analytics onclick patterns
        onclick = element.get('onclick', '')
        if 'gtag(' in onclick or 'ga(' in onclick or '_gaq.push' in onclick:
            analytics_events.append(f"GA tracking in onclick")
        
        has_analytics = len(analytics_events) > 0
        return has_analytics, analytics_events
    
    async def _validate_task_completer(self, completer: TaskCompleter, soup: BeautifulSoup) -> None:
        """Validate a task completer for functionality and accessibility."""
        issues = []
        
        # Parse the element from HTML string
        element_soup = BeautifulSoup(completer.html_element, 'html.parser')
        element = element_soup.find()
        
        if not element:
            completer.validation_status = TaskCompleterValidation.NOT_FUNCTIONAL
            completer.validation_issues.append("Element not found in HTML")
            return
        
        # Check functionality
        if not self._validate_functionality(element, completer.task_type):
            completer.is_functional = False
            issues.append("Element lacks required functionality")
        
        # Check accessibility
        accessibility_issues = self._validate_accessibility(element)
        if accessibility_issues:
            completer.is_accessible = False
            completer.accessibility_issues.extend(accessibility_issues)
            issues.extend(accessibility_issues)
        
        # Check analytics tracking
        if not completer.has_analytics_tracking:
            issues.append("Missing analytics tracking")
        
        # Check mobile friendliness
        if not self._validate_mobile_friendly(element):
            completer.mobile_friendly = False
            issues.append("Not mobile-friendly")
        
        # Determine overall validation status
        if not completer.is_functional:
            completer.validation_status = TaskCompleterValidation.NOT_FUNCTIONAL
        elif not completer.is_accessible:
            completer.validation_status = TaskCompleterValidation.ACCESSIBILITY_ISSUES
        elif not completer.has_analytics_tracking:
            completer.validation_status = TaskCompleterValidation.MISSING_ANALYTICS
        elif issues:
            completer.validation_status = TaskCompleterValidation.POOR_UX
        else:
            completer.validation_status = TaskCompleterValidation.VALID
        
        completer.validation_issues = issues
    
    def _validate_functionality(self, element, task_type: TaskType) -> bool:
        """Validate element functionality based on task type."""
        if task_type == TaskType.FORM:
            # Check if form has required fields and submit button
            if element.name == 'form':
                inputs = element.find_all(['input', 'textarea', 'select'])
                submit_button = element.find(['input', 'button'], type='submit') or element.find('button')
                return len(inputs) > 0 and submit_button is not None
        
        elif task_type == TaskType.CALCULATOR:
            # Check for numeric inputs and calculation logic
            if element.name == 'form':
                numeric_inputs = element.find_all('input', type='number')
                return len(numeric_inputs) > 0
        
        elif task_type == TaskType.DOWNLOAD:
            # Check for download attribute or downloadable file extension
            if element.name == 'a':
                href = element.get('href', '')
                return element.get('download') is not None or any(
                    ext in href for ext in ['.pdf', '.doc', '.xls', '.zip']
                )
        
        elif task_type == TaskType.CHECKLIST:
            # Check for checkboxes or list items
            checkboxes = element.find_all('input', type='checkbox')
            list_items = element.find_all('li')
            return len(checkboxes) > 0 or len(list_items) > 2
        
        # Default: element exists and is interactive
        return element.name in ['form', 'button', 'input', 'select', 'textarea', 'a']
    
    def _validate_accessibility(self, element) -> List[str]:
        """Validate accessibility of task completer."""
        issues = []
        
        # Check for labels
        if element.name in ['input', 'select', 'textarea']:
            label_id = element.get('id')
            aria_label = element.get('aria-label')
            aria_labelledby = element.get('aria-labelledby')
            
            if not any([label_id, aria_label, aria_labelledby]):
                issues.append("Form control missing label or aria-label")
        
        # Check for alt text on images
        images = element.find_all('img')
        for img in images:
            if not img.get('alt'):
                issues.append("Image missing alt text")
        
        # Check for keyboard accessibility
        if element.name in ['button', 'a']:
            if element.name == 'a' and not element.get('href'):
                issues.append("Link missing href attribute")
            
            # Check for role if needed
            if element.get('role') == 'button' and element.name != 'button':
                if not element.get('tabindex'):
                    issues.append("Custom button missing tabindex")
        
        # Check color contrast (basic check for inline styles)
        style = element.get('style', '')
        if 'color:' in style and 'background' not in style:
            issues.append("Potential color contrast issue - check manually")
        
        return issues
    
    def _validate_mobile_friendly(self, element) -> bool:
        """Check if element is mobile-friendly."""
        # Check for responsive design indicators
        classes = ' '.join(element.get('class', []))
        
        # Look for common responsive framework classes
        responsive_patterns = [
            'col-', 'grid-', 'flex-', 'responsive',
            'mobile-', 'sm-', 'md-', 'lg-', 'xl-'
        ]
        
        has_responsive_classes = any(pattern in classes for pattern in responsive_patterns)
        
        # Check for mobile-unfriendly fixed widths in style
        style = element.get('style', '')
        has_fixed_width = 'width:' in style and 'px' in style
        
        # Check for touch-friendly size (buttons should be at least 44px)
        is_touch_friendly = True  # Default assumption
        if 'height:' in style:
            # Basic check for height - this would need more sophisticated parsing
            if 'height: 20px' in style or 'height:20px' in style:
                is_touch_friendly = False
        
        return has_responsive_classes or (not has_fixed_width and is_touch_friendly)
    
    def _generate_audit_result(
        self,
        page_url: str,
        task_completers: List[TaskCompleter],
        is_money_page: bool
    ) -> TaskCompletionAuditResult:
        """Generate comprehensive audit result."""
        valid_completers = [tc for tc in task_completers if tc.is_valid]
        
        # Count by type
        task_completers_by_type = {}
        for task_type in TaskType:
            count = len([tc for tc in task_completers if tc.task_type == task_type])
            if count > 0:
                task_completers_by_type[task_type] = count
        
        # Calculate metrics
        total_count = len(task_completers)
        valid_count = len(valid_completers)
        
        meets_minimum = total_count >= self.content_config.task_completers_required
        meets_money_page = not is_money_page or total_count >= 2
        
        # Calculate average completion rate
        completion_rates = [tc.completion_rate for tc in task_completers if tc.completion_rate is not None]
        avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0.0
        
        # Calculate total engagement score
        engagement_scores = [tc.engagement_score for tc in task_completers]
        total_engagement_score = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0.0
        
        # Collect issues
        validation_issues = []
        accessibility_issues = []
        functionality_issues = []
        analytics_issues = []
        
        for tc in task_completers:
            validation_issues.extend(tc.validation_issues)
            accessibility_issues.extend(tc.accessibility_issues)
            
            if not tc.is_functional:
                functionality_issues.append(f"{tc.title}: Not functional")
            
            if not tc.has_analytics_tracking:
                analytics_issues.append(f"{tc.title}: Missing analytics tracking")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            task_completers=task_completers,
            is_money_page=is_money_page,
            meets_minimum=meets_minimum
        )
        
        # Identify priority fixes
        priority_fixes = []
        if not meets_minimum:
            priority_fixes.append(f"Add {self.content_config.task_completers_required - total_count} more task completers")
        
        if is_money_page and not meets_money_page:
            priority_fixes.append("Add additional task completer for money page (minimum 2 required)")
        
        critical_issues = [tc for tc in task_completers if tc.validation_status == TaskCompleterValidation.NOT_FUNCTIONAL]
        if critical_issues:
            priority_fixes.append(f"Fix {len(critical_issues)} non-functional task completers")
        
        return TaskCompletionAuditResult(
            page_url=page_url,
            audit_timestamp=datetime.now(timezone.utc),
            total_task_completers=total_count,
            valid_task_completers=valid_count,
            task_completers_by_type=task_completers_by_type,
            meets_minimum_requirement=meets_minimum,
            meets_money_page_requirement=meets_money_page,
            avg_completion_rate=avg_completion_rate,
            total_engagement_score=total_engagement_score,
            validation_issues=list(set(validation_issues)),
            accessibility_issues=list(set(accessibility_issues)),
            functionality_issues=functionality_issues,
            analytics_issues=analytics_issues,
            recommendations=recommendations,
            priority_fixes=priority_fixes,
            task_completers=task_completers
        )
    
    def _generate_recommendations(
        self,
        task_completers: List[TaskCompleter],
        is_money_page: bool,
        meets_minimum: bool
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Task completer quantity recommendations
        if not meets_minimum:
            recommendations.append(
                f"Add more task completion elements. Current: {len(task_completers)}, "
                f"Required: {self.content_config.task_completers_required}"
            )
        
        if is_money_page and len(task_completers) < 2:
            recommendations.append(
                "Money pages should have at least 2 task completion elements for better conversion"
            )
        
        # Type diversity recommendations
        task_types_present = {tc.task_type for tc in task_completers}
        if len(task_types_present) < 2 and len(task_completers) >= 2:
            recommendations.append(
                "Consider diversifying task completer types (calculator + download, form + checklist, etc.)"
            )
        
        # Accessibility recommendations
        accessibility_issues = sum(len(tc.accessibility_issues) for tc in task_completers)
        if accessibility_issues > 0:
            recommendations.append(
                f"Fix {accessibility_issues} accessibility issues to improve user experience for all users"
            )
        
        # Analytics tracking recommendations
        untracked_completers = [tc for tc in task_completers if not tc.has_analytics_tracking]
        if untracked_completers:
            recommendations.append(
                f"Add analytics tracking to {len(untracked_completers)} task completers to measure performance"
            )
        
        # Position optimization
        above_fold_completers = [tc for tc in task_completers if tc.position_on_page == "above-fold"]
        if len(above_fold_completers) == 0 and task_completers:
            recommendations.append(
                "Consider placing at least one task completer above the fold for better visibility"
            )
        
        # Mobile optimization
        non_mobile_friendly = [tc for tc in task_completers if not tc.mobile_friendly]
        if non_mobile_friendly:
            recommendations.append(
                f"Optimize {len(non_mobile_friendly)} task completers for mobile devices"
            )
        
        # Engagement optimization
        low_engagement = [tc for tc in task_completers if tc.completion_rate and tc.completion_rate < 0.1]
        if low_engagement:
            recommendations.append(
                f"Improve {len(low_engagement)} task completers with completion rates below 10%"
            )
        
        return recommendations
    
    async def audit_multiple_pages(
        self,
        page_urls: List[str],
        money_page_urls: List[str] = None
    ) -> Dict[str, TaskCompletionAuditResult]:
        """Audit task completion across multiple pages."""
        money_page_urls = money_page_urls or []
        results = {}
        
        for url in page_urls:
            try:
                is_money_page = url in money_page_urls
                result = await self.audit_page_task_completion(
                    page_url=url,
                    is_money_page=is_money_page
                )
                results[url] = result
                logger.info(f"Completed audit for {url}: {result.total_task_completers} task completers found")
                
            except Exception as e:
                logger.error(f"Error auditing {url}: {e}")
                continue
        
        return results
    
    def export_audit_results(
        self,
        results: Union[TaskCompletionAuditResult, Dict[str, TaskCompletionAuditResult]],
        output_path: Path,
        format: str = "json"
    ) -> None:
        """Export audit results to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        if isinstance(results, TaskCompletionAuditResult):
            data = self._serialize_audit_result(results)
        else:
            data = {url: self._serialize_audit_result(result) for url, result in results.items()}
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Task completion audit results exported to {output_path}")
    
    def _serialize_audit_result(self, result: TaskCompletionAuditResult) -> Dict[str, Any]:
        """Convert audit result to serializable dictionary."""
        return {
            "page_url": result.page_url,
            "audit_timestamp": result.audit_timestamp.isoformat(),
            "summary": {
                "total_task_completers": result.total_task_completers,
                "valid_task_completers": result.valid_task_completers,
                "meets_minimum_requirement": result.meets_minimum_requirement,
                "meets_money_page_requirement": result.meets_money_page_requirement,
                "avg_completion_rate": result.avg_completion_rate,
                "total_engagement_score": result.total_engagement_score
            },
            "task_completers_by_type": {k.value: v for k, v in result.task_completers_by_type.items()},
            "issues": {
                "validation_issues": result.validation_issues,
                "accessibility_issues": result.accessibility_issues,
                "functionality_issues": result.functionality_issues,
                "analytics_issues": result.analytics_issues
            },
            "recommendations": result.recommendations,
            "priority_fixes": result.priority_fixes,
            "task_completers": [
                {
                    "element_id": tc.element_id,
                    "task_type": tc.task_type.value,
                    "title": tc.title,
                    "description": tc.description,
                    "completion_trigger": tc.completion_trigger.value,
                    "position_on_page": tc.position_on_page,
                    "is_functional": tc.is_functional,
                    "is_accessible": tc.is_accessible,
                    "mobile_friendly": tc.mobile_friendly,
                    "has_analytics_tracking": tc.has_analytics_tracking,
                    "validation_status": tc.validation_status.value,
                    "validation_issues": tc.validation_issues,
                    "completion_rate": tc.completion_rate,
                    "engagement_score": tc.engagement_score
                }
                for tc in result.task_completers
            ]
        }
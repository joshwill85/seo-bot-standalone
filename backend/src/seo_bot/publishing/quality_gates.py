"""Quality gate implementations for content publishing pipeline."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from .pipeline import QualityGate, QualityGateEvaluation, QualityGateResult
from ..adapters.cms.base import ContentItem
from ..tech.accessibility import AccessibilityChecker
from ..tech.audit import TechnicalSEOAuditor
from ..tech.budgets import PerformanceBudgetManager
from ..content.stc_check import SearchTaskCompletionChecker

logger = logging.getLogger(__name__)


class ContentQualityGate(QualityGate):
    """Quality gate for basic content quality checks."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize content quality gate."""
        super().__init__("Content Quality", config)
        
        # Content quality thresholds
        self.min_word_count = self.config.get('min_word_count', 800)
        self.max_word_count = self.config.get('max_word_count', 3000)
        self.min_readability_score = self.config.get('min_readability_score', 60)
        self.max_keyword_density = self.config.get('max_keyword_density', 0.03)
        self.require_meta_description = self.config.get('require_meta_description', True)
        self.require_featured_image = self.config.get('require_featured_image', False)
    
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate content quality."""
        issues = []
        warnings = []
        recommendations = []
        score = 100.0
        
        try:
            # Word count check
            word_count = len(content.content.split())
            
            if word_count < self.min_word_count:
                issues.append(f"Content too short: {word_count} words (minimum: {self.min_word_count})")
                score -= 20
            elif word_count > self.max_word_count:
                warnings.append(f"Content very long: {word_count} words (recommended max: {self.max_word_count})")
                score -= 5
            
            # Meta description check
            if self.require_meta_description and not content.meta_description:
                issues.append("Meta description is required but missing")
                score -= 15
            elif content.meta_description:
                meta_length = len(content.meta_description)
                if meta_length < 120:
                    warnings.append(f"Meta description too short: {meta_length} chars (recommended: 120-160)")
                    score -= 5
                elif meta_length > 160:
                    warnings.append(f"Meta description too long: {meta_length} chars (recommended: 120-160)")
                    score -= 5
            
            # Title checks
            title_length = len(content.title)
            if title_length < 30:
                warnings.append(f"Title too short: {title_length} chars (recommended: 30-60)")
                score -= 5
            elif title_length > 60:
                warnings.append(f"Title too long: {title_length} chars (recommended: 30-60)")
                score -= 5
            
            # Featured image check
            if self.require_featured_image and not content.featured_image_url:
                issues.append("Featured image is required but missing")
                score -= 10
            
            # Basic content structure checks
            if not self._has_proper_headings(content.content):
                warnings.append("Content lacks proper heading structure (H2, H3)")
                score -= 5
            
            # Check for duplicate content patterns
            if self._has_repetitive_content(content.content):
                warnings.append("Content appears to have repetitive sections")
                score -= 10
            
            # Readability check (simplified)
            readability_score = self._calculate_basic_readability(content.content)
            if readability_score < self.min_readability_score:
                warnings.append(f"Low readability score: {readability_score:.1f} (minimum: {self.min_readability_score})")
                score -= 10
            
            # Generate recommendations
            if word_count < 1000:
                recommendations.append("Consider expanding content with more detailed examples and explanations")
            
            if not content.meta_description:
                recommendations.append("Add a compelling meta description to improve search snippets")
            
            if not self._has_call_to_action(content.content):
                recommendations.append("Consider adding clear calls-to-action to guide reader engagement")
            
            # Determine final result
            if score >= self.min_score and not issues:
                result = QualityGateResult.PASS
                message = f"Content quality passed (score: {score:.1f})"
            elif issues:
                result = QualityGateResult.FAIL
                message = f"Content quality failed with {len(issues)} issues (score: {score:.1f})"
            else:
                result = QualityGateResult.WARNING
                message = f"Content quality passed with warnings (score: {score:.1f})"
            
            return self.create_evaluation(
                result=result,
                score=score,
                message=message,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Content quality gate evaluation failed: {e}")
            return self.create_evaluation(
                result=QualityGateResult.FAIL,
                score=0.0,
                message=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _has_proper_headings(self, content: str) -> bool:
        """Check if content has proper heading structure."""
        # Look for H2 or H3 tags
        heading_pattern = r'<h[23][^>]*>|##\s|###\s'
        return bool(re.search(heading_pattern, content, re.IGNORECASE))
    
    def _has_repetitive_content(self, content: str) -> bool:
        """Check for repetitive content patterns."""
        # Simple check for repeated paragraphs
        sentences = content.split('.')
        unique_sentences = set(sentence.strip().lower() for sentence in sentences if len(sentence.strip()) > 10)
        
        if len(sentences) > 10 and len(unique_sentences) / len(sentences) < 0.8:
            return True
        
        return False
    
    def _calculate_basic_readability(self, content: str) -> float:
        """Calculate basic readability score (simplified Flesch)."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        
        # Count sentences and words
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        syllables = self._count_syllables(text)
        
        if sentences == 0 or words == 0:
            return 0.0
        
        # Simplified Flesch Reading Ease
        avg_sentence_length = words / sentences
        avg_syllables_per_word = syllables / words
        
        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        return max(0.0, min(100.0, score))
    
    def _count_syllables(self, text: str) -> int:
        """Count syllables in text (simplified)."""
        # Very basic syllable counting
        vowels = "aeiouyAEIOUY"
        syllable_count = 0
        prev_was_vowel = False
        
        for char in text:
            if char in vowels:
                if not prev_was_vowel:
                    syllable_count += 1
                prev_was_vowel = True
            else:
                prev_was_vowel = False
        
        return max(1, syllable_count)
    
    def _has_call_to_action(self, content: str) -> bool:
        """Check if content has call-to-action elements."""
        cta_patterns = [
            r'(try|download|get|start|learn|read|subscribe|contact|buy)',
            r'(click here|get started|learn more|try now|contact us)',
            r'<button|<a[^>]*class[^>]*button'
        ]
        
        for pattern in cta_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False


class SEOQualityGate(QualityGate):
    """Quality gate for SEO compliance checks."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize SEO quality gate."""
        super().__init__("SEO Quality", config)
        
        self.require_meta_title = self.config.get('require_meta_title', True)
        self.require_canonical_url = self.config.get('require_canonical_url', False)
        self.require_schema_markup = self.config.get('require_schema_markup', False)
        self.max_title_length = self.config.get('max_title_length', 60)
        self.max_meta_description_length = self.config.get('max_meta_description_length', 160)
    
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate SEO compliance."""
        issues = []
        warnings = []
        recommendations = []
        score = 100.0
        
        try:
            # Title tag checks
            if not content.title:
                issues.append("Title is required")
                score -= 25
            else:
                if len(content.title) > self.max_title_length:
                    warnings.append(f"Title too long: {len(content.title)} chars (max: {self.max_title_length})")
                    score -= 10
                
                # Check for keyword in title
                if not self._has_target_keyword_in_title(content):
                    recommendations.append("Consider including primary keyword in title")
            
            # Meta title check
            if self.require_meta_title and not content.meta_title:
                issues.append("Meta title is required")
                score -= 15
            
            # Meta description checks
            if not content.meta_description:
                warnings.append("Meta description is missing")
                score -= 15
            else:
                meta_length = len(content.meta_description)
                if meta_length > self.max_meta_description_length:
                    warnings.append(f"Meta description too long: {meta_length} chars (max: {self.max_meta_description_length})")
                    score -= 5
            
            # Canonical URL check
            if self.require_canonical_url and not content.canonical_url:
                issues.append("Canonical URL is required")
                score -= 10
            
            # Schema markup check
            if self.require_schema_markup and not content.schema_markup:
                issues.append("Schema markup is required")
                score -= 15
            
            # Slug checks
            if not content.slug:
                issues.append("URL slug is required")
                score -= 20
            else:
                if not self._is_seo_friendly_slug(content.slug):
                    warnings.append("Slug should be more SEO-friendly (lowercase, hyphens, descriptive)")
                    score -= 5
            
            # Content SEO checks
            if not self._has_proper_heading_hierarchy(content.content):
                warnings.append("Content lacks proper heading hierarchy (H1 > H2 > H3)")
                score -= 10
            
            if not self._has_internal_links(content.content):
                recommendations.append("Consider adding relevant internal links")
            
            if not self._has_external_links(content.content):
                recommendations.append("Consider adding authoritative external references")
            
            # Image SEO checks
            if content.featured_image_url and not content.featured_image_alt:
                warnings.append("Featured image missing alt text")
                score -= 5
            
            # Generate additional recommendations
            recommendations.extend(self._generate_seo_recommendations(content))
            
            # Determine final result
            if score >= self.min_score and not issues:
                result = QualityGateResult.PASS
                message = f"SEO quality passed (score: {score:.1f})"
            elif issues:
                result = QualityGateResult.FAIL
                message = f"SEO quality failed with {len(issues)} issues (score: {score:.1f})"
            else:
                result = QualityGateResult.WARNING
                message = f"SEO quality passed with warnings (score: {score:.1f})"
            
            return self.create_evaluation(
                result=result,
                score=score,
                message=message,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"SEO quality gate evaluation failed: {e}")
            return self.create_evaluation(
                result=QualityGateResult.FAIL,
                score=0.0,
                message=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _has_target_keyword_in_title(self, content: ContentItem) -> bool:
        """Check if title contains likely target keywords."""
        # This is simplified - in practice you'd have specific target keywords
        title_lower = content.title.lower()
        
        # Look for keywords in tags/categories as potential targets
        for tag in content.tags:
            if tag.lower() in title_lower:
                return True
        
        for category in content.categories:
            if category.lower() in title_lower:
                return True
        
        return False
    
    def _is_seo_friendly_slug(self, slug: str) -> bool:
        """Check if slug is SEO-friendly."""
        # Should be lowercase, use hyphens, no special characters
        return bool(re.match(r'^[a-z0-9-]+$', slug) and len(slug) > 3)
    
    def _has_proper_heading_hierarchy(self, content: str) -> bool:
        """Check for proper heading hierarchy."""
        # Look for H1, H2, H3 tags in order
        h1_pattern = r'<h1[^>]*>|#\s'
        h2_pattern = r'<h2[^>]*>|##\s'
        
        has_h1 = bool(re.search(h1_pattern, content, re.IGNORECASE))
        has_h2 = bool(re.search(h2_pattern, content, re.IGNORECASE))
        
        return has_h1 and has_h2
    
    def _has_internal_links(self, content: str) -> bool:
        """Check for internal links."""
        # Look for relative links or same-domain links
        internal_link_patterns = [
            r'<a[^>]*href=["\']\/[^"\']*["\']',  # Relative links
            r'<a[^>]*href=["\'][^"\']*(?:\.html|\.php)["\']'  # Local file links
        ]
        
        for pattern in internal_link_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def _has_external_links(self, content: str) -> bool:
        """Check for external links."""
        # Look for absolute HTTP/HTTPS links
        external_link_pattern = r'<a[^>]*href=["\']https?://[^"\']*["\']'
        return bool(re.search(external_link_pattern, content, re.IGNORECASE))
    
    def _generate_seo_recommendations(self, content: ContentItem) -> List[str]:
        """Generate SEO recommendations."""
        recommendations = []
        
        if not content.categories:
            recommendations.append("Add relevant categories to improve content organization")
        
        if not content.tags:
            recommendations.append("Add descriptive tags to improve content discoverability")
        
        if len(content.content) < 1000:
            recommendations.append("Consider expanding content for better search rankings")
        
        return recommendations


class AccessibilityQualityGate(QualityGate):
    """Quality gate for accessibility compliance."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize accessibility quality gate."""
        super().__init__("Accessibility Quality", config)
        
        self.require_alt_text = self.config.get('require_alt_text', True)
        self.require_heading_structure = self.config.get('require_heading_structure', True)
        self.min_color_contrast = self.config.get('min_color_contrast', 4.5)
    
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate accessibility compliance."""
        issues = []
        warnings = []
        recommendations = []
        score = 100.0
        
        try:
            # Featured image alt text check
            if content.featured_image_url and not content.featured_image_alt:
                if self.require_alt_text:
                    issues.append("Featured image missing alt text")
                    score -= 20
                else:
                    warnings.append("Featured image missing alt text")
                    score -= 5
            
            # Check content for images without alt text
            image_alt_issues = self._check_content_images(content.content)
            if image_alt_issues:
                issues.extend(image_alt_issues)
                score -= min(30, len(image_alt_issues) * 5)
            
            # Heading structure check
            if self.require_heading_structure:
                heading_issues = self._check_heading_structure(content.content)
                if heading_issues:
                    warnings.extend(heading_issues)
                    score -= min(20, len(heading_issues) * 5)
            
            # Check for accessibility best practices
            accessibility_warnings = self._check_accessibility_patterns(content.content)
            warnings.extend(accessibility_warnings)
            score -= min(15, len(accessibility_warnings) * 3)
            
            # Generate recommendations
            recommendations.extend(self._generate_accessibility_recommendations(content))
            
            # Determine final result
            if score >= self.min_score and not issues:
                result = QualityGateResult.PASS
                message = f"Accessibility quality passed (score: {score:.1f})"
            elif issues:
                result = QualityGateResult.FAIL
                message = f"Accessibility quality failed with {len(issues)} issues (score: {score:.1f})"
            else:
                result = QualityGateResult.WARNING
                message = f"Accessibility quality passed with warnings (score: {score:.1f})"
            
            return self.create_evaluation(
                result=result,
                score=score,
                message=message,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Accessibility quality gate evaluation failed: {e}")
            return self.create_evaluation(
                result=QualityGateResult.FAIL,
                score=0.0,
                message=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _check_content_images(self, content: str) -> List[str]:
        """Check images in content for alt text."""
        issues = []
        
        # Find all img tags
        img_pattern = r'<img[^>]*>'
        img_tags = re.findall(img_pattern, content, re.IGNORECASE)
        
        for img_tag in img_tags:
            # Check if alt attribute is present and not empty
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_tag, re.IGNORECASE)
            if not alt_match or not alt_match.group(1).strip():
                issues.append("Image missing alt text")
        
        return issues
    
    def _check_heading_structure(self, content: str) -> List[str]:
        """Check heading structure for accessibility."""
        issues = []
        
        # Find all heading tags
        heading_pattern = r'<h([1-6])[^>]*>'
        headings = re.findall(heading_pattern, content, re.IGNORECASE)
        
        if not headings:
            issues.append("Content lacks heading structure")
            return issues
        
        # Check for proper hierarchy
        heading_levels = [int(h) for h in headings]
        
        # Should start with H1 or H2
        if heading_levels and heading_levels[0] > 2:
            issues.append("Content should start with H1 or H2")
        
        # Check for skipped levels
        for i in range(len(heading_levels) - 1):
            if heading_levels[i + 1] > heading_levels[i] + 1:
                issues.append("Heading levels should not skip (e.g., H2 to H4)")
                break
        
        return issues
    
    def _check_accessibility_patterns(self, content: str) -> List[str]:
        """Check for accessibility patterns and issues."""
        warnings = []
        
        # Check for links with generic text
        generic_link_pattern = r'<a[^>]*>(?:click here|read more|more|here)</a>'
        if re.search(generic_link_pattern, content, re.IGNORECASE):
            warnings.append("Links with generic text like 'click here' should be more descriptive")
        
        # Check for tables without headers
        table_pattern = r'<table[^>]*>(?!.*<th[^>]*>)'
        if re.search(table_pattern, content, re.IGNORECASE | re.DOTALL):
            warnings.append("Tables should include header cells (<th>) for accessibility")
        
        # Check for form inputs without labels (simplified)
        input_pattern = r'<input[^>]*>'
        inputs = re.findall(input_pattern, content, re.IGNORECASE)
        for input_tag in inputs:
            if 'type="hidden"' not in input_tag.lower():
                if 'id=' not in input_tag.lower() and 'aria-label=' not in input_tag.lower():
                    warnings.append("Form inputs should have associated labels")
                    break
        
        return warnings
    
    def _generate_accessibility_recommendations(self, content: ContentItem) -> List[str]:
        """Generate accessibility recommendations."""
        recommendations = []
        
        if not content.featured_image_alt and content.featured_image_url:
            recommendations.append("Add descriptive alt text to featured image")
        
        recommendations.append("Ensure color contrast meets WCAG AA standards (4.5:1)")
        recommendations.append("Test content with screen readers")
        recommendations.append("Verify keyboard navigation works for all interactive elements")
        
        return recommendations


class PerformanceQualityGate(QualityGate):
    """Quality gate for performance requirements."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize performance quality gate."""
        super().__init__("Performance Quality", config)
        
        self.max_image_size_kb = self.config.get('max_image_size_kb', 500)
        self.require_lazy_loading = self.config.get('require_lazy_loading', True)
        self.check_external_resources = self.config.get('check_external_resources', True)
    
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate performance requirements."""
        issues = []
        warnings = []
        recommendations = []
        score = 100.0
        
        try:
            # Check for large images
            if content.featured_image_url:
                # In a real implementation, you'd check actual image size
                recommendations.append("Ensure featured image is optimized for web (WebP format, compressed)")
            
            # Check content for performance issues
            performance_issues = self._check_content_performance(content.content)
            warnings.extend(performance_issues)
            score -= min(20, len(performance_issues) * 5)
            
            # Check for external resource dependencies
            if self.check_external_resources:
                external_issues = self._check_external_resources(content.content)
                warnings.extend(external_issues)
                score -= min(15, len(external_issues) * 3)
            
            # Generate performance recommendations
            recommendations.extend(self._generate_performance_recommendations(content))
            
            # Determine final result
            if score >= self.min_score and not issues:
                result = QualityGateResult.PASS
                message = f"Performance quality passed (score: {score:.1f})"
            elif issues:
                result = QualityGateResult.FAIL
                message = f"Performance quality failed with {len(issues)} issues (score: {score:.1f})"
            else:
                result = QualityGateResult.WARNING
                message = f"Performance quality passed with warnings (score: {score:.1f})"
            
            return self.create_evaluation(
                result=result,
                score=score,
                message=message,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Performance quality gate evaluation failed: {e}")
            return self.create_evaluation(
                result=QualityGateResult.FAIL,
                score=0.0,
                message=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _check_content_performance(self, content: str) -> List[str]:
        """Check content for performance issues."""
        warnings = []
        
        # Check for images without lazy loading
        if self.require_lazy_loading:
            img_pattern = r'<img[^>]*>'
            img_tags = re.findall(img_pattern, content, re.IGNORECASE)
            
            for img_tag in img_tags:
                if 'loading=' not in img_tag.lower():
                    warnings.append("Images should use lazy loading for better performance")
                    break
        
        # Check for inline styles (can hurt performance)
        if re.search(r'style\s*=', content, re.IGNORECASE):
            warnings.append("Avoid inline styles - use CSS classes instead")
        
        # Check for large embedded content
        if re.search(r'<iframe[^>]*youtube[^>]*>', content, re.IGNORECASE):
            warnings.append("Consider lazy loading YouTube embeds")
        
        return warnings
    
    def _check_external_resources(self, content: str) -> List[str]:
        """Check for external resource dependencies."""
        warnings = []
        
        # Check for external scripts
        script_pattern = r'<script[^>]*src=["\']https?://[^"\']*["\']'
        if re.search(script_pattern, content, re.IGNORECASE):
            warnings.append("External scripts can impact page performance")
        
        # Check for external stylesheets
        css_pattern = r'<link[^>]*href=["\']https?://[^"\']*\.css["\']'
        if re.search(css_pattern, content, re.IGNORECASE):
            warnings.append("External stylesheets can slow page rendering")
        
        return warnings
    
    def _generate_performance_recommendations(self, content: ContentItem) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        recommendations.append("Optimize all images (compress, use WebP format)")
        recommendations.append("Implement lazy loading for below-the-fold content")
        recommendations.append("Minimize external dependencies")
        recommendations.append("Use CDN for asset delivery")
        
        return recommendations


class TaskCompletionQualityGate(QualityGate):
    """Quality gate for task completion elements."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize task completion quality gate."""
        super().__init__("Task Completion Quality", config)
        
        self.min_task_completers = self.config.get('min_task_completers', 1)
        self.required_for_money_pages = self.config.get('required_for_money_pages', 2)
        self.require_analytics_tracking = self.config.get('require_analytics_tracking', True)
    
    async def evaluate(self, content: ContentItem, context: Dict[str, Any] = None) -> QualityGateEvaluation:
        """Evaluate task completion requirements."""
        issues = []
        warnings = []
        recommendations = []
        score = 100.0
        
        try:
            # Check for task completion elements in content
            task_completers = self._find_task_completers(content.content)
            
            # Determine if this is a "money page"
            is_money_page = self._is_money_page(content)
            
            # Check minimum requirements
            min_required = self.required_for_money_pages if is_money_page else self.min_task_completers
            
            if len(task_completers) < min_required:
                page_type = "money page" if is_money_page else "page"
                issues.append(f"Insufficient task completers: {len(task_completers)} found, {min_required} required for {page_type}")
                score -= 30
            
            # Check task completer quality
            for completer in task_completers:
                if not self._has_clear_purpose(completer):
                    warnings.append(f"Task completer lacks clear purpose: {completer['type']}")
                    score -= 5
                
                if self.require_analytics_tracking and not self._has_analytics_tracking(completer):
                    warnings.append(f"Task completer missing analytics tracking: {completer['type']}")
                    score -= 5
            
            # Generate recommendations
            recommendations.extend(self._generate_task_completer_recommendations(content, task_completers, is_money_page))
            
            # Determine final result
            if score >= self.min_score and not issues:
                result = QualityGateResult.PASS
                message = f"Task completion quality passed with {len(task_completers)} task completers (score: {score:.1f})"
            elif issues:
                result = QualityGateResult.FAIL
                message = f"Task completion quality failed (score: {score:.1f})"
            else:
                result = QualityGateResult.WARNING
                message = f"Task completion quality passed with warnings (score: {score:.1f})"
            
            return self.create_evaluation(
                result=result,
                score=score,
                message=message,
                issues=issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Task completion quality gate evaluation failed: {e}")
            return self.create_evaluation(
                result=QualityGateResult.FAIL,
                score=0.0,
                message=f"Evaluation failed: {str(e)}",
                issues=[str(e)]
            )
    
    def _find_task_completers(self, content: str) -> List[Dict[str, Any]]:
        """Find task completion elements in content."""
        task_completers = []
        
        # Look for forms
        forms = re.findall(r'<form[^>]*>.*?</form>', content, re.IGNORECASE | re.DOTALL)
        for form in forms:
            task_completers.append({
                'type': 'form',
                'element': form,
                'has_analytics': 'data-' in form or 'onclick=' in form
            })
        
        # Look for download links
        downloads = re.findall(r'<a[^>]*download[^>]*>.*?</a>', content, re.IGNORECASE | re.DOTALL)
        for download in downloads:
            task_completers.append({
                'type': 'download',
                'element': download,
                'has_analytics': 'data-' in download or 'onclick=' in download
            })
        
        # Look for calculators/tools
        calculators = re.findall(r'<[^>]*(?:calculator|tool|calc)[^>]*>', content, re.IGNORECASE)
        for calc in calculators:
            task_completers.append({
                'type': 'calculator',
                'element': calc,
                'has_analytics': 'data-' in calc or 'onclick=' in calc
            })
        
        # Look for interactive buttons
        buttons = re.findall(r'<button[^>]*>.*?</button>', content, re.IGNORECASE | re.DOTALL)
        for button in buttons:
            if any(keyword in button.lower() for keyword in ['get', 'try', 'start', 'calculate']):
                task_completers.append({
                    'type': 'interactive_button',
                    'element': button,
                    'has_analytics': 'data-' in button or 'onclick=' in button
                })
        
        return task_completers
    
    def _is_money_page(self, content: ContentItem) -> bool:
        """Determine if this is a money page."""
        money_indicators = [
            'buy', 'purchase', 'price', 'cost', 'product', 'service',
            'comparison', 'review', 'best', 'vs', 'versus'
        ]
        
        content_text = (content.title + ' ' + content.content + ' ' + ' '.join(content.categories) + ' ' + ' '.join(content.tags)).lower()
        
        return any(indicator in content_text for indicator in money_indicators)
    
    def _has_clear_purpose(self, completer: Dict[str, Any]) -> bool:
        """Check if task completer has clear purpose."""
        element = completer['element'].lower()
        
        # Look for descriptive text, labels, or clear calls to action
        purpose_indicators = [
            'submit', 'download', 'calculate', 'get', 'try', 'start',
            'subscribe', 'contact', 'learn', 'find'
        ]
        
        return any(indicator in element for indicator in purpose_indicators)
    
    def _has_analytics_tracking(self, completer: Dict[str, Any]) -> bool:
        """Check if task completer has analytics tracking."""
        return completer.get('has_analytics', False)
    
    def _generate_task_completer_recommendations(
        self,
        content: ContentItem,
        task_completers: List[Dict[str, Any]],
        is_money_page: bool
    ) -> List[str]:
        """Generate task completer recommendations."""
        recommendations = []
        
        if len(task_completers) == 0:
            recommendations.append("Add task completion elements (forms, downloads, calculators)")
        
        if is_money_page and len(task_completers) < 2:
            recommendations.append("Money pages should have multiple task completion options")
        
        if not any(tc['type'] == 'form' for tc in task_completers):
            recommendations.append("Consider adding a contact or subscription form")
        
        if 'download' in content.content.lower() and not any(tc['type'] == 'download' for tc in task_completers):
            recommendations.append("Add downloadable resources mentioned in content")
        
        recommendations.append("Ensure all task completers have analytics tracking")
        recommendations.append("Make task completers visually prominent and easy to find")
        
        return recommendations
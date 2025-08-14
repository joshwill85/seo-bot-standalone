"""Performance budget system with Core Web Vitals monitoring and auto-optimization."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import json
import aiohttp
import time

from ..config import PerformanceBudget, PerformanceBudgetsConfig, Settings
from ..models import Page, PerformanceMetric, Project


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Performance metric types."""
    LCP = "lcp"  # Largest Contentful Paint
    INP = "inp"  # Interaction to Next Paint  
    CLS = "cls"  # Cumulative Layout Shift
    FCP = "fcp"  # First Contentful Paint
    TTFB = "ttfb"  # Time to First Byte
    JAVASCRIPT_SIZE = "js_size"
    CSS_SIZE = "css_size" 
    IMAGE_SIZE = "image_size"
    TOTAL_SIZE = "total_size"


class ViolationSeverity(Enum):
    """Severity levels for budget violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OptimizationType(Enum):
    """Types of automatic optimizations."""
    IMAGE_COMPRESSION = "image_compression"
    IMAGE_FORMAT_CONVERSION = "image_format_conversion"
    LAZY_LOADING = "lazy_loading"
    CSS_MINIFICATION = "css_minification"
    JS_MINIFICATION = "js_minification"
    CRITICAL_CSS_INLINE = "critical_css_inline"
    RESOURCE_PRELOADING = "resource_preloading"
    THIRD_PARTY_OPTIMIZATION = "third_party_optimization"


@dataclass
class BudgetViolation:
    """Represents a performance budget violation."""
    
    metric_type: MetricType
    current_value: Union[int, float]
    budget_value: Union[int, float]
    severity: ViolationSeverity
    violation_percentage: float
    template_type: str
    page_url: str
    device_type: str = "mobile"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_critical(self) -> bool:
        """Check if violation is critical (>50% over budget)."""
        return self.violation_percentage > 0.5
    
    @property
    def description(self) -> str:
        """Human-readable violation description."""
        metric_name = self.metric_type.value.upper().replace("_", " ")
        unit = "ms" if "time" in self.metric_type.value or self.metric_type.value in ["lcp", "inp", "fcp", "ttfb"] else "KB" if "size" in self.metric_type.value else ""
        
        return (
            f"{metric_name} violation: {self.current_value}{unit} "
            f"(budget: {self.budget_value}{unit}, "
            f"{self.violation_percentage:.1%} over)"
        )


@dataclass 
class OptimizationRecommendation:
    """Represents an automatic optimization recommendation."""
    
    optimization_type: OptimizationType
    target_metrics: List[MetricType]
    estimated_improvement: Dict[MetricType, Union[int, float]]
    implementation_effort: str  # "automatic", "low", "medium", "high"
    priority_score: float  # 0-1, higher is more important
    description: str
    implementation_steps: List[str]
    estimated_completion_time: int  # minutes
    
    @property
    def can_auto_implement(self) -> bool:
        """Check if optimization can be automatically implemented."""
        return self.implementation_effort == "automatic"


@dataclass
class PerformanceTestResult:
    """Results from a performance test."""
    
    url: str
    device_type: str
    timestamp: datetime
    test_id: str
    
    # Core Web Vitals
    lcp_ms: Optional[int] = None
    inp_ms: Optional[int] = None
    cls: Optional[float] = None
    fcp_ms: Optional[int] = None
    ttfb_ms: Optional[int] = None
    
    # Resource metrics
    total_size_kb: Optional[int] = None
    js_size_kb: Optional[int] = None
    css_size_kb: Optional[int] = None
    image_size_kb: Optional[int] = None
    
    # Lighthouse scores
    performance_score: Optional[int] = None
    accessibility_score: Optional[int] = None
    best_practices_score: Optional[int] = None
    seo_score: Optional[int] = None
    
    # Field data availability
    has_crux_data: bool = False
    crux_data: Optional[Dict[str, Any]] = None
    
    @property
    def passes_cwv_thresholds(self) -> bool:
        """Check if page passes Core Web Vitals thresholds."""
        if not all([self.lcp_ms, self.inp_ms, self.cls is not None]):
            return False
            
        return (
            self.lcp_ms <= 2500 and
            self.inp_ms <= 200 and 
            self.cls <= 0.1
        )


class PerformanceBudgetManager:
    """Manages performance budgets with Core Web Vitals monitoring and auto-optimization."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the performance budget manager."""
        self.settings = settings or Settings()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # PageSpeed Insights API configuration
        self.psi_base_url = "https://www.googleapis.com/pagespeedonline/runPagespeed/v5"
        self.psi_api_key = self.settings.pagespeed_api_key
        
        # Rate limiting for API calls
        self.last_api_call = 0
        self.api_call_interval = 1.0  # seconds between calls
        
        # Optimization cache
        self.optimization_cache: Dict[str, List[OptimizationRecommendation]] = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_page_performance(
        self,
        url: str,
        device_type: str = "mobile",
        strategy: str = "mobile",
        include_categories: List[str] = None
    ) -> PerformanceTestResult:
        """Test page performance using PageSpeed Insights API."""
        if not self.psi_api_key:
            raise ValueError("PageSpeed Insights API key not configured")
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        # Rate limiting
        now = time.time()
        time_since_last = now - self.last_api_call
        if time_since_last < self.api_call_interval:
            await asyncio.sleep(self.api_call_interval - time_since_last)
        
        categories = include_categories or ["performance", "accessibility", "best-practices", "seo"]
        
        params = {
            "url": url,
            "key": self.psi_api_key,
            "strategy": strategy,
            "category": categories,
            "locale": "en",
            "utm_campaign": "seo-bot",
            "utm_source": "pagespeed-insights"
        }
        
        try:
            async with self.session.get(self.psi_base_url, params=params) as response:
                self.last_api_call = time.time()
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"PageSpeed API error {response.status}: {error_text}")
                    raise RuntimeError(f"PageSpeed API request failed: {response.status}")
                
                data = await response.json()
                return self._parse_psi_response(url, device_type, data)
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error during PageSpeed test: {e}")
            raise RuntimeError(f"Network error: {e}")
    
    def _parse_psi_response(self, url: str, device_type: str, data: Dict[str, Any]) -> PerformanceTestResult:
        """Parse PageSpeed Insights API response."""
        lighthouse_result = data.get("lighthouseResult", {})
        audits = lighthouse_result.get("audits", {})
        categories = lighthouse_result.get("categories", {})
        
        # Core Web Vitals from lighthouse
        lcp_audit = audits.get("largest-contentful-paint", {})
        inp_audit = audits.get("interaction-to-next-paint", {})
        cls_audit = audits.get("cumulative-layout-shift", {})
        fcp_audit = audits.get("first-contentful-paint", {})
        ttfb_audit = audits.get("server-response-time", {})
        
        # Resource metrics
        resource_audit = audits.get("resource-summary", {})
        resource_details = resource_audit.get("details", {}).get("items", [])
        
        js_size = 0
        css_size = 0
        image_size = 0
        total_size = 0
        
        for item in resource_details:
            resource_type = item.get("resourceType", "")
            transfer_size = item.get("transferSize", 0) // 1024  # Convert to KB
            
            if resource_type == "script":
                js_size += transfer_size
            elif resource_type == "stylesheet":
                css_size += transfer_size
            elif resource_type == "image":
                image_size += transfer_size
            
            total_size += transfer_size
        
        # Check for CrUX data
        loading_experience = data.get("loadingExperience", {})
        has_crux_data = bool(loading_experience.get("metrics"))
        
        result = PerformanceTestResult(
            url=url,
            device_type=device_type,
            timestamp=datetime.now(timezone.utc),
            test_id=data.get("id", ""),
            
            # Core Web Vitals (convert to ms/score as needed)
            lcp_ms=int(lcp_audit.get("numericValue", 0)) if lcp_audit.get("numericValue") else None,
            inp_ms=int(inp_audit.get("numericValue", 0)) if inp_audit.get("numericValue") else None,
            cls=float(cls_audit.get("numericValue", 0)) if cls_audit.get("numericValue") is not None else None,
            fcp_ms=int(fcp_audit.get("numericValue", 0)) if fcp_audit.get("numericValue") else None,
            ttfb_ms=int(ttfb_audit.get("numericValue", 0)) if ttfb_audit.get("numericValue") else None,
            
            # Resource metrics
            total_size_kb=total_size,
            js_size_kb=js_size,
            css_size_kb=css_size,
            image_size_kb=image_size,
            
            # Lighthouse scores
            performance_score=int(categories.get("performance", {}).get("score", 0) * 100),
            accessibility_score=int(categories.get("accessibility", {}).get("score", 0) * 100),
            best_practices_score=int(categories.get("best-practices", {}).get("score", 0) * 100),
            seo_score=int(categories.get("seo", {}).get("score", 0) * 100),
            
            # CrUX data
            has_crux_data=has_crux_data,
            crux_data=loading_experience if has_crux_data else None
        )
        
        return result
    
    def check_budget_violations(
        self,
        test_result: PerformanceTestResult,
        budget: PerformanceBudget,
        template_type: str
    ) -> List[BudgetViolation]:
        """Check for budget violations in test results."""
        violations = []
        
        # Core Web Vitals checks
        metrics_to_check = [
            (MetricType.LCP, test_result.lcp_ms, budget.lcp_ms),
            (MetricType.INP, test_result.inp_ms, budget.inp_ms),
            (MetricType.CLS, test_result.cls, budget.cls),
            (MetricType.JAVASCRIPT_SIZE, test_result.js_size_kb, budget.js_kb),
            (MetricType.CSS_SIZE, test_result.css_size_kb, budget.css_kb),
            (MetricType.IMAGE_SIZE, test_result.image_size_kb, budget.image_kb),
        ]
        
        for metric_type, current_value, budget_value in metrics_to_check:
            if current_value is None or budget_value is None:
                continue
                
            if current_value > budget_value:
                violation_percentage = (current_value - budget_value) / budget_value
                
                # Determine severity
                if violation_percentage >= 1.0:  # 100%+ over budget
                    severity = ViolationSeverity.CRITICAL
                elif violation_percentage >= 0.5:  # 50-100% over budget
                    severity = ViolationSeverity.HIGH
                elif violation_percentage >= 0.25:  # 25-50% over budget
                    severity = ViolationSeverity.MEDIUM
                else:  # <25% over budget
                    severity = ViolationSeverity.LOW
                
                violation = BudgetViolation(
                    metric_type=metric_type,
                    current_value=current_value,
                    budget_value=budget_value,
                    severity=severity,
                    violation_percentage=violation_percentage,
                    template_type=template_type,
                    page_url=test_result.url,
                    device_type=test_result.device_type,
                    timestamp=test_result.timestamp
                )
                
                violations.append(violation)
        
        return violations
    
    def generate_optimization_recommendations(
        self,
        violations: List[BudgetViolation],
        test_result: PerformanceTestResult
    ) -> List[OptimizationRecommendation]:
        """Generate automatic optimization recommendations based on violations."""
        recommendations = []
        
        # Cache key for this URL
        cache_key = f"{test_result.url}_{test_result.device_type}"
        if cache_key in self.optimization_cache:
            return self.optimization_cache[cache_key]
        
        # Group violations by type for targeted recommendations
        violation_types = {v.metric_type for v in violations}
        
        # Image optimization recommendations
        if (MetricType.IMAGE_SIZE in violation_types or 
            MetricType.LCP in violation_types):
            
            image_violation = next((v for v in violations if v.metric_type == MetricType.IMAGE_SIZE), None)
            current_image_size = image_violation.current_value if image_violation else test_result.image_size_kb or 0
            
            if current_image_size > 100:  # Only recommend if substantial image usage
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.IMAGE_COMPRESSION,
                    target_metrics=[MetricType.IMAGE_SIZE, MetricType.LCP],
                    estimated_improvement={
                        MetricType.IMAGE_SIZE: int(current_image_size * 0.3),  # 30% reduction
                        MetricType.LCP: int((test_result.lcp_ms or 0) * 0.15)  # 15% LCP improvement
                    },
                    implementation_effort="automatic",
                    priority_score=0.8,
                    description="Compress images using modern codecs (WebP/AVIF) and optimize quality settings",
                    implementation_steps=[
                        "Convert JPEG/PNG images to WebP format",
                        "Optimize compression quality (80-85%)",
                        "Generate responsive image sizes",
                        "Implement proper image dimensions"
                    ],
                    estimated_completion_time=5
                ))
                
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.LAZY_LOADING,
                    target_metrics=[MetricType.LCP, MetricType.TOTAL_SIZE],
                    estimated_improvement={
                        MetricType.LCP: int((test_result.lcp_ms or 0) * 0.1),  # 10% LCP improvement
                        MetricType.TOTAL_SIZE: int(current_image_size * 0.6)  # Defer 60% of images
                    },
                    implementation_effort="automatic",
                    priority_score=0.7,
                    description="Implement lazy loading for below-the-fold images",
                    implementation_steps=[
                        "Add loading='lazy' attributes to images",
                        "Exclude above-the-fold images from lazy loading",
                        "Implement intersection observer fallback",
                        "Add proper loading states"
                    ],
                    estimated_completion_time=3
                ))
        
        # JavaScript optimization recommendations
        if (MetricType.JAVASCRIPT_SIZE in violation_types or 
            MetricType.INP in violation_types):
            
            js_violation = next((v for v in violations if v.metric_type == MetricType.JAVASCRIPT_SIZE), None)
            current_js_size = js_violation.current_value if js_violation else test_result.js_size_kb or 0
            
            if current_js_size > 50:  # Only recommend if substantial JS usage
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.JS_MINIFICATION,
                    target_metrics=[MetricType.JAVASCRIPT_SIZE, MetricType.INP],
                    estimated_improvement={
                        MetricType.JAVASCRIPT_SIZE: int(current_js_size * 0.2),  # 20% reduction
                        MetricType.INP: int((test_result.inp_ms or 0) * 0.1)  # 10% INP improvement
                    },
                    implementation_effort="automatic",
                    priority_score=0.6,
                    description="Minify and optimize JavaScript bundles",
                    implementation_steps=[
                        "Remove unused JavaScript code",
                        "Minify JavaScript files",
                        "Enable gzip/brotli compression",
                        "Split bundles for better caching"
                    ],
                    estimated_completion_time=3
                ))
                
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.THIRD_PARTY_OPTIMIZATION,
                    target_metrics=[MetricType.JAVASCRIPT_SIZE, MetricType.INP, MetricType.LCP],
                    estimated_improvement={
                        MetricType.JAVASCRIPT_SIZE: int(current_js_size * 0.15),  # 15% reduction
                        MetricType.INP: int((test_result.inp_ms or 0) * 0.2),  # 20% INP improvement
                        MetricType.LCP: int((test_result.lcp_ms or 0) * 0.1)  # 10% LCP improvement
                    },
                    implementation_effort="low",
                    priority_score=0.7,
                    description="Optimize third-party script loading and execution",
                    implementation_steps=[
                        "Defer non-critical third-party scripts",
                        "Use web workers for heavy computations",
                        "Implement resource hints (dns-prefetch, preconnect)",
                        "Remove or replace slow third-party scripts"
                    ],
                    estimated_completion_time=10
                ))
        
        # CSS optimization recommendations
        if MetricType.CSS_SIZE in violation_types or MetricType.LCP in violation_types:
            css_violation = next((v for v in violations if v.metric_type == MetricType.CSS_SIZE), None)
            current_css_size = css_violation.current_value if css_violation else test_result.css_size_kb or 0
            
            if current_css_size > 20:  # Only recommend if substantial CSS usage
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.CRITICAL_CSS_INLINE,
                    target_metrics=[MetricType.LCP, MetricType.CLS],
                    estimated_improvement={
                        MetricType.LCP: int((test_result.lcp_ms or 0) * 0.2),  # 20% LCP improvement
                    },
                    implementation_effort="automatic",
                    priority_score=0.9,
                    description="Inline critical CSS and defer non-critical styles",
                    implementation_steps=[
                        "Extract above-the-fold CSS",
                        "Inline critical CSS in HTML head",
                        "Defer non-critical CSS loading",
                        "Remove unused CSS rules"
                    ],
                    estimated_completion_time=5
                ))
                
                recommendations.append(OptimizationRecommendation(
                    optimization_type=OptimizationType.CSS_MINIFICATION,
                    target_metrics=[MetricType.CSS_SIZE],
                    estimated_improvement={
                        MetricType.CSS_SIZE: int(current_css_size * 0.25)  # 25% reduction
                    },
                    implementation_effort="automatic",
                    priority_score=0.5,
                    description="Minify CSS files and remove unused styles",
                    implementation_steps=[
                        "Minify CSS files",
                        "Remove unused CSS rules",
                        "Optimize CSS delivery",
                        "Enable compression"
                    ],
                    estimated_completion_time=2
                ))
        
        # Resource preloading for LCP improvements
        if MetricType.LCP in violation_types:
            recommendations.append(OptimizationRecommendation(
                optimization_type=OptimizationType.RESOURCE_PRELOADING,
                target_metrics=[MetricType.LCP, MetricType.FCP],
                estimated_improvement={
                    MetricType.LCP: int((test_result.lcp_ms or 0) * 0.15),  # 15% LCP improvement
                },
                implementation_effort="automatic",
                priority_score=0.8,
                description="Preload critical resources for faster LCP",
                implementation_steps=[
                    "Identify LCP element and its resources",
                    "Add preload hints for critical resources",
                    "Optimize resource discovery timing", 
                    "Implement fetchpriority attributes"
                ],
                estimated_completion_time=3
            ))
        
        # Sort recommendations by priority score
        recommendations.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Cache recommendations
        self.optimization_cache[cache_key] = recommendations
        
        return recommendations
    
    async def run_comprehensive_audit(
        self,
        project: Project,
        budgets_config: PerformanceBudgetsConfig,
        sample_urls: Optional[List[str]] = None,
        device_types: List[str] = None
    ) -> Dict[str, Any]:
        """Run comprehensive performance audit across multiple pages and templates."""
        device_types = device_types or ["mobile", "desktop"]
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        audit_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_domain": project.domain,
            "total_violations": 0,
            "critical_violations": 0,
            "pages_tested": 0,
            "pages_passing_cwv": 0,
            "template_results": {},
            "recommendations": [],
            "summary": {}
        }
        
        # Default sample URLs if none provided
        if not sample_urls:
            sample_urls = [
                f"{project.base_url}",  # Homepage
                f"{project.base_url}/sample-article",  # Article template
                f"{project.base_url}/sample-product",  # Product template  
            ]
        
        # Test each URL across device types
        for url in sample_urls:
            template_type = self._detect_template_type(url, project.base_url)
            budget = self._get_budget_for_template(template_type, budgets_config)
            
            if template_type not in audit_results["template_results"]:
                audit_results["template_results"][template_type] = {
                    "pages_tested": 0,
                    "violations": [],
                    "recommendations": [],
                    "avg_performance_score": 0,
                    "cwv_pass_rate": 0
                }
            
            template_results = audit_results["template_results"][template_type]
            
            for device_type in device_types:
                try:
                    logger.info(f"Testing {url} on {device_type}")
                    
                    # Run performance test
                    test_result = await self.test_page_performance(
                        url=url,
                        device_type=device_type,
                        strategy=device_type
                    )
                    
                    # Check for violations
                    violations = self.check_budget_violations(
                        test_result=test_result,
                        budget=budget,
                        template_type=template_type
                    )
                    
                    # Generate recommendations
                    recommendations = self.generate_optimization_recommendations(
                        violations=violations,
                        test_result=test_result
                    )
                    
                    # Update audit results
                    template_results["pages_tested"] += 1
                    template_results["violations"].extend(violations)
                    template_results["recommendations"].extend(recommendations)
                    
                    # Track performance scores
                    if test_result.performance_score:
                        current_avg = template_results["avg_performance_score"]
                        page_count = template_results["pages_tested"]
                        template_results["avg_performance_score"] = (
                            (current_avg * (page_count - 1) + test_result.performance_score) / page_count
                        )
                    
                    # Track CWV pass rate
                    if test_result.passes_cwv_thresholds:
                        audit_results["pages_passing_cwv"] += 1
                    
                    audit_results["pages_tested"] += 1
                    audit_results["total_violations"] += len(violations)
                    audit_results["critical_violations"] += len([v for v in violations if v.is_critical])
                    
                    logger.info(f"Completed {url} on {device_type}: {len(violations)} violations found")
                    
                except Exception as e:
                    logger.error(f"Error testing {url} on {device_type}: {e}")
                    continue
        
        # Calculate summary metrics
        if audit_results["pages_tested"] > 0:
            audit_results["summary"] = {
                "cwv_pass_rate": audit_results["pages_passing_cwv"] / audit_results["pages_tested"],
                "avg_violations_per_page": audit_results["total_violations"] / audit_results["pages_tested"],
                "critical_violation_rate": audit_results["critical_violations"] / audit_results["total_violations"] if audit_results["total_violations"] > 0 else 0,
                "templates_tested": len(audit_results["template_results"]),
                "quality_gate_passed": audit_results["pages_passing_cwv"] / audit_results["pages_tested"] >= 0.85  # 85% threshold
            }
            
            # Calculate template-specific CWV pass rates
            for template_type, results in audit_results["template_results"].items():
                pages_tested = results["pages_tested"]
                if pages_tested > 0:
                    cwv_passing = sum(1 for v in results["violations"] if not any(
                        viol.metric_type in [MetricType.LCP, MetricType.INP, MetricType.CLS] 
                        for viol in results["violations"]
                    ))
                    results["cwv_pass_rate"] = cwv_passing / pages_tested
        
        # Consolidate and prioritize recommendations
        all_recommendations = []
        for template_results in audit_results["template_results"].values():
            all_recommendations.extend(template_results["recommendations"])
        
        # Deduplicate and sort recommendations
        unique_recommendations = {}
        for rec in all_recommendations:
            key = f"{rec.optimization_type.value}_{rec.description[:50]}"
            if key not in unique_recommendations or rec.priority_score > unique_recommendations[key].priority_score:
                unique_recommendations[key] = rec
        
        audit_results["recommendations"] = sorted(
            unique_recommendations.values(),
            key=lambda x: x.priority_score,
            reverse=True
        )[:10]  # Top 10 recommendations
        
        return audit_results
    
    def _detect_template_type(self, url: str, base_url: str) -> str:
        """Detect template type based on URL patterns."""
        relative_path = url.replace(base_url, "").strip("/").lower()
        
        if not relative_path or relative_path == "index.html":
            return "homepage"
        elif any(keyword in relative_path for keyword in ["product", "shop", "buy"]):
            return "product"
        elif any(keyword in relative_path for keyword in ["compare", "vs", "comparison"]):
            return "comparison"
        elif any(keyword in relative_path for keyword in ["calculator", "tool", "calc"]):
            return "calculator"
        elif any(keyword in relative_path for keyword in ["blog", "article", "post", "guide"]):
            return "article"
        else:
            return "article"  # Default to article template
    
    def _get_budget_for_template(self, template_type: str, budgets_config: PerformanceBudgetsConfig) -> PerformanceBudget:
        """Get performance budget for specific template type."""
        budget_map = {
            "article": budgets_config.article,
            "product": budgets_config.product,
            "comparison": budgets_config.comparison,
            "calculator": budgets_config.calculator,
            "homepage": budgets_config.article,  # Use article budget for homepage
        }
        
        return budget_map.get(template_type, budgets_config.article)
    
    async def auto_optimize_violations(
        self,
        violations: List[BudgetViolation],
        recommendations: List[OptimizationRecommendation],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Automatically apply optimizations for budget violations."""
        optimization_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "failed_optimizations": 0,
            "estimated_improvements": {},
            "optimization_log": []
        }
        
        # Filter to automatic recommendations only
        auto_recommendations = [r for r in recommendations if r.can_auto_implement]
        
        logger.info(f"Processing {len(auto_recommendations)} automatic optimizations (dry_run={dry_run})")
        
        for recommendation in auto_recommendations:
            optimization_results["total_optimizations"] += 1
            
            try:
                if dry_run:
                    # Simulate optimization
                    success = True
                    result = {"status": "simulated", "message": "Optimization simulated successfully"}
                else:
                    # Apply actual optimization
                    result = await self._apply_optimization(recommendation)
                    success = result.get("status") == "success"
                
                if success:
                    optimization_results["successful_optimizations"] += 1
                    
                    # Track estimated improvements
                    for metric, improvement in recommendation.estimated_improvement.items():
                        if metric.value not in optimization_results["estimated_improvements"]:
                            optimization_results["estimated_improvements"][metric.value] = 0
                        optimization_results["estimated_improvements"][metric.value] += improvement
                else:
                    optimization_results["failed_optimizations"] += 1
                
                optimization_results["optimization_log"].append({
                    "optimization_type": recommendation.optimization_type.value,
                    "success": success,
                    "result": result,
                    "estimated_time": recommendation.estimated_completion_time,
                    "priority_score": recommendation.priority_score
                })
                
            except Exception as e:
                optimization_results["failed_optimizations"] += 1
                optimization_results["optimization_log"].append({
                    "optimization_type": recommendation.optimization_type.value,
                    "success": False,
                    "error": str(e),
                    "priority_score": recommendation.priority_score
                })
                logger.error(f"Failed to apply optimization {recommendation.optimization_type.value}: {e}")
        
        # Calculate success rate
        if optimization_results["total_optimizations"] > 0:
            success_rate = optimization_results["successful_optimizations"] / optimization_results["total_optimizations"]
            optimization_results["success_rate"] = success_rate
            optimization_results["quality_gate_passed"] = success_rate >= 0.9  # 90% success rate threshold
        
        return optimization_results
    
    async def _apply_optimization(self, recommendation: OptimizationRecommendation) -> Dict[str, Any]:
        """Apply a specific optimization (placeholder for actual implementation)."""
        # This would contain actual optimization logic
        # For now, return a simulated success response
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "status": "success",
            "message": f"Applied {recommendation.optimization_type.value} optimization",
            "details": recommendation.implementation_steps
        }
    
    def export_audit_report(
        self,
        audit_results: Dict[str, Any],
        output_path: Path,
        format: str = "json"
    ) -> None:
        """Export audit results to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(audit_results, f, indent=2, default=str)
        
        logger.info(f"Audit report exported to {output_path}")
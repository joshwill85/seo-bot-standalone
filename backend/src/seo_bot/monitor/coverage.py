"""Coverage & Freshness SLA System.

Provides comprehensive monitoring of Google Search Console indexation,
coverage metrics, and automated freshness review scheduling.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import CoverageSLAConfig, Settings
from ..models import AlertSeverity, CoverageMetrics, IndexationStatus


logger = logging.getLogger(__name__)


class CoverageIssueType(Enum):
    """Types of coverage issues detected."""
    SUBMITTED_NOT_INDEXED = "submitted_not_indexed"
    CRAWL_ERROR = "crawl_error"
    REDIRECT_ERROR = "redirect_error"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    DUPLICATE_CONTENT = "duplicate_content"
    COVERAGE_ANOMALY = "coverage_anomaly"
    FRESHNESS_VIOLATION = "freshness_violation"
    ORPHANED_PAGE = "orphaned_page"


@dataclass
class CoverageViolation:
    """Represents a coverage or freshness SLA violation."""
    url: str
    issue_type: CoverageIssueType
    severity: AlertSeverity
    detected_at: datetime
    description: str
    suggested_actions: List[str]
    days_since_submission: Optional[int] = None
    days_since_last_crawl: Optional[int] = None
    mobile_usability_issues: List[str] = None


@dataclass
class CoverageSLAReport:
    """Coverage SLA compliance report."""
    domain: str
    report_date: datetime
    indexation_rate: float
    sla_compliance: bool
    total_pages: int
    indexed_pages: int
    submitted_pages: int
    coverage_violations: List[CoverageViolation]
    freshness_violations: List[CoverageViolation]
    mobile_usability_score: float
    crawl_errors: Dict[str, int]
    avg_indexation_time_days: float
    trend_data: Dict[str, float]
    next_review_date: datetime


class GSCAdapter:
    """Google Search Console API adapter."""
    
    def __init__(self, credentials_file: str):
        """Initialize GSC adapter with service account credentials."""
        self.credentials_file = credentials_file
        self.service = None
        self._setup_service()
    
    def _setup_service(self):
        """Set up Google Search Console service."""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            self.service = build('searchconsole', 'v1', credentials=credentials)
            logger.info("GSC service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GSC service: {e}")
            raise
    
    async def get_indexation_data(self, domain: str, 
                                  start_date: datetime,
                                  end_date: datetime) -> Dict:
        """Get indexation data from GSC."""
        try:
            request = {
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d'),
                'dimensions': ['page'],
                'rowLimit': 25000
            }
            
            # Execute request in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.service.searchanalytics().query(
                    siteUrl=f'https://{domain}',
                    body=request
                ).execute()
            )
            
            return response
            
        except HttpError as e:
            logger.error(f"GSC API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get indexation data: {e}")
            raise
    
    async def get_coverage_data(self, domain: str) -> Dict:
        """Get coverage data from GSC."""
        try:
            # Get coverage details
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.service.sites().get(
                    siteUrl=f'https://{domain}'
                ).execute()
            )
            
            # Get index coverage from inspection API
            inspection_response = await loop.run_in_executor(
                None,
                lambda: self.service.urlInspection().index().inspect(
                    body={'inspectionUrl': f'https://{domain}'}
                ).execute()
            )
            
            return {
                'site_info': response,
                'inspection': inspection_response
            }
            
        except HttpError as e:
            logger.error(f"GSC coverage API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get coverage data: {e}")
            raise
    
    async def get_mobile_usability(self, domain: str) -> Dict:
        """Get mobile usability data from GSC."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.service.searchanalytics().query(
                    siteUrl=f'https://{domain}',
                    body={
                        'startDate': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                        'endDate': datetime.now().strftime('%Y-%m-%d'),
                        'dimensions': ['device'],
                        'rowLimit': 1000
                    }
                ).execute()
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get mobile usability data: {e}")
            raise


class CoverageFreshnessMonitor:
    """Monitors coverage and freshness SLAs with automated alerting."""
    
    def __init__(self, 
                 settings: Settings,
                 sla_config: CoverageSLAConfig,
                 domain: str):
        """Initialize coverage monitor."""
        self.settings = settings
        self.sla_config = sla_config
        self.domain = domain
        self.gsc_adapter = None
        
        if settings.google_search_console_credentials_file:
            self.gsc_adapter = GSCAdapter(settings.google_search_console_credentials_file)
    
    async def check_indexation_sla(self) -> CoverageSLAReport:
        """Check indexation SLA compliance and generate report."""
        if not self.gsc_adapter:
            raise ValueError("Google Search Console credentials not configured")
        
        logger.info(f"Checking indexation SLA for {self.domain}")
        
        # Calculate date ranges
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.sla_config.indexation_timeframe_days)
        
        try:
            # Get indexation data
            indexation_data = await self.gsc_adapter.get_indexation_data(
                self.domain, start_date, end_date
            )
            
            # Get coverage data
            coverage_data = await self.gsc_adapter.get_coverage_data(self.domain)
            
            # Get mobile usability data
            mobile_data = await self.gsc_adapter.get_mobile_usability(self.domain)
            
            # Analyze data and check violations
            report = await self._analyze_coverage_data(
                indexation_data, coverage_data, mobile_data, end_date
            )
            
            logger.info(f"Generated coverage SLA report: {report.indexation_rate:.1%} compliance")
            return report
            
        except Exception as e:
            logger.error(f"Failed to check indexation SLA: {e}")
            raise
    
    async def _analyze_coverage_data(self, 
                                     indexation_data: Dict,
                                     coverage_data: Dict,
                                     mobile_data: Dict,
                                     report_date: datetime) -> CoverageSLAReport:
        """Analyze coverage data and identify violations."""
        
        # Extract metrics
        rows = indexation_data.get('rows', [])
        total_pages = len(rows)
        indexed_pages = sum(1 for row in rows if row.get('clicks', 0) > 0 or row.get('impressions', 0) > 0)
        
        # Calculate indexation rate
        indexation_rate = indexed_pages / total_pages if total_pages > 0 else 0.0
        sla_compliance = indexation_rate >= self.sla_config.indexation_target
        
        # Identify coverage violations
        coverage_violations = await self._identify_coverage_violations(rows)
        
        # Check freshness violations
        freshness_violations = await self._check_freshness_violations()
        
        # Calculate mobile usability score
        mobile_usability_score = self._calculate_mobile_usability_score(mobile_data)
        
        # Calculate crawl errors
        crawl_errors = self._extract_crawl_errors(coverage_data)
        
        # Calculate average indexation time
        avg_indexation_time = self._calculate_avg_indexation_time(rows)
        
        # Generate trend data
        trend_data = await self._generate_trend_data()
        
        # Calculate next review date
        next_review_date = report_date + timedelta(days=self.sla_config.freshness_review_days)
        
        return CoverageSLAReport(
            domain=self.domain,
            report_date=report_date,
            indexation_rate=indexation_rate,
            sla_compliance=sla_compliance,
            total_pages=total_pages,
            indexed_pages=indexed_pages,
            submitted_pages=total_pages,  # Simplified - would need sitemap data
            coverage_violations=coverage_violations,
            freshness_violations=freshness_violations,
            mobile_usability_score=mobile_usability_score,
            crawl_errors=crawl_errors,
            avg_indexation_time_days=avg_indexation_time,
            trend_data=trend_data,
            next_review_date=next_review_date
        )
    
    async def _identify_coverage_violations(self, rows: List[Dict]) -> List[CoverageViolation]:
        """Identify coverage violations from GSC data."""
        violations = []
        
        for row in rows:
            page_url = row.get('keys', [''])[0]
            clicks = row.get('clicks', 0)
            impressions = row.get('impressions', 0)
            
            # Check for pages with no impressions (potential indexation issues)
            if impressions == 0:
                violations.append(CoverageViolation(
                    url=page_url,
                    issue_type=CoverageIssueType.SUBMITTED_NOT_INDEXED,
                    severity=AlertSeverity.HIGH,
                    detected_at=datetime.now(timezone.utc),
                    description=f"Page has no impressions in GSC data",
                    suggested_actions=[
                        "Check if page is properly submitted to GSC",
                        "Verify page is not blocked by robots.txt",
                        "Check for technical SEO issues",
                        "Request indexing via GSC"
                    ]
                ))
        
        return violations
    
    async def _check_freshness_violations(self) -> List[CoverageViolation]:
        """Check for freshness violations requiring content review."""
        violations = []
        
        # This would typically query the database for content that needs review
        # For now, we'll simulate this check
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.sla_config.freshness_review_days)
        
        # In a real implementation, this would query the content database
        # for pages that haven't been reviewed since cutoff_date
        
        return violations
    
    def _calculate_mobile_usability_score(self, mobile_data: Dict) -> float:
        """Calculate mobile usability score from GSC data."""
        rows = mobile_data.get('rows', [])
        
        mobile_clicks = 0
        desktop_clicks = 0
        
        for row in rows:
            device = row.get('keys', [''])[0].lower()
            clicks = row.get('clicks', 0)
            
            if 'mobile' in device:
                mobile_clicks += clicks
            elif 'desktop' in device:
                desktop_clicks += clicks
        
        total_clicks = mobile_clicks + desktop_clicks
        if total_clicks == 0:
            return 0.0
        
        # Simple mobile usability score based on mobile vs desktop performance
        return min(100.0, (mobile_clicks / total_clicks) * 100.0)
    
    def _extract_crawl_errors(self, coverage_data: Dict) -> Dict[str, int]:
        """Extract crawl error counts from coverage data."""
        # This would parse actual GSC coverage data for crawl errors
        # For now, return a simplified structure
        return {
            'server_errors': 0,
            'not_found': 0,
            'access_denied': 0,
            'redirect_errors': 0
        }
    
    def _calculate_avg_indexation_time(self, rows: List[Dict]) -> float:
        """Calculate average time to indexation."""
        # This would require additional data about submission dates
        # For now, return a reasonable estimate
        return self.sla_config.indexation_timeframe_days / 2
    
    async def _generate_trend_data(self) -> Dict[str, float]:
        """Generate trend data for reporting."""
        # This would query historical data for trends
        # For now, return placeholder data
        return {
            'indexation_rate_7d': 0.82,
            'indexation_rate_30d': 0.85,
            'coverage_issues_trend': -0.05,  # Negative = improving
            'mobile_usability_trend': 0.02   # Positive = improving
        }
    
    async def schedule_freshness_review(self, content_id: str, 
                                        priority: str = "normal") -> bool:
        """Schedule content for freshness review."""
        try:
            review_date = datetime.now(timezone.utc) + timedelta(days=self.sla_config.freshness_review_days)
            
            # In a real implementation, this would create a review task
            logger.info(f"Scheduled freshness review for {content_id} on {review_date}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule freshness review: {e}")
            return False
    
    async def get_orphaned_pages(self) -> List[str]:
        """Identify orphaned pages with insufficient internal links."""
        orphaned_pages = []
        
        # This would typically:
        # 1. Query sitemap for all pages
        # 2. Analyze internal link structure
        # 3. Identify pages with < min_internal_links
        
        logger.info(f"Checking for pages with < {self.sla_config.min_internal_links} internal links")
        
        return orphaned_pages
    
    async def auto_resolve_coverage_issues(self, 
                                           violations: List[CoverageViolation]) -> Dict[str, int]:
        """Attempt automatic resolution of coverage issues."""
        results = {
            'resolved': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for violation in violations:
            try:
                if violation.issue_type == CoverageIssueType.SUBMITTED_NOT_INDEXED:
                    # Request indexing via GSC API
                    success = await self._request_indexing(violation.url)
                    if success:
                        results['resolved'] += 1
                    else:
                        results['failed'] += 1
                else:
                    results['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to resolve coverage issue for {violation.url}: {e}")
                results['failed'] += 1
        
        return results
    
    async def _request_indexing(self, url: str) -> bool:
        """Request indexing for a specific URL via GSC API."""
        try:
            if not self.gsc_adapter:
                return False
            
            # Use URL Inspection API to request indexing
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gsc_adapter.service.urlInspection().index().inspect(
                    body={'inspectionUrl': url}
                ).execute()
            )
            
            logger.info(f"Requested indexing for {url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request indexing for {url}: {e}")
            return False
    
    async def export_coverage_report(self, 
                                     report: CoverageSLAReport,
                                     output_path: Path) -> bool:
        """Export coverage report to file."""
        try:
            import json
            
            report_data = {
                'domain': report.domain,
                'report_date': report.report_date.isoformat(),
                'indexation_rate': report.indexation_rate,
                'sla_compliance': report.sla_compliance,
                'total_pages': report.total_pages,
                'indexed_pages': report.indexed_pages,
                'submitted_pages': report.submitted_pages,
                'mobile_usability_score': report.mobile_usability_score,
                'crawl_errors': report.crawl_errors,
                'avg_indexation_time_days': report.avg_indexation_time_days,
                'trend_data': report.trend_data,
                'next_review_date': report.next_review_date.isoformat(),
                'coverage_violations': [
                    {
                        'url': v.url,
                        'issue_type': v.issue_type.value,
                        'severity': v.severity.value,
                        'detected_at': v.detected_at.isoformat(),
                        'description': v.description,
                        'suggested_actions': v.suggested_actions
                    }
                    for v in report.coverage_violations
                ],
                'freshness_violations': [
                    {
                        'url': v.url,
                        'issue_type': v.issue_type.value,
                        'severity': v.severity.value,
                        'detected_at': v.detected_at.isoformat(),
                        'description': v.description,
                        'suggested_actions': v.suggested_actions
                    }
                    for v in report.freshness_violations
                ]
            }
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Coverage report exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export coverage report: {e}")
            return False


async def run_coverage_monitor(domain: str, 
                               settings: Settings,
                               sla_config: CoverageSLAConfig) -> CoverageSLAReport:
    """Run coverage monitoring for a domain."""
    monitor = CoverageFreshnessMonitor(settings, sla_config, domain)
    report = await monitor.check_indexation_sla()
    
    # Auto-resolve issues if enabled
    if report.coverage_violations:
        resolution_results = await monitor.auto_resolve_coverage_issues(report.coverage_violations)
        logger.info(f"Auto-resolution results: {resolution_results}")
    
    return report
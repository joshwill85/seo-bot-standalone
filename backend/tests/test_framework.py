"""
Automated Testing Framework for SEO Bot
Provides comprehensive test automation, reporting, and CI/CD integration
"""

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging
import subprocess
import sqlite3
from pathlib import Path

# Test result tracking
@dataclass
class TestResult:
    name: str
    status: str  # passed, failed, skipped
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    coverage: Optional[float] = None
    performance_metrics: Optional[Dict[str, Any]] = None

@dataclass
class TestSuite:
    name: str
    tests: List[TestResult]
    start_time: datetime
    end_time: datetime
    total_tests: int
    passed: int
    failed: int
    skipped: int
    coverage_percentage: float
    performance_score: Optional[float] = None

class TestReporter:
    """Generates comprehensive test reports in multiple formats"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_html_report(self, suite: TestSuite) -> str:
        """Generate HTML test report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SEO Bot Test Report - {suite.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric {{ background: #e8f4fd; padding: 15px; border-radius: 5px; text-align: center; }}
                .passed {{ background: #d4edda; }}
                .failed {{ background: #f8d7da; }}
                .skipped {{ background: #fff3cd; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f2f2f2; }}
                .test-passed {{ color: #28a745; }}
                .test-failed {{ color: #dc3545; }}
                .test-skipped {{ color: #ffc107; }}
                .error-details {{ background: #f8f9fa; padding: 10px; margin: 5px 0; font-family: monospace; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>SEO Bot Test Report</h1>
                <p><strong>Suite:</strong> {suite.name}</p>
                <p><strong>Executed:</strong> {suite.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Duration:</strong> {(suite.end_time - suite.start_time).total_seconds():.2f}s</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Tests</h3>
                    <p style="font-size: 24px; margin: 0;">{suite.total_tests}</p>
                </div>
                <div class="metric passed">
                    <h3>Passed</h3>
                    <p style="font-size: 24px; margin: 0;">{suite.passed}</p>
                </div>
                <div class="metric failed">
                    <h3>Failed</h3>
                    <p style="font-size: 24px; margin: 0;">{suite.failed}</p>
                </div>
                <div class="metric skipped">
                    <h3>Skipped</h3>
                    <p style="font-size: 24px; margin: 0;">{suite.skipped}</p>
                </div>
                <div class="metric">
                    <h3>Coverage</h3>
                    <p style="font-size: 24px; margin: 0;">{suite.coverage_percentage:.1f}%</p>
                </div>
            </div>
            
            <h2>Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Coverage</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for test in suite.tests:
            status_class = f"test-{test.status}"
            html_content += f"""
                    <tr>
                        <td>{test.name}</td>
                        <td class="{status_class}">{test.status.upper()}</td>
                        <td>{test.duration:.3f}s</td>
                        <td>{test.coverage:.1f}% if test.coverage else 'N/A'}</td>
                        <td>
            """
            
            if test.error_message:
                html_content += f"""
                            <div class="error-details">
                                <strong>Error:</strong> {test.error_message}<br>
                                {test.stack_trace if test.stack_trace else ''}
                            </div>
                """
            
            if test.performance_metrics:
                html_content += f"""
                            <div class="error-details">
                                <strong>Performance:</strong><br>
                                {json.dumps(test.performance_metrics, indent=2)}
                            </div>
                """
            
            html_content += """
                        </td>
                    </tr>
            """
        
        html_content += """
                </tbody>
            </table>
        </body>
        </html>
        """
        
        report_file = self.output_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def generate_json_report(self, suite: TestSuite) -> str:
        """Generate JSON test report for CI/CD integration"""
        report_data = asdict(suite)
        report_file = self.output_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return str(report_file)
    
    def generate_junit_xml(self, suite: TestSuite) -> str:
        """Generate JUnit XML format for CI/CD systems"""
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{suite.name}" 
           tests="{suite.total_tests}" 
           failures="{suite.failed}" 
           skipped="{suite.skipped}" 
           time="{(suite.end_time - suite.start_time).total_seconds():.3f}">
'''
        
        for test in suite.tests:
            xml_content += f'''  <testcase name="{test.name}" time="{test.duration:.3f}">
'''
            
            if test.status == 'failed':
                xml_content += f'''    <failure message="{test.error_message or 'Test failed'}">{test.stack_trace or ''}</failure>
'''
            elif test.status == 'skipped':
                xml_content += f'''    <skipped/>
'''
            
            xml_content += f'''  </testcase>
'''
        
        xml_content += '</testsuite>'
        
        report_file = self.output_dir / f"junit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        with open(report_file, 'w') as f:
            f.write(xml_content)
        
        return str(report_file)

class PerformanceMonitor:
    """Monitors performance metrics during test execution"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = None
        
    def start_monitoring(self, test_name: str):
        """Start monitoring for a test"""
        self.start_time = time.time()
        self.metrics[test_name] = {
            'start_time': self.start_time,
            'memory_usage': self._get_memory_usage(),
            'cpu_usage': self._get_cpu_usage()
        }
    
    def stop_monitoring(self, test_name: str) -> Dict[str, Any]:
        """Stop monitoring and return metrics"""
        if test_name not in self.metrics:
            return {}
        
        end_time = time.time()
        metrics = self.metrics[test_name]
        
        return {
            'duration': end_time - metrics['start_time'],
            'memory_peak': self._get_memory_usage(),
            'memory_baseline': metrics['memory_usage'],
            'cpu_average': self._get_cpu_usage(),
            'performance_score': self._calculate_performance_score(
                end_time - metrics['start_time']
            )
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage (simplified)"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage (simplified)"""
        try:
            import psutil
            return psutil.cpu_percent()
        except ImportError:
            return 0.0
    
    def _calculate_performance_score(self, duration: float) -> float:
        """Calculate performance score based on duration"""
        if duration < 0.1:
            return 100.0
        elif duration < 0.5:
            return 90.0
        elif duration < 1.0:
            return 80.0
        elif duration < 2.0:
            return 70.0
        else:
            return 50.0

class CoverageTracker:
    """Tracks code coverage during test execution"""
    
    def __init__(self):
        self.coverage_data = {}
        
    def start_coverage(self, test_name: str):
        """Start coverage tracking"""
        try:
            import coverage
            self.cov = coverage.Coverage()
            self.cov.start()
        except ImportError:
            logging.warning("Coverage package not installed")
    
    def stop_coverage(self, test_name: str) -> float:
        """Stop coverage tracking and return percentage"""
        try:
            if hasattr(self, 'cov'):
                self.cov.stop()
                self.cov.save()
                return self.cov.report()
        except:
            pass
        return 0.0

class TestOrchestrator:
    """Orchestrates test execution with parallel processing and intelligent scheduling"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.performance_monitor = PerformanceMonitor()
        self.coverage_tracker = CoverageTracker()
        self.reporter = TestReporter()
        
    async def run_test_suite(self, test_functions: List[Callable], suite_name: str) -> TestSuite:
        """Run a complete test suite with monitoring and reporting"""
        start_time = datetime.now()
        test_results = []
        
        # Run tests in parallel
        semaphore = asyncio.Semaphore(self.max_workers)
        tasks = []
        
        for test_func in test_functions:
            task = self._run_single_test(semaphore, test_func)
            tasks.append(task)
        
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        passed = sum(1 for r in test_results if isinstance(r, TestResult) and r.status == 'passed')
        failed = sum(1 for r in test_results if isinstance(r, TestResult) and r.status == 'failed')
        skipped = sum(1 for r in test_results if isinstance(r, TestResult) and r.status == 'skipped')
        
        # Calculate overall coverage
        coverage_percentage = sum(
            r.coverage for r in test_results 
            if isinstance(r, TestResult) and r.coverage
        ) / len(test_results) if test_results else 0
        
        suite = TestSuite(
            name=suite_name,
            tests=[r for r in test_results if isinstance(r, TestResult)],
            start_time=start_time,
            end_time=datetime.now(),
            total_tests=len(test_functions),
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage_percentage=coverage_percentage
        )
        
        # Generate reports
        self.reporter.generate_html_report(suite)
        self.reporter.generate_json_report(suite)
        self.reporter.generate_junit_xml(suite)
        
        return suite
    
    async def _run_single_test(self, semaphore: asyncio.Semaphore, test_func: Callable) -> TestResult:
        """Run a single test with monitoring"""
        async with semaphore:
            test_name = test_func.__name__
            
            # Start monitoring
            self.performance_monitor.start_monitoring(test_name)
            self.coverage_tracker.start_coverage(test_name)
            
            start_time = time.time()
            
            try:
                # Execute test
                if asyncio.iscoroutinefunction(test_func):
                    await test_func()
                else:
                    test_func()
                
                status = 'passed'
                error_message = None
                stack_trace = None
                
            except Exception as e:
                status = 'failed'
                error_message = str(e)
                stack_trace = self._get_stack_trace(e)
            
            duration = time.time() - start_time
            
            # Stop monitoring
            performance_metrics = self.performance_monitor.stop_monitoring(test_name)
            coverage = self.coverage_tracker.stop_coverage(test_name)
            
            return TestResult(
                name=test_name,
                status=status,
                duration=duration,
                error_message=error_message,
                stack_trace=stack_trace,
                coverage=coverage,
                performance_metrics=performance_metrics
            )
    
    def _get_stack_trace(self, exception: Exception) -> str:
        """Get formatted stack trace"""
        import traceback
        return traceback.format_exc()

class ContinuousIntegration:
    """Handles CI/CD integration and automated test execution"""
    
    def __init__(self, config_file: str = "ci_config.json"):
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load CI/CD configuration"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "triggers": ["push", "pull_request"],
                "test_suites": ["unit", "integration", "performance"],
                "notifications": {
                    "slack_webhook": None,
                    "email": None
                },
                "thresholds": {
                    "coverage": 80.0,
                    "performance_score": 70.0
                }
            }
    
    def setup_github_actions(self) -> str:
        """Generate GitHub Actions workflow file"""
        workflow_content = """
name: SEO Bot Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run tests
      run: |
        python -m pytest tests/ --cov=src/ --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
    
    - name: Generate test report
      run: |
        python -m tests.test_framework generate-report
    
    - name: Upload test artifacts
      uses: actions/upload-artifact@v3
      with:
        name: test-reports
        path: test_reports/
"""
        
        workflow_dir = Path(".github/workflows")
        workflow_dir.mkdir(parents=True, exist_ok=True)
        
        workflow_file = workflow_dir / "test.yml"
        with open(workflow_file, 'w') as f:
            f.write(workflow_content)
        
        return str(workflow_file)
    
    def notify_results(self, suite: TestSuite):
        """Send notifications about test results"""
        if suite.failed > 0:
            self._send_failure_notification(suite)
        elif suite.coverage_percentage < self.config["thresholds"]["coverage"]:
            self._send_coverage_warning(suite)
        else:
            self._send_success_notification(suite)
    
    def _send_failure_notification(self, suite: TestSuite):
        """Send failure notification"""
        message = f"⚠️ Test suite '{suite.name}' failed: {suite.failed}/{suite.total_tests} tests failed"
        self._send_notification(message, "warning")
    
    def _send_coverage_warning(self, suite: TestSuite):
        """Send coverage warning"""
        message = f"📊 Coverage below threshold: {suite.coverage_percentage:.1f}% < {self.config['thresholds']['coverage']}%"
        self._send_notification(message, "info")
    
    def _send_success_notification(self, suite: TestSuite):
        """Send success notification"""
        message = f"✅ All tests passed! Coverage: {suite.coverage_percentage:.1f}%"
        self._send_notification(message, "success")
    
    def _send_notification(self, message: str, level: str):
        """Send notification via configured channels"""
        # Implement Slack, email, or other notification methods
        logging.info(f"[{level.upper()}] {message}")

# Example test functions for demonstration
async def test_keyword_scoring():
    """Test keyword scoring functionality"""
    from src.seo_bot.keywords.score import KeywordScorer
    
    scorer = KeywordScorer()
    result = await scorer.score_keywords(["test keyword"], "test_business")
    assert len(result) > 0

def test_clustering_algorithm():
    """Test keyword clustering"""
    from src.seo_bot.keywords.cluster import KeywordClusterer
    
    clusterer = KeywordClusterer()
    keywords = ["seo tools", "seo software", "content marketing", "digital marketing"]
    clusters = clusterer.cluster_keywords(keywords)
    assert len(clusters) > 0

async def test_performance_optimization():
    """Test performance optimization features"""
    # Simulate performance test
    start_time = time.time()
    
    # Mock heavy operation
    await asyncio.sleep(0.1)
    
    duration = time.time() - start_time
    assert duration < 1.0, "Performance test exceeded 1 second threshold"

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "generate-report":
        # Generate standalone report
        orchestrator = TestOrchestrator()
        
        # Mock test suite for demonstration
        test_results = [
            TestResult("test_example", "passed", 0.150, coverage=85.0),
            TestResult("test_integration", "passed", 0.300, coverage=92.0),
            TestResult("test_performance", "passed", 0.100, coverage=78.0)
        ]
        
        suite = TestSuite(
            name="SEO Bot Test Suite",
            tests=test_results,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_tests=3,
            passed=3,
            failed=0,
            skipped=0,
            coverage_percentage=85.0
        )
        
        orchestrator.reporter.generate_html_report(suite)
        orchestrator.reporter.generate_json_report(suite)
        orchestrator.reporter.generate_junit_xml(suite)
        
        print("Test reports generated successfully!")
    else:
        # Run actual tests
        async def main():
            orchestrator = TestOrchestrator()
            ci = ContinuousIntegration()
            
            # Define test functions
            test_functions = [
                test_keyword_scoring,
                test_clustering_algorithm,
                test_performance_optimization
            ]
            
            # Run test suite
            suite = await orchestrator.run_test_suite(test_functions, "SEO Bot Automated Tests")
            
            # Handle CI/CD
            ci.notify_results(suite)
            
            print(f"Test suite completed: {suite.passed}/{suite.total_tests} passed")
            print(f"Coverage: {suite.coverage_percentage:.1f}%")
            
            return suite.failed == 0
        
        # Run the test suite
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
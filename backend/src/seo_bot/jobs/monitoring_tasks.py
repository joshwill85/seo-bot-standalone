"""Background tasks for monitoring and system maintenance."""

import time
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from celery import Task
from ..jobs import celery_app

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task class with callbacks."""
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Monitoring task {task_id} succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Monitoring task {task_id} failed: {exc}")


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.monitoring_tasks.check_keyword_rankings')
def check_keyword_rankings(self) -> Dict[str, Any]:
    """
    Periodic task to check keyword rankings for all active projects.
    
    Returns:
        Summary of ranking checks performed
    """
    try:
        logger.info("Starting periodic keyword ranking checks")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Loading active projects...'}
        )
        
        # Simulate loading projects
        time.sleep(1)
        projects_checked = 0
        total_keywords = 0
        
        # Mock project data
        active_projects = [
            {"id": "proj_123", "domain": "example.com", "keywords": ["plumber", "emergency plumber"]},
            {"id": "proj_124", "domain": "blog.example.com", "keywords": ["plumbing tips", "drain cleaning"]}
        ]
        
        for i, project in enumerate(active_projects):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 30 + (i * 30),
                    'total': 100,
                    'status': f'Checking rankings for {project["domain"]}...'
                }
            )
            
            # Simulate ranking checks
            time.sleep(2)
            projects_checked += 1
            total_keywords += len(project["keywords"])
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': 'Finalizing results...'}
        )
        
        result = {
            'status': 'completed',
            'projects_checked': projects_checked,
            'total_keywords_checked': total_keywords,
            'alerts_generated': 2,  # Mock alerts
            'completed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Keyword ranking check completed: {projects_checked} projects, {total_keywords} keywords")
        return result
        
    except Exception as exc:
        logger.error(f"Keyword ranking check failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Ranking check failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.monitoring_tasks.health_check_apis')
def health_check_apis(self) -> Dict[str, Any]:
    """
    Check health of external APIs and services.
    
    Returns:
        Health check results
    """
    try:
        logger.info("Starting external API health checks")
        
        apis_to_check = [
            {"name": "Google Search Console API", "url": "https://searchconsole.googleapis.com"},
            {"name": "Google Analytics API", "url": "https://analytics.googleapis.com"},
            {"name": "Keyword Research API", "url": "https://api.keywordtool.io"},
            {"name": "SERP API", "url": "https://serpapi.com"}
        ]
        
        health_results = []
        
        for i, api in enumerate(apis_to_check):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(apis_to_check),
                    'status': f'Checking {api["name"]}...'
                }
            )
            
            # Simulate API health check
            time.sleep(0.5)
            
            # Mock health check result
            is_healthy = i % 4 != 3  # Make one API "unhealthy" for demo
            
            health_results.append({
                'api_name': api['name'],
                'url': api['url'],
                'status': 'healthy' if is_healthy else 'unhealthy',
                'response_time': 150 + (i * 20),
                'checked_at': datetime.utcnow().isoformat()
            })
        
        unhealthy_apis = [r for r in health_results if r['status'] == 'unhealthy']
        
        result = {
            'status': 'completed',
            'total_apis_checked': len(apis_to_check),
            'healthy_apis': len(health_results) - len(unhealthy_apis),
            'unhealthy_apis': len(unhealthy_apis),
            'health_results': health_results,
            'alerts_sent': len(unhealthy_apis),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        if unhealthy_apis:
            logger.warning(f"Found {len(unhealthy_apis)} unhealthy APIs")
        
        logger.info(f"API health check completed: {len(health_results)} APIs checked")
        return result
        
    except Exception as exc:
        logger.error(f"API health check failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Health check failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.monitoring_tasks.cleanup_old_data')
def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Clean up old data and temporary files.
    
    Args:
        days_to_keep: Number of days of data to retain
        
    Returns:
        Cleanup results
    """
    try:
        logger.info(f"Starting data cleanup (keeping {days_to_keep} days)")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        cleanup_tasks = [
            "Cleaning old keyword analysis results",
            "Removing expired ranking data", 
            "Clearing temporary report files",
            "Purging old job logs",
            "Cleaning cached API responses"
        ]
        
        cleanup_results = []
        
        for i, task in enumerate(cleanup_tasks):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(cleanup_tasks),
                    'status': task
                }
            )
            
            # Simulate cleanup work
            time.sleep(1)
            
            # Mock cleanup results
            items_cleaned = 50 + (i * 25)
            space_freed = 10 + (i * 5)  # MB
            
            cleanup_results.append({
                'task': task,
                'items_cleaned': items_cleaned,
                'space_freed_mb': space_freed,
                'completed_at': datetime.utcnow().isoformat()
            })
        
        total_items = sum(r['items_cleaned'] for r in cleanup_results)
        total_space = sum(r['space_freed_mb'] for r in cleanup_results)
        
        result = {
            'status': 'completed',
            'cutoff_date': cutoff_date.isoformat(),
            'total_items_cleaned': total_items,
            'total_space_freed_mb': total_space,
            'cleanup_results': cleanup_results,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data cleanup completed: {total_items} items, {total_space}MB freed")
        return result
        
    except Exception as exc:
        logger.error(f"Data cleanup failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Cleanup failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.monitoring_tasks.monitor_system_resources')
def monitor_system_resources(self) -> Dict[str, Any]:
    """
    Monitor system resource usage and performance.
    
    Returns:
        System resource metrics
    """
    try:
        logger.info("Starting system resource monitoring")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Checking CPU usage...'}
        )
        
        time.sleep(0.5)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 40, 'total': 100, 'status': 'Checking memory usage...'}
        )
        
        time.sleep(0.5)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 60, 'total': 100, 'status': 'Checking disk usage...'}
        )
        
        time.sleep(0.5)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 80, 'total': 100, 'status': 'Checking database connections...'}
        )
        
        time.sleep(0.5)
        
        # Mock system metrics
        metrics = {
            'cpu_usage_percent': 45.2,
            'memory_usage_percent': 68.7,
            'disk_usage_percent': 23.1,
            'active_db_connections': 15,
            'redis_memory_usage_mb': 128.5,
            'celery_active_tasks': 3,
            'celery_queue_sizes': {
                'keywords': 2,
                'content': 1,
                'monitoring': 0,
                'analytics': 0
            },
            'response_times': {
                'api_avg_ms': 245,
                'db_query_avg_ms': 12,
                'redis_avg_ms': 3
            }
        }
        
        # Check for alerts
        alerts = []
        if metrics['cpu_usage_percent'] > 80:
            alerts.append('High CPU usage detected')
        if metrics['memory_usage_percent'] > 80:
            alerts.append('High memory usage detected')
        if metrics['disk_usage_percent'] > 85:
            alerts.append('High disk usage detected')
        
        result = {
            'status': 'completed',
            'metrics': metrics,
            'alerts': alerts,
            'monitoring_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"System monitoring completed, {len(alerts)} alerts generated")
        return result
        
    except Exception as exc:
        logger.error(f"System monitoring failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Monitoring failed'}
        )
        raise
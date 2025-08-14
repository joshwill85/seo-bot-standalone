"""Background job processing system using Celery."""

import os
from celery import Celery
from kombu import Queue, Exchange

from ..config import settings

# Configure Celery
def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    
    # Celery configuration
    celery_app = Celery(
        'seo_bot',
        broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
        backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2'),
        include=[
            'seo_bot.jobs.keyword_tasks',
            'seo_bot.jobs.content_tasks', 
            'seo_bot.jobs.monitoring_tasks',
            'seo_bot.jobs.analytics_tasks'
        ]
    )
    
    # Update configuration
    celery_app.conf.update(
        # Task routing
        task_routes={
            'seo_bot.jobs.keyword_tasks.*': {'queue': 'keywords'},
            'seo_bot.jobs.content_tasks.*': {'queue': 'content'},
            'seo_bot.jobs.monitoring_tasks.*': {'queue': 'monitoring'},
            'seo_bot.jobs.analytics_tasks.*': {'queue': 'analytics'},
        },
        
        # Queues with different priorities
        task_queues=(
            Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
            Queue('keywords', Exchange('keywords'), routing_key='keywords'),
            Queue('content', Exchange('content'), routing_key='content'),
            Queue('monitoring', Exchange('monitoring'), routing_key='monitoring'),
            Queue('analytics', Exchange('analytics'), routing_key='analytics'),
            Queue('default', Exchange('default'), routing_key='default'),
        ),
        
        # Task execution settings
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        
        # Task time limits
        task_time_limit=3600,  # 1 hour hard limit
        task_soft_time_limit=1800,  # 30 minute soft limit
        
        # Worker settings
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        
        # Result backend settings
        result_expires=86400,  # Results expire after 24 hours
        result_backend_transport_options={
            'master_name': 'mymaster',
            'retry_on_timeout': True,
        },
        
        # Task execution options
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Beat schedule for periodic tasks
        beat_schedule={
            'monitor-keyword-rankings': {
                'task': 'seo_bot.jobs.monitoring_tasks.check_keyword_rankings',
                'schedule': 3600.0,  # Every hour
                'options': {'queue': 'monitoring'}
            },
            'generate-analytics-reports': {
                'task': 'seo_bot.jobs.analytics_tasks.generate_daily_reports',
                'schedule': 86400.0,  # Daily
                'options': {'queue': 'analytics'}
            },
            'cleanup-old-data': {
                'task': 'seo_bot.jobs.monitoring_tasks.cleanup_old_data',
                'schedule': 604800.0,  # Weekly
                'options': {'queue': 'monitoring'}
            },
            'health-check-external-apis': {
                'task': 'seo_bot.jobs.monitoring_tasks.health_check_apis',
                'schedule': 300.0,  # Every 5 minutes
                'options': {'queue': 'monitoring'}
            }
        }
    )
    
    return celery_app

# Create global Celery instance
celery_app = create_celery_app()
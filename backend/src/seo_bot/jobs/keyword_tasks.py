"""Background tasks for keyword processing."""

import time
import logging
from typing import List, Dict, Any
from datetime import datetime

from celery import Task
from ..jobs import celery_app
from ..db import get_db_session, DatabaseManager

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task class with callbacks for success/failure."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed with exception: {exc}")


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.keyword_tasks.analyze_keywords')
def analyze_keywords(self, keywords: List[str], project_id: str, user_id: str) -> Dict[str, Any]:
    """
    Analyze keywords for SEO metrics.
    
    Args:
        keywords: List of keywords to analyze
        project_id: Project ID for context
        user_id: User ID for tracking
        
    Returns:
        Dictionary with analysis results
    """
    try:
        logger.info(f"Starting keyword analysis for {len(keywords)} keywords")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(keywords), 'status': 'Starting analysis...'}
        )
        
        results = []
        
        for i, keyword in enumerate(keywords):
            # Simulate keyword analysis
            time.sleep(1)  # Simulate API calls
            
            # Mock analysis - in production, this would call real SEO APIs
            analysis = {
                'keyword': keyword,
                'search_volume': 1000 + (i * 100),
                'competition': 0.5 + (i * 0.1),
                'cpc': 1.5 + (i * 0.2),
                'difficulty': 0.6 + (i * 0.05),
                'intent': 'commercial' if i % 2 == 0 else 'informational',
                'serp_features': ['featured_snippet'] if i % 3 == 0 else [],
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            results.append(analysis)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(keywords),
                    'status': f'Analyzed {keyword}',
                    'results': results
                }
            )
        
        # Store results in database
        with get_db_session() as session:
            # In production, save to keyword_analysis table
            logger.info(f"Saving {len(results)} keyword analyses to database")
        
        logger.info(f"Keyword analysis completed for {len(keywords)} keywords")
        
        return {
            'status': 'completed',
            'total_analyzed': len(keywords),
            'results': results,
            'project_id': project_id,
            'user_id': user_id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Keyword analysis failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Analysis failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.keyword_tasks.discover_keywords')
def discover_keywords(self, seeds: List[str], max_keywords: int = 100, project_id: str = None) -> Dict[str, Any]:
    """
    Discover keyword variations from seed keywords.
    
    Args:
        seeds: Seed keywords for expansion
        max_keywords: Maximum keywords to discover
        project_id: Optional project ID
        
    Returns:
        Dictionary with discovered keywords
    """
    try:
        logger.info(f"Starting keyword discovery from {len(seeds)} seeds")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(seeds), 'status': 'Discovering keywords...'}
        )
        
        discovered = []
        
        for i, seed in enumerate(seeds):
            # Simulate keyword discovery
            time.sleep(2)  # Simulate API calls
            
            # Mock discovery - in production, use real keyword APIs
            variations = [
                f"{seed} near me",
                f"best {seed}",
                f"{seed} services",
                f"how to {seed}",
                f"{seed} cost",
                f"{seed} reviews",
                f"cheap {seed}",
                f"{seed} company",
                f"{seed} expert",
                f"{seed} professional"
            ]
            
            discovered.extend(variations)
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(seeds),
                    'status': f'Processed {seed}',
                    'discovered_count': len(discovered)
                }
            )
        
        # Limit results
        discovered = discovered[:max_keywords]
        
        logger.info(f"Discovered {len(discovered)} keywords from {len(seeds)} seeds")
        
        return {
            'status': 'completed',
            'seeds': seeds,
            'discovered_keywords': discovered,
            'total_discovered': len(discovered),
            'project_id': project_id,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Keyword discovery failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Discovery failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.keyword_tasks.cluster_keywords')
def cluster_keywords(self, keywords: List[str], min_cluster_size: int = 3) -> Dict[str, Any]:
    """
    Cluster keywords by semantic similarity.
    
    Args:
        keywords: Keywords to cluster
        min_cluster_size: Minimum size for clusters
        
    Returns:
        Dictionary with clustering results
    """
    try:
        logger.info(f"Starting keyword clustering for {len(keywords)} keywords")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Computing similarities...'}
        )
        
        # Simulate clustering process
        time.sleep(3)
        
        # Mock clustering - in production, use ML clustering
        clusters = []
        
        # Simple word-based clustering for demo
        repair_keywords = [k for k in keywords if 'repair' in k.lower()]
        install_keywords = [k for k in keywords if 'install' in k.lower()]
        service_keywords = [k for k in keywords if 'service' in k.lower()]
        other_keywords = [k for k in keywords if k not in repair_keywords + install_keywords + service_keywords]
        
        if len(repair_keywords) >= min_cluster_size:
            clusters.append({
                'name': 'Repair Services',
                'keywords': repair_keywords,
                'hub_keyword': repair_keywords[0],
                'size': len(repair_keywords),
                'confidence': 0.85
            })
        
        if len(install_keywords) >= min_cluster_size:
            clusters.append({
                'name': 'Installation Services',
                'keywords': install_keywords,
                'hub_keyword': install_keywords[0],
                'size': len(install_keywords),
                'confidence': 0.80
            })
        
        if len(service_keywords) >= min_cluster_size:
            clusters.append({
                'name': 'General Services',
                'keywords': service_keywords,
                'hub_keyword': service_keywords[0],
                'size': len(service_keywords),
                'confidence': 0.75
            })
        
        if len(other_keywords) >= min_cluster_size:
            clusters.append({
                'name': 'Other Keywords',
                'keywords': other_keywords,
                'hub_keyword': other_keywords[0] if other_keywords else None,
                'size': len(other_keywords),
                'confidence': 0.60
            })
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 100, 'total': 100, 'status': 'Clustering complete'}
        )
        
        logger.info(f"Keyword clustering completed: {len(clusters)} clusters found")
        
        return {
            'status': 'completed',
            'total_keywords': len(keywords),
            'clusters': clusters,
            'total_clusters': len(clusters),
            'min_cluster_size': min_cluster_size,
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Keyword clustering failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Clustering failed'}
        )
        raise


@celery_app.task(bind=True, base=CallbackTask, name='seo_bot.jobs.keyword_tasks.update_keyword_rankings')
def update_keyword_rankings(self, project_id: str, keywords: List[str]) -> Dict[str, Any]:
    """
    Update keyword rankings for a project.
    
    Args:
        project_id: Project to update rankings for
        keywords: Keywords to check rankings for
        
    Returns:
        Dictionary with ranking updates
    """
    try:
        logger.info(f"Updating rankings for {len(keywords)} keywords in project {project_id}")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': len(keywords), 'status': 'Checking rankings...'}
        )
        
        ranking_updates = []
        
        for i, keyword in enumerate(keywords):
            # Simulate ranking check
            time.sleep(0.5)  # Simulate SERP API call
            
            # Mock ranking data
            ranking = {
                'keyword': keyword,
                'position': 10 + (i % 20),  # Random position 10-30
                'url': f"https://example.com/page-{i}",
                'previous_position': 12 + (i % 20),
                'change': (-1) ** i * (i % 3),
                'checked_at': datetime.utcnow().isoformat()
            }
            
            ranking_updates.append(ranking)
            
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i + 1,
                    'total': len(keywords),
                    'status': f'Checked {keyword}',
                    'updates': len(ranking_updates)
                }
            )
        
        logger.info(f"Ranking update completed for {len(keywords)} keywords")
        
        return {
            'status': 'completed',
            'project_id': project_id,
            'total_keywords': len(keywords),
            'ranking_updates': ranking_updates,
            'avg_position': sum(r['position'] for r in ranking_updates) / len(ranking_updates),
            'completed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Ranking update failed: {exc}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'Ranking update failed'}
        )
        raise
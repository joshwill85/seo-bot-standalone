"""SEO Tools API endpoints for running SEO analysis on businesses - Supabase version."""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from supabase_client import db_ops

# Import SEO bot modules
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from seo_bot.audit.website import WebsiteAuditor
from seo_bot.keywords.research import KeywordResearcher
from seo_bot.keywords.clustering import KeywordClusterer
from seo_bot.serp.analyzer import SERPAnalyzer
from seo_bot.performance.monitor import PerformanceMonitor
from seo_bot.accessibility.checker import AccessibilityChecker
from seo_bot.content.analyzer import ContentAnalyzer

logger = logging.getLogger(__name__)

# Create blueprint
seo_tools = Blueprint('seo_tools', __name__, url_prefix='/api/seo')

# Thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4)


async def log_seo_action_async(business_id: int, action_type: str, description: str, 
                              tool_name: str = None, old_data: str = None, new_data: str = None):
    """Log SEO action for audit trail."""
    try:
        current_user_id = get_jwt_identity() if request else None
        
        log_data = {
            'business_id': business_id,
            'action_type': action_type,
            'action_description': description,
            'tool_name': tool_name,
            'old_data': old_data,
            'new_data': new_data,
            'user_id': current_user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        await db_ops.create_seo_log(log_data)
        
    except Exception as e:
        logger.error(f"Failed to log SEO action: {e}")


def log_seo_action(business_id: int, action_type: str, description: str, 
                   tool_name: str = None, old_data: str = None, new_data: str = None):
    """Sync wrapper for logging SEO actions."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(log_seo_action_async(business_id, action_type, description, tool_name, old_data, new_data))
    finally:
        loop.close()


async def run_website_audit(business: Dict) -> Dict:
    """Run comprehensive website audit."""
    try:
        auditor = WebsiteAuditor()
        
        if not business.get('website_url'):
            raise ValueError("Business website URL is required")
        
        # Run audit
        audit_result = await auditor.audit_website(business['website_url'])
        
        # Calculate overall score
        technical_score = audit_result.get('technical_score', 0)
        content_score = audit_result.get('content_score', 0)
        performance_score = audit_result.get('performance_score', 0)
        overall_score = (technical_score + content_score + performance_score) / 3
        
        # Count issues
        issues = audit_result.get('issues', [])
        issues_count = len([issue for issue in issues if issue.get('severity') in ['high', 'critical']])
        
        # Generate recommendations
        recommendations = []
        if technical_score < 80:
            recommendations.append({
                'category': 'Technical SEO',
                'priority': 'high',
                'description': 'Fix technical SEO issues to improve crawlability'
            })
        
        if content_score < 70:
            recommendations.append({
                'category': 'Content',
                'priority': 'medium',
                'description': 'Optimize content for target keywords and user intent'
            })
        
        if performance_score < 85:
            recommendations.append({
                'category': 'Performance',
                'priority': 'high',
                'description': 'Improve page load speed and Core Web Vitals'
            })
        
        return {
            'audit_result': audit_result,
            'overall_score': round(overall_score, 1),
            'issues_count': issues_count,
            'recommendations': recommendations
        }
        
    except Exception as e:
        logger.error(f"Website audit failed: {e}")
        raise


async def run_keyword_research(business: Dict, seed_keywords: List[str]) -> Dict:
    """Run keyword research and clustering."""
    try:
        researcher = KeywordResearcher()
        clusterer = KeywordClusterer()
        
        # Research keywords
        research_result = await researcher.research_keywords(
            seed_keywords=seed_keywords,
            location=f"{business['city']}, {business['state']}",
            language='en'
        )
        
        # Cluster keywords
        keywords = research_result.get('keywords', [])
        clustering_result = await clusterer.cluster_keywords(keywords)
        
        # Analyze opportunity keywords
        opportunities = []
        for keyword in keywords:
            if (keyword.get('difficulty', 100) < 50 and 
                keyword.get('search_volume', 0) > 100):
                opportunities.append(keyword)
        
        return {
            'keywords': keywords,
            'clusters': clustering_result.get('clusters', []),
            'opportunities': opportunities[:20],  # Top 20 opportunities
            'total_keywords': len(keywords),
            'total_clusters': len(clustering_result.get('clusters', []))
        }
        
    except Exception as e:
        logger.error(f"Keyword research failed: {e}")
        raise


async def run_performance_audit(business: Dict) -> Dict:
    """Run performance monitoring and Core Web Vitals check."""
    try:
        monitor = PerformanceMonitor()
        
        if not business.get('website_url'):
            raise ValueError("Business website URL is required")
        
        # Run performance audit
        perf_result = await monitor.audit_performance(business['website_url'])
        
        # Analyze Core Web Vitals
        core_web_vitals = perf_result.get('core_web_vitals', {})
        lcp = core_web_vitals.get('lcp', 0)
        fid = core_web_vitals.get('fid', 0)
        cls = core_web_vitals.get('cls', 0)
        
        # Calculate performance score
        lcp_score = 100 if lcp <= 2.5 else (50 if lcp <= 4.0 else 0)
        fid_score = 100 if fid <= 100 else (50 if fid <= 300 else 0)
        cls_score = 100 if cls <= 0.1 else (50 if cls <= 0.25 else 0)
        
        performance_score = (lcp_score + fid_score + cls_score) / 3
        
        # Generate recommendations
        recommendations = []
        if lcp > 2.5:
            recommendations.append({
                'metric': 'LCP',
                'current': f"{lcp:.1f}s",
                'target': '≤ 2.5s',
                'priority': 'high',
                'suggestions': ['Optimize images', 'Reduce server response time', 'Remove unused CSS']
            })
        
        if fid > 100:
            recommendations.append({
                'metric': 'FID',
                'current': f"{fid:.0f}ms",
                'target': '≤ 100ms',
                'priority': 'medium',
                'suggestions': ['Reduce JavaScript execution time', 'Use web workers', 'Remove non-critical third-party scripts']
            })
        
        if cls > 0.1:
            recommendations.append({
                'metric': 'CLS',
                'current': f"{cls:.3f}",
                'target': '≤ 0.1',
                'priority': 'high',
                'suggestions': ['Set image dimensions', 'Reserve space for ads', 'Avoid inserting content above existing content']
            })
        
        return {
            'performance_result': perf_result,
            'performance_score': round(performance_score, 1),
            'core_web_vitals': {
                'lcp': lcp,
                'fid': fid,
                'cls': cls,
                'lcp_score': lcp_score,
                'fid_score': fid_score,
                'cls_score': cls_score
            },
            'recommendations': recommendations
        }
        
    except Exception as e:
        logger.error(f"Performance audit failed: {e}")
        raise


@seo_tools.route('/audit/<int:business_id>', methods=['POST'])
@jwt_required()
def run_full_audit(business_id):
    """Run comprehensive SEO audit for business."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            # Create audit report
            report_data = {
                'business_id': business_id,
                'report_type': 'full_audit',
                'status': 'running'
            }
            report = loop.run_until_complete(db_ops.create_seo_report(report_data))
            
            # Log audit start
            log_seo_action(
                business_id,
                'audit_started',
                'Full SEO audit initiated',
                'full_audit'
            )
            
            # Run audit asynchronously
            def run_audit():
                try:
                    audit_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(audit_loop)
                    
                    start_time = datetime.utcnow()
                    
                    # Run all audit components
                    audit_results = {}
                    
                    # Website audit
                    website_result = audit_loop.run_until_complete(run_website_audit(business))
                    audit_results['website_audit'] = website_result
                    
                    # Performance audit
                    performance_result = audit_loop.run_until_complete(run_performance_audit(business))
                    audit_results['performance_audit'] = performance_result
                    
                    # Calculate overall score
                    scores = [
                        website_result.get('overall_score', 0),
                        performance_result.get('performance_score', 0)
                    ]
                    overall_score = sum(scores) / len(scores)
                    
                    # Count total issues
                    total_issues = (
                        website_result.get('issues_count', 0) +
                        len(performance_result.get('recommendations', []))
                    )
                    
                    # Compile recommendations
                    all_recommendations = []
                    all_recommendations.extend(website_result.get('recommendations', []))
                    all_recommendations.extend(performance_result.get('recommendations', []))
                    
                    # Update report
                    execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    update_data = {
                        'status': 'completed',
                        'results': json.dumps(audit_results),
                        'score': round(overall_score, 1),
                        'issues_found': total_issues,
                        'recommendations': json.dumps(all_recommendations),
                        'execution_time_ms': int(execution_time),
                        'tools_used': json.dumps(['website_audit', 'performance_audit'])
                    }
                    
                    audit_loop.run_until_complete(db_ops.update_report(report['id'], update_data))
                    
                    # Log completion
                    log_seo_action(
                        business_id,
                        'audit_completed',
                        f'Full SEO audit completed with score {overall_score:.1f}',
                        'full_audit',
                        new_data=json.dumps({'score': overall_score, 'issues': total_issues})
                    )
                    
                except Exception as e:
                    logger.error(f"Audit execution failed: {e}")
                    
                    update_data = {
                        'status': 'failed',
                        'results': json.dumps({'error': str(e)})
                    }
                    
                    audit_loop.run_until_complete(db_ops.update_report(report['id'], update_data))
                    
                    log_seo_action(
                        business_id,
                        'audit_failed',
                        f'SEO audit failed: {str(e)}',
                        'full_audit'
                    )
                
                finally:
                    audit_loop.close()
            
            # Submit to thread pool
            executor.submit(run_audit)
            
            return jsonify({
                'message': 'SEO audit started',
                'report_id': report['id'],
                'status': 'running'
            }), 202
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Audit initiation failed: {e}")
        return jsonify({'error': 'Failed to start audit'}), 500


@seo_tools.route('/keywords/<int:business_id>', methods=['POST'])
@jwt_required()
def research_keywords(business_id):
    """Research keywords for business."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            data = request.get_json()
            seed_keywords = data.get('keywords', [])
            
            if not seed_keywords:
                # Use business target keywords if provided
                if business.get('target_keywords'):
                    try:
                        seed_keywords = json.loads(business['target_keywords'])
                    except:
                        seed_keywords = business['target_keywords'].split(',') if business['target_keywords'] else []
            
            if not seed_keywords:
                return jsonify({'error': 'Keywords required'}), 400
            
            # Create keyword research report
            report_data = {
                'business_id': business_id,
                'report_type': 'keyword_research',
                'status': 'running'
            }
            report = loop.run_until_complete(db_ops.create_seo_report(report_data))
            
            # Log keyword research start
            log_seo_action(
                business_id,
                'keyword_research_started',
                f'Keyword research for: {", ".join(seed_keywords)}',
                'keyword_research'
            )
            
            # Run keyword research asynchronously
            def run_research():
                try:
                    research_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(research_loop)
                    
                    start_time = datetime.utcnow()
                    
                    # Run keyword research
                    research_result = research_loop.run_until_complete(run_keyword_research(business, seed_keywords))
                    
                    # Update report
                    execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    update_data = {
                        'status': 'completed',
                        'results': json.dumps(research_result),
                        'score': len(research_result.get('opportunities', [])) * 5,  # Score based on opportunities
                        'issues_found': 0,
                        'recommendations': json.dumps([
                            {
                                'category': 'Keywords',
                                'priority': 'medium',
                                'description': f'Target {len(research_result.get("opportunities", []))} opportunity keywords'
                            }
                        ]),
                        'execution_time_ms': int(execution_time),
                        'tools_used': json.dumps(['keyword_research', 'keyword_clustering'])
                    }
                    
                    research_loop.run_until_complete(db_ops.update_report(report['id'], update_data))
                    
                    # Log completion
                    log_seo_action(
                        business_id,
                        'keyword_research_completed',
                        f'Found {research_result.get("total_keywords", 0)} keywords in {research_result.get("total_clusters", 0)} clusters',
                        'keyword_research',
                        new_data=json.dumps({
                            'total_keywords': research_result.get('total_keywords', 0),
                            'opportunities': len(research_result.get('opportunities', []))
                        })
                    )
                    
                except Exception as e:
                    logger.error(f"Keyword research failed: {e}")
                    
                    update_data = {
                        'status': 'failed',
                        'results': json.dumps({'error': str(e)})
                    }
                    
                    research_loop.run_until_complete(db_ops.update_report(report['id'], update_data))
                    
                    log_seo_action(
                        business_id,
                        'keyword_research_failed',
                        f'Keyword research failed: {str(e)}',
                        'keyword_research'
                    )
                
                finally:
                    research_loop.close()
            
            # Submit to thread pool
            executor.submit(run_research)
            
            return jsonify({
                'message': 'Keyword research started',
                'report_id': report['id'],
                'status': 'running'
            }), 202
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Keyword research initiation failed: {e}")
        return jsonify({'error': 'Failed to start keyword research'}), 500


@seo_tools.route('/reports/<int:business_id>', methods=['GET'])
@jwt_required()
def get_reports(business_id):
    """Get SEO reports for business."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            # Get reports
            reports = loop.run_until_complete(db_ops.get_reports_by_business(business_id))
            
            return jsonify({
                'reports': reports
            }), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get reports failed: {e}")
        return jsonify({'error': 'Failed to get reports'}), 500


@seo_tools.route('/reports/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """Get specific SEO report."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            report = loop.run_until_complete(db_ops.get_report_by_id(report_id))
            
            if not report:
                return jsonify({'error': 'Report not found'}), 404
            
            business = loop.run_until_complete(db_ops.get_business_by_id(report['business_id']))
            
            # Check permissions
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            return jsonify({'report': report}), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get report failed: {e}")
        return jsonify({'error': 'Failed to get report'}), 500


@seo_tools.route('/logs/<int:business_id>', methods=['GET'])
@jwt_required()
def get_seo_logs(business_id):
    """Get SEO activity logs for business."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            # Get logs with pagination
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            
            logs_data = loop.run_until_complete(db_ops.get_logs_by_business(business_id, page, per_page))
            
            return jsonify(logs_data), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get logs failed: {e}")
        return jsonify({'error': 'Failed to get logs'}), 500
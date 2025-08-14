"""Background job management API endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...middleware.auth import get_current_user, require_permission
from ...middleware.rate_limiting import rate_limit
from ...jobs import celery_app
from ...jobs.keyword_tasks import analyze_keywords, discover_keywords, cluster_keywords, update_keyword_rankings
from ...jobs.content_tasks import generate_content_brief, analyze_content_quality, generate_meta_tags, optimize_images
from ...jobs.monitoring_tasks import check_keyword_rankings, health_check_apis, cleanup_old_data, monitor_system_resources
from ...jobs.analytics_tasks import generate_daily_reports, analyze_competitor_changes, calculate_roi_metrics, generate_custom_report

router = APIRouter()


class JobRequest(BaseModel):
    task_name: str
    parameters: Dict[str, Any] = {}


class JobResponse(BaseModel):
    job_id: str
    task_name: str
    status: str
    created_at: str


@router.post("/start", response_model=JobResponse)
@rate_limit(requests=20, window=60)  # 20 job starts per minute
async def start_job(
    request: Request,
    job_request: JobRequest,
    user: Dict[str, Any] = Depends(require_permission("jobs:create"))
):
    """Start a background job."""
    
    # Map task names to actual Celery tasks
    task_map = {
        # Keyword tasks
        "analyze_keywords": analyze_keywords,
        "discover_keywords": discover_keywords,
        "cluster_keywords": cluster_keywords,
        "update_keyword_rankings": update_keyword_rankings,
        
        # Content tasks
        "generate_content_brief": generate_content_brief,
        "analyze_content_quality": analyze_content_quality,
        "generate_meta_tags": generate_meta_tags,
        "optimize_images": optimize_images,
        
        # Monitoring tasks
        "check_keyword_rankings": check_keyword_rankings,
        "health_check_apis": health_check_apis,
        "cleanup_old_data": cleanup_old_data,
        "monitor_system_resources": monitor_system_resources,
        
        # Analytics tasks
        "generate_daily_reports": generate_daily_reports,
        "analyze_competitor_changes": analyze_competitor_changes,
        "calculate_roi_metrics": calculate_roi_metrics,
        "generate_custom_report": generate_custom_report
    }
    
    if job_request.task_name not in task_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown task: {job_request.task_name}"
        )
    
    # Start the Celery task
    task = task_map[job_request.task_name]
    
    # Add user context to parameters
    parameters = job_request.parameters.copy()
    parameters["user_id"] = user["id"]
    
    # Start the job
    job = task.delay(**parameters)
    
    return JobResponse(
        job_id=job.id,
        task_name=job_request.task_name,
        status="started",
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/{job_id}")
async def get_job_status(
    request: Request,
    job_id: str,
    user: Dict[str, Any] = Depends(require_permission("jobs:read"))
):
    """Get job status and results."""
    
    try:
        # Get job result from Celery
        result = celery_app.AsyncResult(job_id)
        
        response = {
            "job_id": job_id,
            "status": result.status,
            "created_at": "2024-01-01T00:00:00Z"  # Mock timestamp
        }
        
        if result.status == "PENDING":
            response["message"] = "Job is waiting to be processed"
        elif result.status == "PROGRESS":
            response["progress"] = result.info
        elif result.status == "SUCCESS":
            response["result"] = result.result
        elif result.status == "FAILURE":
            response["error"] = str(result.info)
        
        return response
        
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(exc)}"
        )


@router.get("/")
async def list_jobs(
    request: Request,
    status_filter: Optional[str] = Query(None, regex="^(pending|progress|success|failure)$"),
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = Depends(require_permission("jobs:read"))
):
    """List recent jobs."""
    
    # Mock job list - in production, this would query Celery or a job database
    mock_jobs = [
        {
            "job_id": "job_123",
            "task_name": "analyze_keywords",
            "status": "success",
            "created_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:05:00Z",
            "duration": 300
        },
        {
            "job_id": "job_124",
            "task_name": "generate_content_brief",
            "status": "progress", 
            "created_at": "2024-01-01T10:30:00Z",
            "progress": {"current": 60, "total": 100, "status": "Generating outline..."}
        },
        {
            "job_id": "job_125",
            "task_name": "update_keyword_rankings",
            "status": "pending",
            "created_at": "2024-01-01T11:00:00Z"
        }
    ]
    
    # Apply status filter
    if status_filter:
        mock_jobs = [job for job in mock_jobs if job["status"] == status_filter]
    
    # Apply limit
    mock_jobs = mock_jobs[:limit]
    
    return {
        "jobs": mock_jobs,
        "total": len(mock_jobs),
        "filters": {
            "status": status_filter,
            "limit": limit
        }
    }


@router.delete("/{job_id}")
async def cancel_job(
    request: Request,
    job_id: str,
    user: Dict[str, Any] = Depends(require_permission("jobs:delete"))
):
    """Cancel a running job."""
    
    try:
        # Revoke the Celery task
        celery_app.control.revoke(job_id, terminate=True)
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancellation requested"
        }
        
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(exc)}"
        )


@router.get("/queues/status")
async def get_queue_status(
    request: Request,
    user: Dict[str, Any] = Depends(require_permission("jobs:read"))
):
    """Get status of job queues."""
    
    try:
        # Get queue information from Celery
        inspect = celery_app.control.inspect()
        
        # Mock queue status - in production, use inspect.active_queues()
        queue_status = {
            "queues": [
                {
                    "name": "keywords",
                    "active_jobs": 2,
                    "pending_jobs": 5,
                    "workers": 3
                },
                {
                    "name": "content", 
                    "active_jobs": 1,
                    "pending_jobs": 2,
                    "workers": 2
                },
                {
                    "name": "monitoring",
                    "active_jobs": 0,
                    "pending_jobs": 0,
                    "workers": 1
                },
                {
                    "name": "analytics",
                    "active_jobs": 1,
                    "pending_jobs": 1,
                    "workers": 1
                }
            ],
            "total_workers": 7,
            "total_active_jobs": 4,
            "total_pending_jobs": 8,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        return queue_status
        
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(exc)}"
        )


@router.post("/bulk-start")
@rate_limit(requests=5, window=60)  # 5 bulk operations per minute
async def start_bulk_jobs(
    request: Request,
    job_requests: List[JobRequest],
    user: Dict[str, Any] = Depends(require_permission("jobs:create"))
):
    """Start multiple jobs in bulk."""
    
    if len(job_requests) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 jobs can be started in bulk"
        )
    
    started_jobs = []
    failed_jobs = []
    
    for job_request in job_requests:
        try:
            # Use the same logic as single job start
            job_response = await start_job(request, job_request, user)
            started_jobs.append(job_response)
        except Exception as exc:
            failed_jobs.append({
                "task_name": job_request.task_name,
                "error": str(exc)
            })
    
    return {
        "started_jobs": started_jobs,
        "failed_jobs": failed_jobs,
        "summary": {
            "total_requested": len(job_requests),
            "successfully_started": len(started_jobs),
            "failed": len(failed_jobs)
        }
    }
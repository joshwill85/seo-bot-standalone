"""Dashboard API with service buttons and workflow execution."""

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...middleware.auth import get_current_user, require_permission
from ...middleware.rate_limiting import rate_limit
from ...services.service_button_mapping import ServiceButtonMapping, ServiceCategory
from ...jobs import celery_app

router = APIRouter()

# Initialize service button mapping
service_mapping = ServiceButtonMapping()


class WorkflowExecutionRequest(BaseModel):
    button_id: str
    parameters: Dict[str, Any] = {}
    priority: str = "normal"  # "low", "normal", "high"


class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    button_id: str
    status: str
    estimated_completion_time: str
    workflow_steps: List[Dict[str, Any]]
    created_at: str


@router.get("/service-buttons")
async def get_all_service_buttons(
    request: Request,
    category: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_permission("dashboard:read"))
):
    """Get all available service buttons, optionally filtered by category."""
    
    if category:
        try:
            category_enum = ServiceCategory(category)
            buttons = service_mapping.get_buttons_by_category(category_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {category}"
            )
    else:
        buttons = list(service_mapping.get_all_service_buttons().values())
    
    # Convert to response format
    button_list = []
    for button in buttons:
        button_data = {
            "button_id": button.button_id,
            "button_text": button.button_text,
            "button_description": button.button_description,
            "category": button.category.value,
            "estimated_completion_time": button.estimated_completion_time,
            "automation_level": button.automation_level,
            "prerequisites": button.prerequisites,
            "output_deliverables": button.output_deliverables,
            "parameters_required": button.parameters_required
        }
        button_list.append(button_data)
    
    return {
        "service_buttons": button_list,
        "total_buttons": len(button_list),
        "category_filter": category
    }


@router.get("/dashboard-layout")
async def get_dashboard_layout(
    request: Request,
    user: Dict[str, Any] = Depends(require_permission("dashboard:read"))
):
    """Get organized dashboard layout with buttons grouped by category."""
    
    layout = service_mapping.get_dashboard_layout()
    
    # Convert to response format
    dashboard_layout = {}
    for category_name, buttons in layout.items():
        dashboard_layout[category_name] = {
            "category_title": category_name.replace("_", " ").title(),
            "category_description": _get_category_description(category_name),
            "buttons": [
                {
                    "button_id": button.button_id,
                    "button_text": button.button_text,
                    "button_description": button.button_description,
                    "estimated_completion_time": button.estimated_completion_time,
                    "automation_level": button.automation_level,
                    "prerequisites": button.prerequisites
                }
                for button in buttons
            ]
        }
    
    return {
        "dashboard_layout": dashboard_layout,
        "user_permissions": user.get("permissions", []),
        "quick_access_buttons": _get_quick_access_buttons(user)
    }


@router.post("/execute-workflow", response_model=WorkflowExecutionResponse)
@rate_limit(requests=30, window=60)  # 30 workflow executions per minute
async def execute_workflow(
    request: Request,
    workflow_request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_permission("workflows:execute"))
):
    """Execute a service workflow from a button click."""
    
    # Get button configuration
    button = service_mapping.get_button_by_id(workflow_request.button_id)
    if not button:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service button not found: {workflow_request.button_id}"
        )
    
    # Validate prerequisites
    missing_prerequisites = _check_prerequisites(button.prerequisites, user, workflow_request.parameters)
    if missing_prerequisites:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing prerequisites: {', '.join(missing_prerequisites)}"
        )
    
    # Validate required parameters
    missing_parameters = _check_required_parameters(button.parameters_required, workflow_request.parameters)
    if missing_parameters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required parameters: {', '.join(missing_parameters)}"
        )
    
    # Get workflow mapping
    workflow_mapping = service_mapping.get_workflow_mapping(workflow_request.button_id)
    if not workflow_mapping:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow mapping not found for button: {workflow_request.button_id}"
        )
    
    # Create execution ID
    execution_id = f"exec_{workflow_request.button_id}_{int(datetime.utcnow().timestamp())}"
    
    # Add user context to parameters
    execution_parameters = workflow_request.parameters.copy()
    execution_parameters.update({
        "user_id": user["id"],
        "execution_id": execution_id,
        "button_id": workflow_request.button_id
    })
    
    # Execute workflow based on automation level
    if button.automation_level == "instant":
        # Execute immediately and return results
        result = await _execute_instant_workflow(button, execution_parameters, workflow_mapping)
        status_value = "completed"
    elif button.automation_level == "background":
        # Queue background job
        job = _queue_background_workflow(button, execution_parameters, workflow_mapping, workflow_request.priority)
        status_value = "queued"
    elif button.automation_level == "scheduled":
        # Schedule for later execution
        _schedule_workflow(button, execution_parameters, workflow_mapping)
        status_value = "scheduled"
    else:
        status_value = "pending"
    
    return WorkflowExecutionResponse(
        execution_id=execution_id,
        button_id=workflow_request.button_id,
        status=status_value,
        estimated_completion_time=button.estimated_completion_time,
        workflow_steps=workflow_mapping.get("workflow_steps", []),
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/workflow-status/{execution_id}")
async def get_workflow_status(
    request: Request,
    execution_id: str,
    user: Dict[str, Any] = Depends(require_permission("workflows:read"))
):
    """Get status of a running or completed workflow."""
    
    # Extract job ID from execution ID if it's a background job
    if execution_id.startswith("exec_"):
        # For background jobs, we need to map execution ID to Celery job ID
        # This would typically be stored in a database
        job_id = execution_id  # Simplified for demo
        
        try:
            result = celery_app.AsyncResult(job_id)
            
            response = {
                "execution_id": execution_id,
                "status": result.status,
                "created_at": "2024-01-01T00:00:00Z"  # Mock
            }
            
            if result.status == "PENDING":
                response["message"] = "Workflow is waiting to be processed"
            elif result.status == "PROGRESS":
                response["progress"] = result.info
                response["current_step"] = result.info.get("status", "Processing...")
            elif result.status == "SUCCESS":
                response["result"] = result.result
                response["deliverables"] = result.result.get("deliverables", [])
            elif result.status == "FAILURE":
                response["error"] = str(result.info)
            
            return response
            
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get workflow status: {str(exc)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )


@router.get("/workflow-history")
async def get_workflow_history(
    request: Request,
    limit: int = 50,
    category: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_permission("workflows:read"))
):
    """Get user's workflow execution history."""
    
    # Mock workflow history data
    history = [
        {
            "execution_id": "exec_discover_keywords_1704067200",
            "button_id": "discover_keywords",
            "button_text": "🔍 Discover New Keywords",
            "status": "completed",
            "created_at": "2024-01-01T10:00:00Z",
            "completed_at": "2024-01-01T10:08:00Z",
            "duration_seconds": 480,
            "deliverables": ["keyword_opportunity_report", "search_volume_data", "competition_analysis"]
        },
        {
            "execution_id": "exec_run_technical_audit_1704063600",
            "button_id": "run_technical_audit", 
            "button_text": "🔧 Run Technical SEO Audit",
            "status": "completed",
            "created_at": "2024-01-01T09:00:00Z",
            "completed_at": "2024-01-01T09:25:00Z",
            "duration_seconds": 1500,
            "deliverables": ["technical_audit_report", "prioritized_issues", "implementation_roadmap"]
        },
        {
            "execution_id": "exec_optimize_google_my_business_1704060000",
            "button_id": "optimize_google_my_business",
            "button_text": "🏢 Optimize Google My Business",
            "status": "in_progress",
            "created_at": "2024-01-01T08:00:00Z",
            "progress": {"current": 65, "total": 100, "status": "Optimizing business categories..."}
        }
    ]
    
    # Filter by category if specified
    if category:
        # In a real implementation, you'd filter based on button category
        pass
    
    # Apply limit
    history = history[:limit]
    
    return {
        "workflow_history": history,
        "total_executions": len(history),
        "filters": {
            "category": category,
            "limit": limit
        },
        "summary": {
            "total_completed": len([h for h in history if h["status"] == "completed"]),
            "total_in_progress": len([h for h in history if h["status"] == "in_progress"]),
            "total_failed": len([h for h in history if h["status"] == "failed"])
        }
    }


@router.get("/quick-actions")
async def get_quick_actions(
    request: Request,
    user: Dict[str, Any] = Depends(require_permission("dashboard:read"))
):
    """Get personalized quick action recommendations based on user's project state."""
    
    # Mock quick action recommendations
    quick_actions = [
        {
            "button_id": "discover_keywords",
            "button_text": "🔍 Discover New Keywords",
            "recommendation_reason": "You haven't run keyword research in 30 days",
            "priority": "high",
            "estimated_impact": "Find 50+ new keyword opportunities"
        },
        {
            "button_id": "run_technical_audit",
            "button_text": "🔧 Run Technical SEO Audit",
            "recommendation_reason": "Last audit found 8 high-priority issues",
            "priority": "medium",
            "estimated_impact": "Fix critical technical SEO issues"
        },
        {
            "button_id": "monitor_online_reviews",
            "button_text": "⭐ Monitor Online Reviews",
            "recommendation_reason": "2 new reviews detected",
            "priority": "low",
            "estimated_impact": "Maintain online reputation"
        }
    ]
    
    return {
        "quick_actions": quick_actions,
        "recommendations_count": len(quick_actions),
        "last_updated": datetime.utcnow().isoformat()
    }


def _get_category_description(category_name: str) -> str:
    """Get description for service category."""
    
    descriptions = {
        "keyword_research": "Discover, analyze, and track keywords to improve search visibility",
        "content_strategy": "Create, optimize, and manage content for better search performance",
        "technical_seo": "Audit and fix technical issues that impact search engine crawling and indexing",
        "link_building": "Build high-quality backlinks to improve domain authority and rankings",
        "local_seo": "Optimize for local search to attract nearby customers and improve local visibility",
        "competitor_analysis": "Analyze competitor strategies to identify opportunities and stay competitive",
        "conversion_optimization": "Optimize website elements to increase conversion rates and ROI",
        "analytics_reporting": "Track, measure, and report on SEO performance and business impact",
        "automation_management": "Manage automated SEO tasks and configure system settings"
    }
    
    return descriptions.get(category_name, "SEO optimization services")


def _get_quick_access_buttons(user: Dict[str, Any]) -> List[str]:
    """Get quick access buttons based on user preferences and usage patterns."""
    
    # Mock quick access buttons based on common usage patterns
    return [
        "discover_keywords",
        "run_technical_audit",
        "generate_seo_report",
        "optimize_google_my_business",
        "find_link_opportunities"
    ]


def _check_prerequisites(prerequisites: List[str], user: Dict[str, Any], parameters: Dict[str, Any]) -> List[str]:
    """Check if all prerequisites are met for workflow execution."""
    
    missing = []
    
    for prerequisite in prerequisites:
        if prerequisite == "business_profile_complete":
            if not parameters.get("business_name") or not parameters.get("domain"):
                missing.append("Complete business profile")
        elif prerequisite == "domain_verified":
            if not parameters.get("domain_verification_status"):
                missing.append("Verify domain ownership")
        elif prerequisite == "analytics_connected":
            if not parameters.get("google_analytics_connected"):
                missing.append("Connect Google Analytics")
        # Add more prerequisite checks as needed
    
    return missing


def _check_required_parameters(required_params: List[str], provided_params: Dict[str, Any]) -> List[str]:
    """Check if all required parameters are provided."""
    
    missing = []
    
    for param in required_params:
        if param not in provided_params or provided_params[param] is None:
            missing.append(param)
    
    return missing


async def _execute_instant_workflow(
    button: Any,
    parameters: Dict[str, Any],
    workflow_mapping: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute workflow that completes instantly."""
    
    # Mock instant execution for certain workflows
    return {
        "status": "completed",
        "deliverables": button.output_deliverables,
        "execution_time": "instant",
        "results": f"Instant workflow {button.button_id} completed successfully"
    }


def _queue_background_workflow(
    button: Any,
    parameters: Dict[str, Any],
    workflow_mapping: Dict[str, Any],
    priority: str
) -> str:
    """Queue background workflow for execution."""
    
    # Map button to actual Celery task
    task_map = {
        "discover_keywords": "seo_bot.jobs.keyword_tasks.analyze_keywords",
        "run_technical_audit": "seo_bot.jobs.monitoring_tasks.monitor_system_resources",
        "generate_seo_report": "seo_bot.jobs.analytics_tasks.generate_daily_reports",
        # Add more mappings as needed
    }
    
    task_name = task_map.get(button.button_id, "seo_bot.jobs.keyword_tasks.analyze_keywords")
    
    # Queue the appropriate Celery task
    # In a real implementation, you'd import and call the actual task
    # For now, return a mock job ID
    return f"job_{button.button_id}_{int(datetime.utcnow().timestamp())}"


def _schedule_workflow(
    button: Any,
    parameters: Dict[str, Any],
    workflow_mapping: Dict[str, Any]
) -> None:
    """Schedule workflow for later execution."""
    
    # In a real implementation, you'd add to a scheduler like Celery Beat
    pass
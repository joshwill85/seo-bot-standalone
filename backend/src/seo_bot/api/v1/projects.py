"""Projects API endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from ...middleware.auth import get_current_user, require_permission
from ...middleware.rate_limiting import rate_limit

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    domain: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    domain: str
    description: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    request: Request,
    user: Dict[str, Any] = Depends(require_permission("projects:read"))
):
    """List all projects for the current user."""
    # Mock project data
    projects = [
        ProjectResponse(
            id="proj_123",
            name="Main Website",
            domain="example.com",
            description="Primary business website",
            status="active",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        ),
        ProjectResponse(
            id="proj_124",
            name="Blog Site",
            domain="blog.example.com", 
            description="Company blog",
            status="active",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
    ]
    
    return projects


@router.post("/", response_model=ProjectResponse)
@rate_limit(requests=10, window=3600)  # 10 project creations per hour
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    user: Dict[str, Any] = Depends(require_permission("projects:write"))
):
    """Create a new project."""
    # Mock project creation
    project = ProjectResponse(
        id=f"proj_{hash(project_data.domain)}",
        name=project_data.name,
        domain=project_data.domain,
        description=project_data.description,
        status="active",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )
    
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    request: Request,
    project_id: str,
    user: Dict[str, Any] = Depends(require_permission("projects:read"))
):
    """Get project details by ID."""
    # Mock project retrieval
    if project_id == "proj_123":
        return ProjectResponse(
            id=project_id,
            name="Main Website",
            domain="example.com",
            description="Primary business website",
            status="active",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    request: Request,
    project_id: str,
    project_data: ProjectCreate,
    user: Dict[str, Any] = Depends(require_permission("projects:write"))
):
    """Update project details."""
    # Mock project update
    return ProjectResponse(
        id=project_id,
        name=project_data.name,
        domain=project_data.domain,
        description=project_data.description,
        status="active",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z"
    )


@router.delete("/{project_id}")
async def delete_project(
    request: Request,
    project_id: str,
    user: Dict[str, Any] = Depends(require_permission("projects:delete"))
):
    """Delete a project."""
    # Mock project deletion
    return {"message": f"Project {project_id} deleted successfully"}
"""Analytics API endpoints."""

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ...middleware.auth import get_current_user, require_permission
from ...middleware.rate_limiting import rate_limit

router = APIRouter()


class AnalyticsResponse(BaseModel):
    metric: str
    value: float
    change: float
    period: str


@router.get("/dashboard")
async def get_dashboard_analytics(
    request: Request,
    project_id: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_permission("analytics:read"))
):
    """Get dashboard analytics overview."""
    # Mock analytics data
    return {
        "overview": {
            "total_keywords": 1250,
            "organic_traffic": 15430,
            "avg_position": 12.5,
            "click_through_rate": 3.2
        },
        "trends": [
            AnalyticsResponse(
                metric="organic_traffic",
                value=15430,
                change=12.5,
                period="30d"
            ),
            AnalyticsResponse(
                metric="keyword_rankings",
                value=1250,
                change=8.3,
                period="30d"
            ),
            AnalyticsResponse(
                metric="avg_position",
                value=12.5,
                change=-2.1,
                period="30d"
            )
        ],
        "period": "last_30_days",
        "updated_at": datetime.utcnow().isoformat()
    }


@router.get("/keywords")
@rate_limit(requests=100, window=60)
async def get_keyword_analytics(
    request: Request,
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    user: Dict[str, Any] = Depends(require_permission("analytics:read"))
):
    """Get keyword performance analytics."""
    # Mock keyword analytics
    keywords = []
    
    sample_keywords = [
        "emergency plumber",
        "plumbing repair", 
        "water heater installation",
        "drain cleaning",
        "pipe replacement"
    ]
    
    for i, keyword in enumerate(sample_keywords):
        keywords.append({
            "keyword": keyword,
            "position": 8 + i,
            "clicks": 150 - (i * 20),
            "impressions": 2000 - (i * 200),
            "ctr": (150 - (i * 20)) / (2000 - (i * 200)) * 100,
            "change_7d": (-1) ** i * (i + 1) * 0.5
        })
    
    return {
        "keywords": keywords[:limit],
        "total_keywords": len(sample_keywords),
        "summary": {
            "total_clicks": sum(k["clicks"] for k in keywords),
            "total_impressions": sum(k["impressions"] for k in keywords),
            "avg_position": sum(k["position"] for k in keywords) / len(keywords),
            "avg_ctr": sum(k["ctr"] for k in keywords) / len(keywords)
        }
    }


@router.get("/traffic")
async def get_traffic_analytics(
    request: Request,
    project_id: Optional[str] = Query(None),
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    user: Dict[str, Any] = Depends(require_permission("analytics:read"))
):
    """Get traffic analytics over time."""
    # Mock traffic data
    days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}[period]
    
    traffic_data = []
    base_date = datetime.utcnow() - timedelta(days=days)
    
    for i in range(days):
        date = base_date + timedelta(days=i)
        traffic_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "organic_clicks": 450 + (i * 2) + (i % 7) * 50,
            "impressions": 8000 + (i * 10) + (i % 7) * 200,
            "ctr": 5.6 + (i % 10) * 0.1,
            "avg_position": 12.0 - (i % 20) * 0.1
        })
    
    return {
        "traffic_data": traffic_data,
        "period": period,
        "summary": {
            "total_clicks": sum(d["organic_clicks"] for d in traffic_data),
            "total_impressions": sum(d["impressions"] for d in traffic_data),
            "avg_ctr": sum(d["ctr"] for d in traffic_data) / len(traffic_data),
            "avg_position": sum(d["avg_position"] for d in traffic_data) / len(traffic_data)
        }
    }


@router.get("/competitors")
async def get_competitor_analysis(
    request: Request,
    project_id: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_permission("analytics:read"))
):
    """Get competitor analysis data."""
    # Mock competitor data
    return {
        "competitors": [
            {
                "domain": "competitor1.com",
                "shared_keywords": 150,
                "avg_position": 8.5,
                "estimated_traffic": 12000,
                "visibility_score": 78.5
            },
            {
                "domain": "competitor2.com",
                "shared_keywords": 120,
                "avg_position": 11.2,
                "estimated_traffic": 8500,
                "visibility_score": 65.3
            }
        ],
        "keyword_gaps": [
            {
                "keyword": "emergency plumbing service",
                "competitor_position": 3,
                "our_position": None,
                "search_volume": 1200,
                "difficulty": 0.7
            }
        ],
        "opportunities": [
            {
                "keyword": "24/7 plumber",
                "current_position": 15,
                "opportunity_position": 5,
                "potential_traffic": 200,
                "difficulty": 0.6
            }
        ]
    }


@router.get("/reports")
async def get_reports_list(
    request: Request,
    user: Dict[str, Any] = Depends(require_permission("analytics:read"))
):
    """Get list of available reports."""
    return {
        "reports": [
            {
                "id": "weekly_summary",
                "name": "Weekly SEO Summary",
                "description": "Weekly performance overview",
                "last_generated": "2024-01-01T00:00:00Z",
                "status": "completed"
            },
            {
                "id": "keyword_opportunities",
                "name": "Keyword Opportunities",
                "description": "New keyword opportunities analysis",
                "last_generated": "2024-01-01T00:00:00Z", 
                "status": "completed"
            }
        ]
    }
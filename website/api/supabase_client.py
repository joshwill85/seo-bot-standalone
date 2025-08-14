"""Supabase client configuration and database operations."""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from supabase import create_client, Client
import postgrest
from postgrest.exceptions import APIError

logger = logging.getLogger(__name__)


@dataclass
class SupabaseConfig:
    """Supabase configuration."""
    url: str
    key: str
    service_role_key: str


class SupabaseClient:
    """Enhanced Supabase client with error handling and logging."""
    
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.client: Client = create_client(config.url, config.key)
        self.admin_client: Client = create_client(config.url, config.service_role_key)
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into table."""
        try:
            result = self.client.table(table).insert(data).execute()
            logger.info(f"Inserted into {table}: {result.data}")
            return result.data[0] if result.data else {}
        except APIError as e:
            logger.error(f"Insert failed for {table}: {e}")
            raise
    
    async def select(self, table: str, columns: str = "*", filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Select data from table with optional filters."""
        try:
            query = self.client.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(key, value)
                    elif isinstance(value, dict) and 'operator' in value:
                        op = value['operator']
                        val = value['value']
                        if op == 'gte':
                            query = query.gte(key, val)
                        elif op == 'lte':
                            query = query.lte(key, val)
                        elif op == 'gt':
                            query = query.gt(key, val)
                        elif op == 'lt':
                            query = query.lt(key, val)
                        elif op == 'like':
                            query = query.like(key, val)
                        elif op == 'ilike':
                            query = query.ilike(key, val)
                        else:
                            query = query.eq(key, val)
                    else:
                        query = query.eq(key, value)
            
            result = query.execute()
            return result.data
            
        except APIError as e:
            logger.error(f"Select failed for {table}: {e}")
            raise
    
    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update data in table."""
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            logger.info(f"Updated {table}: {len(result.data)} records")
            return result.data
            
        except APIError as e:
            logger.error(f"Update failed for {table}: {e}")
            raise
    
    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete data from table."""
        try:
            query = self.client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            logger.info(f"Deleted from {table}: {len(result.data)} records")
            return result.data
            
        except APIError as e:
            logger.error(f"Delete failed for {table}: {e}")
            raise
    
    async def upsert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert data into table."""
        try:
            result = self.client.table(table).upsert(data).execute()
            logger.info(f"Upserted into {table}: {result.data}")
            return result.data[0] if result.data else {}
        except APIError as e:
            logger.error(f"Upsert failed for {table}: {e}")
            raise
    
    async def count(self, table: str, filters: Dict[str, Any] = None) -> int:
        """Count records in table."""
        try:
            query = self.client.table(table).select("*", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.count
            
        except APIError as e:
            logger.error(f"Count failed for {table}: {e}")
            raise
    
    async def rpc(self, function_name: str, params: Dict[str, Any] = None) -> Any:
        """Call Supabase RPC function."""
        try:
            result = self.client.rpc(function_name, params or {}).execute()
            return result.data
        except APIError as e:
            logger.error(f"RPC failed for {function_name}: {e}")
            raise


# Initialize Supabase client
def get_supabase_client() -> SupabaseClient:
    """Get configured Supabase client."""
    config = SupabaseConfig(
        url=os.getenv('SUPABASE_URL'),
        key=os.getenv('SUPABASE_ANON_KEY'),
        service_role_key=os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    
    if not all([config.url, config.key, config.service_role_key]):
        raise ValueError("Missing Supabase configuration. Please set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY environment variables.")
    
    return SupabaseClient(config)


# Database operation helpers
class DatabaseOperations:
    """Database operations using Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new user."""
        user_data['created_at'] = datetime.utcnow().isoformat()
        return await self.client.insert('users', user_data)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        users = await self.client.select('users', filters={'email': email})
        return users[0] if users else None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        users = await self.client.select('users', filters={'id': user_id})
        return users[0] if users else None
    
    async def update_user_login(self, user_id: int) -> None:
        """Update user last login timestamp."""
        await self.client.update(
            'users',
            {'last_login': datetime.utcnow().isoformat()},
            {'id': user_id}
        )
    
    # Business operations
    async def create_business(self, business_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new business."""
        business_data['created_at'] = datetime.utcnow().isoformat()
        business_data['updated_at'] = datetime.utcnow().isoformat()
        return await self.client.insert('businesses', business_data)
    
    async def get_businesses_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Get businesses for user."""
        return await self.client.select('businesses', filters={'user_id': user_id})
    
    async def get_all_businesses(self) -> List[Dict[str, Any]]:
        """Get all businesses (admin only)."""
        return await self.client.select('businesses')
    
    async def get_business_by_id(self, business_id: int) -> Optional[Dict[str, Any]]:
        """Get business by ID."""
        businesses = await self.client.select('businesses', filters={'id': business_id})
        return businesses[0] if businesses else None
    
    async def update_business(self, business_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update business."""
        updates['updated_at'] = datetime.utcnow().isoformat()
        result = await self.client.update('businesses', updates, {'id': business_id})
        return result[0] if result else {}
    
    # SEO Report operations
    async def create_seo_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create SEO report."""
        report_data['created_at'] = datetime.utcnow().isoformat()
        return await self.client.insert('seo_reports', report_data)
    
    async def get_reports_by_business(self, business_id: int) -> List[Dict[str, Any]]:
        """Get reports for business."""
        return await self.client.select(
            'seo_reports',
            filters={'business_id': business_id}
        )
    
    async def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Get report by ID."""
        reports = await self.client.select('seo_reports', filters={'id': report_id})
        return reports[0] if reports else None
    
    async def update_report(self, report_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update SEO report."""
        if 'status' in updates and updates['status'] == 'completed':
            updates['completed_at'] = datetime.utcnow().isoformat()
        
        result = await self.client.update('seo_reports', updates, {'id': report_id})
        return result[0] if result else {}
    
    # SEO Log operations
    async def create_seo_log(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create SEO log entry."""
        log_data['created_at'] = datetime.utcnow().isoformat()
        return await self.client.insert('seo_logs', log_data)
    
    async def get_logs_by_business(self, business_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get logs for business with pagination."""
        offset = (page - 1) * per_page
        
        # Get total count
        total_count = await self.client.count('seo_logs', {'business_id': business_id})
        
        # Get paginated logs
        logs = await self.client.select(
            'seo_logs',
            filters={'business_id': business_id}
        )
        
        # Sort by created_at desc and apply pagination
        sorted_logs = sorted(logs, key=lambda x: x['created_at'], reverse=True)
        paginated_logs = sorted_logs[offset:offset + per_page]
        
        return {
            'logs': paginated_logs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': offset + per_page < total_count,
                'has_prev': page > 1
            }
        }
    
    # Analytics and insights
    async def get_business_analytics(self, business_id: int) -> Dict[str, Any]:
        """Get analytics for business."""
        try:
            # Get report counts by type
            reports = await self.client.select('seo_reports', filters={'business_id': business_id})
            
            report_stats = {}
            latest_scores = {}
            
            for report in reports:
                report_type = report.get('report_type', 'unknown')
                report_stats[report_type] = report_stats.get(report_type, 0) + 1
                
                # Track latest scores
                if report.get('score') is not None:
                    if report_type not in latest_scores or report['created_at'] > latest_scores[report_type]['created_at']:
                        latest_scores[report_type] = {
                            'score': report['score'],
                            'created_at': report['created_at']
                        }
            
            # Get recent activity
            recent_logs = await self.client.select(
                'seo_logs',
                filters={'business_id': business_id}
            )
            recent_activity = sorted(recent_logs, key=lambda x: x['created_at'], reverse=True)[:10]
            
            return {
                'report_counts': report_stats,
                'latest_scores': latest_scores,
                'total_reports': len(reports),
                'recent_activity': recent_activity
            }
            
        except Exception as e:
            logger.error(f"Analytics failed for business {business_id}: {e}")
            return {}


# Global database instance
db_ops = DatabaseOperations()
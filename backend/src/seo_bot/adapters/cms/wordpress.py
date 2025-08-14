"""WordPress CMS adapter using REST API."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path
import base64
import mimetypes

import aiohttp

from .base import (
    CMSAdapter, CMSCapabilities, CMSError, AuthenticationError, PublishError,
    ContentItem, ContentType, PublishResult, PublishStatus
)

logger = logging.getLogger(__name__)


class WordPressAdapter(CMSAdapter):
    """CMS adapter for WordPress using REST API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize WordPress adapter.
        
        Expected config:
        - site_url: WordPress site URL
        - username: WordPress username
        - app_password: WordPress application password
        - api_base: API base path (default: '/wp-json/wp/v2')
        """
        super().__init__(config)
        
        self.site_url = config['site_url'].rstrip('/')
        self.username = config['username']
        self.app_password = config['app_password']
        self.api_base = config.get('api_base', '/wp-json/wp/v2')
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._auth_header = self._create_auth_header()
    
    @property
    def name(self) -> str:
        """Return the name of this CMS adapter."""
        return "WordPress"
    
    def _get_capabilities(self) -> CMSCapabilities:
        """Return the capabilities of the WordPress adapter."""
        return CMSCapabilities(
            supports_drafts=True,
            supports_scheduling=True,
            supports_categories=True,
            supports_tags=True,
            supports_custom_fields=True,
            supports_media_upload=True,
            supports_bulk_operations=False,
            supports_revisions=True,
            supports_redirects=True,
            max_content_length=None,
            supported_content_types=[ContentType.ARTICLE, ContentType.PAGE]
        )
    
    def _create_auth_header(self) -> str:
        """Create HTTP Basic authentication header."""
        credentials = f"{self.username}:{self.app_password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to WordPress API."""
        await self._ensure_session()
        
        url = f"{self.site_url}{self.api_base}{endpoint}"
        headers = {
            'Authorization': self._auth_header,
            'Content-Type': 'application/json'
        }
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            ) as response:
                
                if response.status == 401:
                    raise AuthenticationError("WordPress authentication failed")
                
                response_data = await response.json()
                
                if response.status >= 400:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    raise PublishError(f"WordPress API error: {error_message}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            raise CMSError(f"Network error: {e}")
    
    async def authenticate(self) -> bool:
        """Test authentication with WordPress."""
        try:
            await self._make_request('GET', '/users/me')
            self._authenticated = True
            return True
        except (AuthenticationError, CMSError):
            self._authenticated = False
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to WordPress site."""
        try:
            await self._ensure_session()
            
            # Test basic connectivity
            url = f"{self.site_url}/wp-json/"
            async with self.session.get(url) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"WordPress connection test failed: {e}")
            return False
    
    def _map_status_to_wordpress(self, status: PublishStatus) -> str:
        """Map PublishStatus to WordPress status."""
        mapping = {
            PublishStatus.DRAFT: 'draft',
            PublishStatus.PUBLISHED: 'publish',
            PublishStatus.SCHEDULED: 'future',
            PublishStatus.ARCHIVED: 'private'
        }
        return mapping.get(status, 'draft')
    
    def _map_wordpress_status(self, wp_status: str) -> PublishStatus:
        """Map WordPress status to PublishStatus."""
        mapping = {
            'draft': PublishStatus.DRAFT,
            'publish': PublishStatus.PUBLISHED,
            'future': PublishStatus.SCHEDULED,
            'private': PublishStatus.ARCHIVED,
            'pending': PublishStatus.DRAFT,
            'auto-draft': PublishStatus.DRAFT
        }
        return mapping.get(wp_status, PublishStatus.DRAFT)
    
    def _prepare_wordpress_data(self, content: ContentItem) -> Dict[str, Any]:
        """Prepare content data for WordPress API."""
        data = {
            'title': content.title,
            'content': content.content,
            'slug': content.slug,
            'status': self._map_status_to_wordpress(content.status)
        }
        
        # Add meta fields
        if content.meta_description:
            data['excerpt'] = content.meta_description
        
        if content.publish_date:
            data['date'] = content.publish_date.isoformat()
        
        if content.modified_date:
            data['modified'] = content.modified_date.isoformat()
        
        # Handle categories (need to convert names to IDs)
        if content.categories:
            data['categories'] = content.categories  # WordPress will handle name-to-ID conversion
        
        # Handle tags
        if content.tags:
            data['tags'] = content.tags
        
        # Featured image
        if content.featured_image_url:
            # This would need to be handled separately by uploading the image first
            pass
        
        # Custom fields (meta)
        meta_fields = {}
        
        if content.meta_title:
            meta_fields['_yoast_wpseo_title'] = content.meta_title
        
        if content.meta_description:
            meta_fields['_yoast_wpseo_metadesc'] = content.meta_description
        
        if content.canonical_url:
            meta_fields['_yoast_wpseo_canonical'] = content.canonical_url
        
        if content.schema_markup:
            meta_fields['_seo_bot_schema'] = content.schema_markup
        
        # Add custom fields
        meta_fields.update(content.custom_fields)
        
        if meta_fields:
            data['meta'] = meta_fields
        
        return data
    
    def _parse_wordpress_response(self, wp_data: Dict[str, Any]) -> ContentItem:
        """Parse WordPress API response to ContentItem."""
        
        # Parse dates
        publish_date = None
        if wp_data.get('date'):
            try:
                publish_date = datetime.fromisoformat(wp_data['date'].replace('T', ' ').replace('Z', '+00:00'))
            except ValueError:
                pass
        
        modified_date = None
        if wp_data.get('modified'):
            try:
                modified_date = datetime.fromisoformat(wp_data['modified'].replace('T', ' ').replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Extract content
        title = wp_data.get('title', {})
        if isinstance(title, dict):
            title = title.get('rendered', '')
        
        content_data = wp_data.get('content', {})
        if isinstance(content_data, dict):
            content = content_data.get('rendered', '')
        else:
            content = str(content_data)
        
        excerpt = wp_data.get('excerpt', {})
        if isinstance(excerpt, dict):
            excerpt = excerpt.get('rendered', '')
        
        # Get meta fields
        meta = wp_data.get('meta', {})
        meta_title = meta.get('_yoast_wpseo_title')
        meta_description = meta.get('_yoast_wpseo_metadesc', excerpt)
        canonical_url = meta.get('_yoast_wpseo_canonical')
        schema_markup = meta.get('_seo_bot_schema')
        
        # Extract custom fields (exclude known SEO fields)
        known_meta_fields = {
            '_yoast_wpseo_title', '_yoast_wpseo_metadesc', '_yoast_wpseo_canonical',
            '_seo_bot_schema'
        }
        custom_fields = {k: v for k, v in meta.items() if k not in known_meta_fields}
        
        # Determine content type
        post_type = wp_data.get('type', 'post')
        if post_type == 'page':
            content_type = ContentType.PAGE
        else:
            content_type = ContentType.ARTICLE
        
        return ContentItem(
            title=title,
            content=content,
            content_type=content_type,
            slug=wp_data.get('slug', ''),
            meta_title=meta_title,
            meta_description=meta_description,
            canonical_url=canonical_url,
            status=self._map_wordpress_status(wp_data.get('status', 'draft')),
            author=wp_data.get('author'),  # This would be author ID, not name
            publish_date=publish_date,
            modified_date=modified_date,
            categories=wp_data.get('categories', []),
            tags=wp_data.get('tags', []),
            schema_markup=schema_markup,
            custom_fields=custom_fields,
            external_id=str(wp_data.get('id', '')),
        )
    
    async def publish_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Publish content to WordPress."""
        try:
            # Validate content
            validation_errors = self.validate_content(content)
            if validation_errors:
                result = PublishResult(success=False, message="Content validation failed")
                for error in validation_errors:
                    result.add_error(error)
                return result
            
            # Prepare content
            content = self.prepare_content_for_publish(content)
            
            if dry_run:
                return PublishResult(
                    success=True,
                    message=f"Dry run: Would publish '{content.title}' to WordPress",
                    status=content.status
                )
            
            # Determine endpoint based on content type
            if content.content_type == ContentType.PAGE:
                endpoint = '/pages'
            else:
                endpoint = '/posts'
            
            # Prepare WordPress data
            wp_data = self._prepare_wordpress_data(content)
            
            # Create post/page
            response = await self._make_request('POST', endpoint, wp_data)
            
            # Parse response
            post_id = response.get('id')
            post_url = response.get('link')
            
            logger.info(f"Published content to WordPress: ID {post_id}")
            
            return PublishResult(
                success=True,
                external_id=str(post_id),
                url=post_url,
                status=self._map_wordpress_status(response.get('status', 'draft')),
                message=f"Successfully published to WordPress (ID: {post_id})",
                published_at=datetime.now(timezone.utc),
                cms_response=response
            )
            
        except Exception as e:
            logger.error(f"Failed to publish to WordPress: {e}")
            result = PublishResult(success=False, message=f"WordPress publish failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def update_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Update existing content in WordPress."""
        try:
            if not content.external_id:
                return await self.publish_content(content, dry_run)
            
            # Validate content
            validation_errors = self.validate_content(content)
            if validation_errors:
                result = PublishResult(success=False, message="Content validation failed")
                for error in validation_errors:
                    result.add_error(error)
                return result
            
            # Prepare content
            content = self.prepare_content_for_publish(content)
            
            if dry_run:
                return PublishResult(
                    success=True,
                    message=f"Dry run: Would update WordPress content ID {content.external_id}",
                    status=content.status
                )
            
            # Determine endpoint based on content type
            if content.content_type == ContentType.PAGE:
                endpoint = f'/pages/{content.external_id}'
            else:
                endpoint = f'/posts/{content.external_id}'
            
            # Prepare WordPress data
            wp_data = self._prepare_wordpress_data(content)
            
            # Update post/page
            response = await self._make_request('PUT', endpoint, wp_data)
            
            # Parse response
            post_id = response.get('id')
            post_url = response.get('link')
            
            logger.info(f"Updated WordPress content: ID {post_id}")
            
            return PublishResult(
                success=True,
                external_id=str(post_id),
                url=post_url,
                status=self._map_wordpress_status(response.get('status', 'draft')),
                message=f"Successfully updated WordPress content (ID: {post_id})",
                published_at=datetime.now(timezone.utc),
                cms_response=response
            )
            
        except Exception as e:
            logger.error(f"Failed to update WordPress content: {e}")
            result = PublishResult(success=False, message=f"WordPress update failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def delete_content(self, external_id: str, dry_run: bool = False) -> PublishResult:
        """Delete content from WordPress."""
        try:
            if dry_run:
                return PublishResult(
                    success=True,
                    message=f"Dry run: Would delete WordPress content ID {external_id}"
                )
            
            # First, get the content to determine type
            content = await self.get_content(external_id)
            if not content:
                result = PublishResult(success=False, message=f"Content not found: {external_id}")
                result.add_error("Content does not exist")
                return result
            
            # Determine endpoint
            if content.content_type == ContentType.PAGE:
                endpoint = f'/pages/{external_id}'
            else:
                endpoint = f'/posts/{external_id}'
            
            # Delete (move to trash)
            response = await self._make_request('DELETE', endpoint)
            
            logger.info(f"Deleted WordPress content: ID {external_id}")
            
            return PublishResult(
                success=True,
                message=f"Successfully deleted WordPress content (ID: {external_id})",
                cms_response=response
            )
            
        except Exception as e:
            logger.error(f"Failed to delete WordPress content: {e}")
            result = PublishResult(success=False, message=f"WordPress delete failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def get_content(self, external_id: str) -> Optional[ContentItem]:
        """Retrieve content from WordPress."""
        try:
            # Try as post first
            try:
                response = await self._make_request('GET', f'/posts/{external_id}')
                return self._parse_wordpress_response(response)
            except PublishError:
                # Try as page
                try:
                    response = await self._make_request('GET', f'/pages/{external_id}')
                    return self._parse_wordpress_response(response)
                except PublishError:
                    return None
            
        except Exception as e:
            logger.error(f"Failed to get WordPress content {external_id}: {e}")
            return None
    
    async def list_content(self, content_type: Optional[ContentType] = None, limit: int = 100) -> List[ContentItem]:
        """List content from WordPress."""
        try:
            content_items = []
            
            # Determine endpoints to query
            endpoints = []
            if content_type == ContentType.PAGE:
                endpoints = ['/pages']
            elif content_type == ContentType.ARTICLE:
                endpoints = ['/posts']
            else:
                endpoints = ['/posts', '/pages']
            
            # Query each endpoint
            for endpoint in endpoints:
                params = {
                    'per_page': min(limit, 100),  # WordPress max is 100
                    'status': 'any',
                    'orderby': 'modified',
                    'order': 'desc'
                }
                
                try:
                    response = await self._make_request('GET', endpoint, params=params)
                    
                    if isinstance(response, list):
                        for item_data in response:
                            content_item = self._parse_wordpress_response(item_data)
                            content_items.append(content_item)
                            
                            if len(content_items) >= limit:
                                break
                                
                except Exception as e:
                    logger.warning(f"Failed to list from {endpoint}: {e}")
                    continue
                
                if len(content_items) >= limit:
                    break
            
            return content_items[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list WordPress content: {e}")
            return []
    
    async def upload_media(self, file_path: Path, alt_text: str = "") -> Optional[str]:
        """Upload media file to WordPress."""
        try:
            if not file_path.exists():
                logger.error(f"Media file not found: {file_path}")
                return None
            
            await self._ensure_session()
            
            # Prepare file upload
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            url = f"{self.site_url}{self.api_base}/media"
            headers = {
                'Authorization': self._auth_header,
                'Content-Disposition': f'attachment; filename="{file_path.name}"',
                'Content-Type': mime_type
            }
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload file
            async with self.session.post(url, data=file_content, headers=headers) as response:
                if response.status == 401:
                    raise AuthenticationError("WordPress authentication failed")
                
                response_data = await response.json()
                
                if response.status >= 400:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    raise PublishError(f"WordPress media upload error: {error_message}")
                
                # Update alt text if provided
                media_id = response_data.get('id')
                if media_id and alt_text:
                    alt_data = {'alt_text': alt_text}
                    await self._make_request('PUT', f'/media/{media_id}', alt_data)
                
                media_url = response_data.get('source_url')
                logger.info(f"Uploaded media to WordPress: {media_url}")
                
                return media_url
            
        except Exception as e:
            logger.error(f"Failed to upload media to WordPress: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
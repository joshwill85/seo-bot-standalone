"""Contentful headless CMS adapter."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

import aiohttp

from .base import (
    CMSAdapter, CMSCapabilities, CMSError, AuthenticationError, PublishError,
    ContentItem, ContentType, PublishResult, PublishStatus
)

logger = logging.getLogger(__name__)


class ContentfulAdapter(CMSAdapter):
    """CMS adapter for Contentful headless CMS."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Contentful adapter.
        
        Expected config:
        - space_id: Contentful space ID
        - access_token: Content Delivery API access token
        - management_token: Content Management API access token (for publishing)
        - environment: Environment ID (default: 'master')
        - content_type_mapping: Mapping of ContentType to Contentful content type IDs
        """
        super().__init__(config)
        
        self.space_id = config['space_id']
        self.access_token = config['access_token']
        self.management_token = config['management_token']
        self.environment = config.get('environment', 'master')
        
        # Content type mapping
        self.content_type_mapping = config.get('content_type_mapping', {
            ContentType.ARTICLE.value: 'article',
            ContentType.PAGE.value: 'page',
            ContentType.AUTHOR.value: 'author'
        })
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        # API URLs
        self.delivery_base_url = f"https://cdn.contentful.com/spaces/{self.space_id}/environments/{self.environment}"
        self.management_base_url = f"https://api.contentful.com/spaces/{self.space_id}/environments/{self.environment}"
    
    @property
    def name(self) -> str:
        """Return the name of this CMS adapter."""
        return "Contentful"
    
    def _get_capabilities(self) -> CMSCapabilities:
        """Return the capabilities of the Contentful adapter."""
        return CMSCapabilities(
            supports_drafts=True,
            supports_scheduling=True,
            supports_categories=True,
            supports_tags=True,
            supports_custom_fields=True,
            supports_media_upload=True,
            supports_bulk_operations=True,
            supports_revisions=True,
            supports_redirects=False,
            max_content_length=50000,  # Contentful text field limit
            supported_content_types=[ContentType.ARTICLE, ContentType.PAGE, ContentType.AUTHOR]
        )
    
    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _make_delivery_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make request to Contentful Delivery API."""
        await self._ensure_session()
        
        url = f"{self.delivery_base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 401:
                    raise AuthenticationError("Contentful authentication failed")
                
                response_data = await response.json()
                
                if response.status >= 400:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    raise CMSError(f"Contentful Delivery API error: {error_message}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            raise CMSError(f"Network error: {e}")
    
    async def _make_management_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make request to Contentful Management API."""
        await self._ensure_session()
        
        url = f"{self.management_base_url}{endpoint}"
        request_headers = {
            'Authorization': f'Bearer {self.management_token}',
            'Content-Type': 'application/vnd.contentful.management.v1+json'
        }
        
        if headers:
            request_headers.update(headers)
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                headers=request_headers
            ) as response:
                
                if response.status == 401:
                    raise AuthenticationError("Contentful management authentication failed")
                
                if response.status == 204:  # No content
                    return {}
                
                response_data = await response.json()
                
                if response.status >= 400:
                    error_message = response_data.get('message', f'HTTP {response.status}')
                    raise PublishError(f"Contentful Management API error: {error_message}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            raise CMSError(f"Network error: {e}")
    
    async def authenticate(self) -> bool:
        """Test authentication with Contentful."""
        try:
            # Test delivery API
            await self._make_delivery_request('/entries', {'limit': 1})
            
            # Test management API
            await self._make_management_request('GET', '/entries', {'limit': 1})
            
            self._authenticated = True
            return True
        except (AuthenticationError, CMSError):
            self._authenticated = False
            return False
    
    async def test_connection(self) -> bool:
        """Test connection to Contentful."""
        try:
            await self._make_delivery_request('/entries', {'limit': 1})
            return True
        except Exception as e:
            logger.error(f"Contentful connection test failed: {e}")
            return False
    
    def _map_status_to_contentful(self, status: PublishStatus) -> bool:
        """Map PublishStatus to Contentful published state."""
        return status == PublishStatus.PUBLISHED
    
    def _map_contentful_status(self, entry_data: Dict[str, Any]) -> PublishStatus:
        """Map Contentful entry state to PublishStatus."""
        sys = entry_data.get('sys', {})
        
        # Check if entry is published
        if 'publishedAt' in sys and sys['publishedAt']:
            publish_date = datetime.fromisoformat(sys['publishedAt'].replace('Z', '+00:00'))
            if publish_date > datetime.now(timezone.utc):
                return PublishStatus.SCHEDULED
            else:
                return PublishStatus.PUBLISHED
        else:
            return PublishStatus.DRAFT
    
    def _prepare_contentful_data(self, content: ContentItem) -> Dict[str, Any]:
        """Prepare content data for Contentful Management API."""
        
        # Get Contentful content type ID
        contentful_content_type = self.content_type_mapping.get(
            content.content_type.value,
            'article'
        )
        
        fields = {
            'title': {'en-US': content.title},
            'slug': {'en-US': content.slug},
            'content': {'en-US': content.content}
        }
        
        # Add optional fields
        if content.meta_title:
            fields['metaTitle'] = {'en-US': content.meta_title}
        
        if content.meta_description:
            fields['metaDescription'] = {'en-US': content.meta_description}
        
        if content.canonical_url:
            fields['canonicalUrl'] = {'en-US': content.canonical_url}
        
        if content.author:
            fields['author'] = {'en-US': content.author}
        
        if content.categories:
            fields['categories'] = {'en-US': content.categories}
        
        if content.tags:
            fields['tags'] = {'en-US': content.tags}
        
        if content.featured_image_url:
            # This would need to reference an uploaded asset
            # For now, store as URL field
            fields['featuredImageUrl'] = {'en-US': content.featured_image_url}
            if content.featured_image_alt:
                fields['featuredImageAlt'] = {'en-US': content.featured_image_alt}
        
        if content.schema_markup:
            fields['schemaMarkup'] = {'en-US': content.schema_markup}
        
        # Add custom fields
        for key, value in content.custom_fields.items():
            fields[key] = {'en-US': value}
        
        return {
            'fields': fields
        }
    
    def _parse_contentful_entry(self, entry_data: Dict[str, Any]) -> ContentItem:
        """Parse Contentful entry to ContentItem."""
        
        fields = entry_data.get('fields', {})
        sys = entry_data.get('sys', {})
        
        # Extract basic fields
        title = fields.get('title', {}).get('en-US', '')
        content = fields.get('content', {}).get('en-US', '')
        slug = fields.get('slug', {}).get('en-US', '')
        
        # Extract dates
        created_at = sys.get('createdAt')
        updated_at = sys.get('updatedAt')
        published_at = sys.get('publishedAt')
        
        publish_date = None
        if published_at:
            try:
                publish_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        modified_date = None
        if updated_at:
            try:
                modified_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        # Determine content type
        contentful_type = sys.get('contentType', {}).get('sys', {}).get('id', 'article')
        content_type = ContentType.ARTICLE  # Default
        for ct, cf_type in self.content_type_mapping.items():
            if cf_type == contentful_type:
                try:
                    content_type = ContentType(ct)
                    break
                except ValueError:
                    pass
        
        # Extract optional fields
        meta_title = fields.get('metaTitle', {}).get('en-US')
        meta_description = fields.get('metaDescription', {}).get('en-US')
        canonical_url = fields.get('canonicalUrl', {}).get('en-US')
        author = fields.get('author', {}).get('en-US')
        categories = fields.get('categories', {}).get('en-US', [])
        tags = fields.get('tags', {}).get('en-US', [])
        featured_image_url = fields.get('featuredImageUrl', {}).get('en-US')
        featured_image_alt = fields.get('featuredImageAlt', {}).get('en-US')
        schema_markup = fields.get('schemaMarkup', {}).get('en-US')
        
        # Extract custom fields
        known_fields = {
            'title', 'slug', 'content', 'metaTitle', 'metaDescription',
            'canonicalUrl', 'author', 'categories', 'tags',
            'featuredImageUrl', 'featuredImageAlt', 'schemaMarkup'
        }
        custom_fields = {}
        for key, value in fields.items():
            if key not in known_fields and isinstance(value, dict) and 'en-US' in value:
                custom_fields[key] = value['en-US']
        
        return ContentItem(
            title=title,
            content=content,
            content_type=content_type,
            slug=slug,
            meta_title=meta_title,
            meta_description=meta_description,
            canonical_url=canonical_url,
            status=self._map_contentful_status(entry_data),
            author=author,
            publish_date=publish_date,
            modified_date=modified_date,
            categories=categories if isinstance(categories, list) else [],
            tags=tags if isinstance(tags, list) else [],
            featured_image_url=featured_image_url,
            featured_image_alt=featured_image_alt,
            schema_markup=schema_markup,
            custom_fields=custom_fields,
            external_id=sys.get('id', ''),
        )
    
    async def publish_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Publish content to Contentful."""
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
                    message=f"Dry run: Would publish '{content.title}' to Contentful",
                    status=content.status
                )
            
            # Get Contentful content type
            contentful_content_type = self.content_type_mapping.get(
                content.content_type.value,
                'article'
            )
            
            # Prepare Contentful data
            contentful_data = self._prepare_contentful_data(content)
            
            # Create entry
            response = await self._make_management_request(
                'POST',
                f'/entries',
                contentful_data,
                headers={'X-Contentful-Content-Type': contentful_content_type}
            )
            
            entry_id = response.get('sys', {}).get('id')
            
            # Publish if status is published
            if content.status == PublishStatus.PUBLISHED:
                version = response.get('sys', {}).get('version')
                publish_headers = {'X-Contentful-Version': str(version)}
                
                await self._make_management_request(
                    'PUT',
                    f'/entries/{entry_id}/published',
                    headers=publish_headers
                )
            
            logger.info(f"Published content to Contentful: ID {entry_id}")
            
            return PublishResult(
                success=True,
                external_id=entry_id,
                url=f"https://app.contentful.com/spaces/{self.space_id}/entries/{entry_id}",
                status=content.status,
                message=f"Successfully published to Contentful (ID: {entry_id})",
                published_at=datetime.now(timezone.utc),
                cms_response=response
            )
            
        except Exception as e:
            logger.error(f"Failed to publish to Contentful: {e}")
            result = PublishResult(success=False, message=f"Contentful publish failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def update_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Update existing content in Contentful."""
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
                    message=f"Dry run: Would update Contentful entry {content.external_id}",
                    status=content.status
                )
            
            # Get current entry to get version
            current_entry = await self._make_management_request(
                'GET',
                f'/entries/{content.external_id}'
            )
            
            current_version = current_entry.get('sys', {}).get('version')
            
            # Prepare Contentful data
            contentful_data = self._prepare_contentful_data(content)
            
            # Update entry
            response = await self._make_management_request(
                'PUT',
                f'/entries/{content.external_id}',
                contentful_data,
                headers={'X-Contentful-Version': str(current_version)}
            )
            
            # Publish if status is published
            if content.status == PublishStatus.PUBLISHED:
                new_version = response.get('sys', {}).get('version')
                publish_headers = {'X-Contentful-Version': str(new_version)}
                
                await self._make_management_request(
                    'PUT',
                    f'/entries/{content.external_id}/published',
                    headers=publish_headers
                )
            
            logger.info(f"Updated Contentful entry: {content.external_id}")
            
            return PublishResult(
                success=True,
                external_id=content.external_id,
                url=f"https://app.contentful.com/spaces/{self.space_id}/entries/{content.external_id}",
                status=content.status,
                message=f"Successfully updated Contentful entry (ID: {content.external_id})",
                published_at=datetime.now(timezone.utc),
                cms_response=response
            )
            
        except Exception as e:
            logger.error(f"Failed to update Contentful content: {e}")
            result = PublishResult(success=False, message=f"Contentful update failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def delete_content(self, external_id: str, dry_run: bool = False) -> PublishResult:
        """Delete content from Contentful."""
        try:
            if dry_run:
                return PublishResult(
                    success=True,
                    message=f"Dry run: Would delete Contentful entry {external_id}"
                )
            
            # Unpublish first if published
            try:
                await self._make_management_request('DELETE', f'/entries/{external_id}/published')
            except PublishError:
                # Entry might not be published
                pass
            
            # Delete entry
            await self._make_management_request('DELETE', f'/entries/{external_id}')
            
            logger.info(f"Deleted Contentful entry: {external_id}")
            
            return PublishResult(
                success=True,
                message=f"Successfully deleted Contentful entry (ID: {external_id})"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete Contentful content: {e}")
            result = PublishResult(success=False, message=f"Contentful delete failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def get_content(self, external_id: str) -> Optional[ContentItem]:
        """Retrieve content from Contentful."""
        try:
            # Try management API first (includes drafts)
            try:
                response = await self._make_management_request('GET', f'/entries/{external_id}')
                return self._parse_contentful_entry(response)
            except PublishError:
                # Try delivery API (published only)
                try:
                    response = await self._make_delivery_request(f'/entries/{external_id}')
                    return self._parse_contentful_entry(response)
                except CMSError:
                    return None
            
        except Exception as e:
            logger.error(f"Failed to get Contentful content {external_id}: {e}")
            return None
    
    async def list_content(self, content_type: Optional[ContentType] = None, limit: int = 100) -> List[ContentItem]:
        """List content from Contentful."""
        try:
            params = {
                'limit': min(limit, 1000),  # Contentful max is 1000
                'order': '-sys.updatedAt'
            }
            
            # Filter by content type if specified
            if content_type:
                contentful_content_type = self.content_type_mapping.get(content_type.value)
                if contentful_content_type:
                    params['content_type'] = contentful_content_type
            
            # Get entries from management API (includes drafts)
            response = await self._make_management_request('GET', '/entries', params=params)
            
            content_items = []
            items = response.get('items', [])
            
            for item_data in items:
                try:
                    content_item = self._parse_contentful_entry(item_data)
                    content_items.append(content_item)
                except Exception as e:
                    logger.warning(f"Failed to parse Contentful entry: {e}")
                    continue
            
            return content_items
            
        except Exception as e:
            logger.error(f"Failed to list Contentful content: {e}")
            return []
    
    async def upload_media(self, file_path: Path, alt_text: str = "") -> Optional[str]:
        """Upload media file to Contentful."""
        try:
            if not file_path.exists():
                logger.error(f"Media file not found: {file_path}")
                return None
            
            await self._ensure_session()
            
            # First, upload the file to get an upload URL
            upload_response = await self._make_management_request(
                'POST',
                '/uploads',
                headers={'Content-Type': 'application/octet-stream'}
            )
            
            upload_url = upload_response.get('sys', {}).get('id')
            if not upload_url:
                raise PublishError("Failed to get upload URL from Contentful")
            
            # Upload the actual file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            upload_endpoint = f"/uploads/{upload_url}"
            await self._make_management_request(
                'PUT',
                upload_endpoint,
                data=file_content,
                headers={'Content-Type': 'application/octet-stream'}
            )
            
            # Create asset
            asset_data = {
                'fields': {
                    'title': {'en-US': file_path.stem},
                    'file': {
                        'en-US': {
                            'fileName': file_path.name,
                            'contentType': f'image/{file_path.suffix[1:]}',  # Remove dot
                            'uploadFrom': {
                                'sys': {
                                    'type': 'Link',
                                    'linkType': 'Upload',
                                    'id': upload_url
                                }
                            }
                        }
                    }
                }
            }
            
            if alt_text:
                asset_data['fields']['description'] = {'en-US': alt_text}
            
            asset_response = await self._make_management_request(
                'POST',
                '/assets',
                asset_data
            )
            
            asset_id = asset_response.get('sys', {}).get('id')
            asset_version = asset_response.get('sys', {}).get('version')
            
            # Process asset
            await self._make_management_request(
                'PUT',
                f'/assets/{asset_id}/files/en-US/process',
                headers={'X-Contentful-Version': str(asset_version)}
            )
            
            # Publish asset
            # Note: We need to wait for processing to complete, which is async
            # In a real implementation, you'd poll for completion
            
            # Return a Contentful CDN URL (this is a placeholder)
            asset_url = f"https://assets.ctfassets.net/{self.space_id}/{asset_id}/{file_path.name}"
            
            logger.info(f"Uploaded media to Contentful: {asset_url}")
            return asset_url
            
        except Exception as e:
            logger.error(f"Failed to upload media to Contentful: {e}")
            return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
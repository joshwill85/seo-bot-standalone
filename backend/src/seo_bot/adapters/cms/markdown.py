"""Markdown/MDX CMS adapter for static site generators."""

import logging
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .base import (
    CMSAdapter, CMSCapabilities, CMSError, PublishError, ValidationError,
    ContentItem, ContentType, PublishResult, PublishStatus
)

logger = logging.getLogger(__name__)


class MarkdownAdapter(CMSAdapter):
    """CMS adapter for Markdown/MDX files with frontmatter."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Markdown adapter.
        
        Expected config:
        - content_dir: Path to content directory
        - public_dir: Path to public/static directory (optional)
        - assets_dir: Path to assets directory (optional)
        - use_mdx: Whether to use MDX format (default: False)
        - frontmatter_format: 'yaml' or 'json' (default: 'yaml')
        - date_format: Date format for frontmatter (default: ISO format)
        """
        super().__init__(config)
        
        self.content_dir = Path(config.get('content_dir', './content'))
        self.public_dir = Path(config.get('public_dir', './public'))
        self.assets_dir = Path(config.get('assets_dir', './assets'))
        self.use_mdx = config.get('use_mdx', False)
        self.frontmatter_format = config.get('frontmatter_format', 'yaml')
        self.date_format = config.get('date_format', 'iso')
        
        # Ensure directories exist
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        if self.public_dir:
            self.public_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def name(self) -> str:
        """Return the name of this CMS adapter."""
        return "Markdown" + ("X" if self.use_mdx else "")
    
    def _get_capabilities(self) -> CMSCapabilities:
        """Return the capabilities of the Markdown adapter."""
        return CMSCapabilities(
            supports_drafts=True,
            supports_scheduling=True,
            supports_categories=True,
            supports_tags=True,
            supports_custom_fields=True,
            supports_media_upload=True,
            supports_bulk_operations=True,
            supports_revisions=False,
            supports_redirects=False,
            max_content_length=None,  # No limit for markdown files
            supported_content_types=[ContentType.ARTICLE, ContentType.PAGE, ContentType.AUTHOR]
        )
    
    async def authenticate(self) -> bool:
        """Authentication not required for file system."""
        self._authenticated = True
        return True
    
    async def test_connection(self) -> bool:
        """Test that content directory is accessible."""
        try:
            return self.content_dir.exists() and self.content_dir.is_dir()
        except Exception as e:
            logger.error(f"Failed to access content directory: {e}")
            return False
    
    def _get_file_extension(self) -> str:
        """Get the file extension based on format."""
        return '.mdx' if self.use_mdx else '.md'
    
    def _get_content_path(self, content: ContentItem) -> Path:
        """Get the file path for content item."""
        extension = self._get_file_extension()
        
        # Organize by content type
        if content.content_type == ContentType.ARTICLE:
            base_dir = self.content_dir / 'articles'
        elif content.content_type == ContentType.PAGE:
            base_dir = self.content_dir / 'pages'
        elif content.content_type == ContentType.AUTHOR:
            base_dir = self.content_dir / 'authors'
        else:
            base_dir = self.content_dir / content.content_type.value
        
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Use slug as filename
        filename = f"{content.slug}{extension}"
        return base_dir / filename
    
    def _format_date(self, date: datetime) -> str:
        """Format date according to configuration."""
        if self.date_format == 'iso':
            return date.isoformat()
        elif self.date_format == 'date':
            return date.strftime('%Y-%m-%d')
        elif self.date_format == 'datetime':
            return date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return date.isoformat()
    
    def _create_frontmatter(self, content: ContentItem) -> str:
        """Create frontmatter for the content."""
        frontmatter = {
            'title': content.title,
            'slug': content.slug,
            'type': content.content_type.value,
            'status': content.status.value
        }
        
        # Add optional fields
        if content.meta_title:
            frontmatter['metaTitle'] = content.meta_title
        
        if content.meta_description:
            frontmatter['metaDescription'] = content.meta_description
        
        if content.canonical_url:
            frontmatter['canonicalUrl'] = content.canonical_url
        
        if content.author:
            frontmatter['author'] = content.author
        
        if content.publish_date:
            frontmatter['publishDate'] = self._format_date(content.publish_date)
        
        if content.modified_date:
            frontmatter['modifiedDate'] = self._format_date(content.modified_date)
        
        if content.categories:
            frontmatter['categories'] = content.categories
        
        if content.tags:
            frontmatter['tags'] = content.tags
        
        if content.featured_image_url:
            frontmatter['featuredImage'] = {
                'url': content.featured_image_url,
                'alt': content.featured_image_alt or ''
            }
        
        if content.schema_markup:
            frontmatter['schema'] = content.schema_markup
        
        # Add custom fields
        if content.custom_fields:
            frontmatter.update(content.custom_fields)
        
        # Format frontmatter
        if self.frontmatter_format == 'yaml':
            frontmatter_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            return f"---\n{frontmatter_str}---\n\n"
        elif self.frontmatter_format == 'json':
            frontmatter_str = json.dumps(frontmatter, indent=2, ensure_ascii=False)
            return f"---\n{frontmatter_str}\n---\n\n"
        else:
            raise ValueError(f"Unsupported frontmatter format: {self.frontmatter_format}")
    
    def _parse_frontmatter(self, file_content: str) -> tuple[Dict[str, Any], str]:
        """Parse frontmatter from file content."""
        if not file_content.startswith('---'):
            return {}, file_content
        
        # Find the end of frontmatter
        parts = file_content.split('---', 2)
        if len(parts) < 3:
            return {}, file_content
        
        frontmatter_content = parts[1].strip()
        content = parts[2].strip()
        
        try:
            if self.frontmatter_format == 'yaml':
                frontmatter = yaml.safe_load(frontmatter_content) or {}
            elif self.frontmatter_format == 'json':
                frontmatter = json.loads(frontmatter_content)
            else:
                frontmatter = {}
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
            frontmatter = {}
        
        return frontmatter, content
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string from frontmatter."""
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try date format
                return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    # Try datetime format
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Unable to parse date: {date_str}")
                    return None
    
    def _frontmatter_to_content_item(self, frontmatter: Dict[str, Any], content: str, file_path: Path) -> ContentItem:
        """Convert frontmatter and content to ContentItem."""
        
        # Parse dates
        publish_date = None
        if 'publishDate' in frontmatter:
            publish_date = self._parse_date(frontmatter['publishDate'])
        
        modified_date = None
        if 'modifiedDate' in frontmatter:
            modified_date = self._parse_date(frontmatter['modifiedDate'])
        
        # Parse featured image
        featured_image_url = None
        featured_image_alt = None
        if 'featuredImage' in frontmatter:
            if isinstance(frontmatter['featuredImage'], dict):
                featured_image_url = frontmatter['featuredImage'].get('url')
                featured_image_alt = frontmatter['featuredImage'].get('alt')
            else:
                featured_image_url = str(frontmatter['featuredImage'])
        
        # Parse content type
        content_type_str = frontmatter.get('type', 'article')
        try:
            content_type = ContentType(content_type_str)
        except ValueError:
            content_type = ContentType.ARTICLE
        
        # Parse status
        status_str = frontmatter.get('status', 'draft')
        try:
            status = PublishStatus(status_str)
        except ValueError:
            status = PublishStatus.DRAFT
        
        # Custom fields (exclude known frontmatter fields)
        known_fields = {
            'title', 'slug', 'type', 'status', 'metaTitle', 'metaDescription',
            'canonicalUrl', 'author', 'publishDate', 'modifiedDate', 'categories',
            'tags', 'featuredImage', 'schema'
        }
        custom_fields = {k: v for k, v in frontmatter.items() if k not in known_fields}
        
        return ContentItem(
            title=frontmatter.get('title', ''),
            content=content,
            content_type=content_type,
            slug=frontmatter.get('slug', ''),
            meta_title=frontmatter.get('metaTitle'),
            meta_description=frontmatter.get('metaDescription'),
            canonical_url=frontmatter.get('canonicalUrl'),
            status=status,
            author=frontmatter.get('author'),
            publish_date=publish_date,
            modified_date=modified_date,
            categories=frontmatter.get('categories', []),
            tags=frontmatter.get('tags', []),
            featured_image_url=featured_image_url,
            featured_image_alt=featured_image_alt,
            schema_markup=frontmatter.get('schema'),
            custom_fields=custom_fields,
            external_id=str(file_path.relative_to(self.content_dir)),
            source_file=file_path
        )
    
    async def publish_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Publish content as Markdown file."""
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
            
            # Generate file path
            file_path = self._get_content_path(content)
            
            if dry_run:
                return PublishResult(
                    success=True,
                    external_id=str(file_path.relative_to(self.content_dir)),
                    url=str(file_path),
                    status=content.status,
                    message=f"Dry run: Would create file {file_path}"
                )
            
            # Create backup if file exists
            backup_path = None
            if file_path.exists():
                backup_path = file_path.with_suffix(f'.backup-{int(datetime.now().timestamp())}.md')
                shutil.copy2(file_path, backup_path)
            
            # Create frontmatter and content
            frontmatter = self._create_frontmatter(content)
            full_content = frontmatter + content.content
            
            # Write file
            file_path.write_text(full_content, encoding='utf-8')
            
            logger.info(f"Published content to {file_path}")
            
            return PublishResult(
                success=True,
                external_id=str(file_path.relative_to(self.content_dir)),
                url=str(file_path),
                status=content.status,
                message=f"Successfully published to {file_path}",
                published_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to publish content: {e}")
            result = PublishResult(success=False, message=f"Publish failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def update_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Update existing content (same as publish for file-based system)."""
        return await self.publish_content(content, dry_run)
    
    async def delete_content(self, external_id: str, dry_run: bool = False) -> PublishResult:
        """Delete content file."""
        try:
            file_path = self.content_dir / external_id
            
            if not file_path.exists():
                result = PublishResult(success=False, message=f"File not found: {file_path}")
                result.add_error("File does not exist")
                return result
            
            if dry_run:
                return PublishResult(
                    success=True,
                    message=f"Dry run: Would delete file {file_path}"
                )
            
            # Create backup before deletion
            backup_path = file_path.with_suffix(f'.deleted-{int(datetime.now().timestamp())}.md')
            shutil.move(file_path, backup_path)
            
            logger.info(f"Deleted content file {file_path} (backed up to {backup_path})")
            
            return PublishResult(
                success=True,
                message=f"Successfully deleted {file_path}"
            )
            
        except Exception as e:
            logger.error(f"Failed to delete content: {e}")
            result = PublishResult(success=False, message=f"Delete failed: {str(e)}")
            result.add_error(str(e))
            return result
    
    async def get_content(self, external_id: str) -> Optional[ContentItem]:
        """Retrieve content from file."""
        try:
            file_path = self.content_dir / external_id
            
            if not file_path.exists():
                return None
            
            file_content = file_path.read_text(encoding='utf-8')
            frontmatter, content = self._parse_frontmatter(file_content)
            
            return self._frontmatter_to_content_item(frontmatter, content, file_path)
            
        except Exception as e:
            logger.error(f"Failed to get content {external_id}: {e}")
            return None
    
    async def list_content(self, content_type: Optional[ContentType] = None, limit: int = 100) -> List[ContentItem]:
        """List content files."""
        try:
            content_items = []
            extension = self._get_file_extension()
            
            # Search pattern based on content type
            if content_type:
                search_pattern = f"{content_type.value}/**/*{extension}"
            else:
                search_pattern = f"**/*{extension}"
            
            # Find matching files
            matching_files = list(self.content_dir.glob(search_pattern))
            
            # Sort by modification time (newest first)
            matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Limit results
            matching_files = matching_files[:limit]
            
            # Parse each file
            for file_path in matching_files:
                try:
                    file_content = file_path.read_text(encoding='utf-8')
                    frontmatter, content = self._parse_frontmatter(file_content)
                    
                    content_item = self._frontmatter_to_content_item(frontmatter, content, file_path)
                    content_items.append(content_item)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse file {file_path}: {e}")
                    continue
            
            return content_items
            
        except Exception as e:
            logger.error(f"Failed to list content: {e}")
            return []
    
    async def upload_media(self, file_path: Path, alt_text: str = "") -> Optional[str]:
        """Upload media file to assets directory."""
        try:
            if not file_path.exists():
                logger.error(f"Media file not found: {file_path}")
                return None
            
            # Create assets subdirectory based on type
            file_extension = file_path.suffix.lower()
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                assets_subdir = self.assets_dir / 'images'
            elif file_extension in ['.pdf', '.doc', '.docx', '.txt']:
                assets_subdir = self.assets_dir / 'documents'
            else:
                assets_subdir = self.assets_dir / 'files'
            
            assets_subdir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename if needed
            destination = assets_subdir / file_path.name
            counter = 1
            while destination.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                destination = assets_subdir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Copy file
            shutil.copy2(file_path, destination)
            
            # Return relative URL
            relative_path = destination.relative_to(self.assets_dir)
            url = f"/assets/{relative_path.as_posix()}"
            
            logger.info(f"Uploaded media file to {destination}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload media file: {e}")
            return None
    
    async def bulk_publish(self, content_items: List[ContentItem], dry_run: bool = False) -> List[PublishResult]:
        """Publish multiple content items."""
        results = []
        
        for content in content_items:
            result = await self.publish_content(content, dry_run)
            results.append(result)
        
        # Log summary
        successful = len([r for r in results if r.success])
        failed = len(results) - successful
        
        logger.info(f"Bulk publish completed: {successful} successful, {failed} failed")
        
        return results
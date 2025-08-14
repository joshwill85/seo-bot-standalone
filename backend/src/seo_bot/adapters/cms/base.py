"""Base CMS adapter interface and common utilities."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class PublishStatus(Enum):
    """Content publishing status."""
    DRAFT = "draft"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    ARCHIVED = "archived"
    FAILED = "failed"


class ContentType(Enum):
    """Content type definitions."""
    ARTICLE = "article"
    PAGE = "page"
    PRODUCT = "product"
    CATEGORY = "category"
    AUTHOR = "author"
    MEDIA = "media"


class CMSError(Exception):
    """Base exception for CMS adapter errors."""
    pass


class AuthenticationError(CMSError):
    """Authentication failed with CMS."""
    pass


class ValidationError(CMSError):
    """Content validation failed."""
    pass


class PublishError(CMSError):
    """Publishing operation failed."""
    pass


@dataclass
class ContentItem:
    """Represents a content item for CMS publishing."""
    
    # Basic metadata
    title: str
    content: str
    content_type: ContentType
    slug: str
    
    # SEO metadata
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    
    # Publishing details
    status: PublishStatus = PublishStatus.DRAFT
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    
    # Categories and tags
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Featured media
    featured_image_url: Optional[str] = None
    featured_image_alt: Optional[str] = None
    
    # Schema and structured data
    schema_markup: Optional[Dict[str, Any]] = None
    
    # Custom fields for CMS-specific data
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Internal tracking
    external_id: Optional[str] = None  # CMS-specific ID
    source_file: Optional[Path] = None  # Original file path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type.value,
            "slug": self.slug,
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "canonical_url": self.canonical_url,
            "status": self.status.value,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "modified_date": self.modified_date.isoformat() if self.modified_date else None,
            "categories": self.categories,
            "tags": self.tags,
            "featured_image_url": self.featured_image_url,
            "featured_image_alt": self.featured_image_alt,
            "schema_markup": self.schema_markup,
            "custom_fields": self.custom_fields,
            "external_id": self.external_id,
            "source_file": str(self.source_file) if self.source_file else None
        }


@dataclass
class PublishResult:
    """Result of a publishing operation."""
    
    success: bool
    external_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[PublishStatus] = None
    message: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    published_at: Optional[datetime] = None
    cms_response: Optional[Dict[str, Any]] = None
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


@dataclass 
class CMSCapabilities:
    """Describes CMS adapter capabilities."""
    
    supports_drafts: bool = True
    supports_scheduling: bool = True
    supports_categories: bool = True
    supports_tags: bool = True
    supports_custom_fields: bool = True
    supports_media_upload: bool = True
    supports_bulk_operations: bool = False
    supports_revisions: bool = False
    supports_redirects: bool = False
    max_content_length: Optional[int] = None
    supported_content_types: List[ContentType] = field(default_factory=lambda: [ContentType.ARTICLE, ContentType.PAGE])


class CMSAdapter(ABC):
    """Abstract base class for CMS adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the CMS adapter with configuration."""
        self.config = config
        self._authenticated = False
        self._capabilities: Optional[CMSCapabilities] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this CMS adapter."""
        pass
    
    @property
    def capabilities(self) -> CMSCapabilities:
        """Return the capabilities of this CMS adapter."""
        if self._capabilities is None:
            self._capabilities = self._get_capabilities()
        return self._capabilities
    
    @abstractmethod
    def _get_capabilities(self) -> CMSCapabilities:
        """Return the capabilities of this CMS implementation."""
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the CMS."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the CMS."""
        pass
    
    @abstractmethod
    async def publish_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Publish content to the CMS."""
        pass
    
    @abstractmethod
    async def update_content(self, content: ContentItem, dry_run: bool = False) -> PublishResult:
        """Update existing content in the CMS."""
        pass
    
    @abstractmethod
    async def delete_content(self, external_id: str, dry_run: bool = False) -> PublishResult:
        """Delete content from the CMS."""
        pass
    
    @abstractmethod
    async def get_content(self, external_id: str) -> Optional[ContentItem]:
        """Retrieve content from the CMS."""
        pass
    
    @abstractmethod
    async def list_content(self, content_type: Optional[ContentType] = None, limit: int = 100) -> List[ContentItem]:
        """List content from the CMS."""
        pass
    
    async def upload_media(self, file_path: Path, alt_text: str = "") -> Optional[str]:
        """Upload media file and return URL."""
        if not self.capabilities.supports_media_upload:
            raise NotImplementedError("Media upload not supported by this CMS")
        return None
    
    async def bulk_publish(self, content_items: List[ContentItem], dry_run: bool = False) -> List[PublishResult]:
        """Publish multiple content items."""
        if not self.capabilities.supports_bulk_operations:
            # Fall back to individual publishing
            results = []
            for content in content_items:
                try:
                    result = await self.publish_content(content, dry_run)
                    results.append(result)
                except Exception as e:
                    result = PublishResult(success=False, message=str(e))
                    result.add_error(f"Failed to publish {content.title}: {e}")
                    results.append(result)
            return results
        
        # Implement bulk publishing in subclass
        raise NotImplementedError("Bulk operations not implemented")
    
    def validate_content(self, content: ContentItem) -> List[str]:
        """Validate content before publishing."""
        errors = []
        
        # Basic validation
        if not content.title.strip():
            errors.append("Title is required")
        
        if not content.content.strip():
            errors.append("Content is required")
        
        if not content.slug.strip():
            errors.append("Slug is required")
        
        # Length validation
        if self.capabilities.max_content_length:
            if len(content.content) > self.capabilities.max_content_length:
                errors.append(f"Content exceeds maximum length of {self.capabilities.max_content_length} characters")
        
        # Content type validation
        if content.content_type not in self.capabilities.supported_content_types:
            errors.append(f"Content type {content.content_type.value} not supported")
        
        # SEO validation
        if content.meta_title and len(content.meta_title) > 60:
            errors.append("Meta title should be 60 characters or less")
        
        if content.meta_description and len(content.meta_description) > 160:
            errors.append("Meta description should be 160 characters or less")
        
        return errors
    
    def prepare_content_for_publish(self, content: ContentItem) -> ContentItem:
        """Prepare content for publishing (set defaults, clean up, etc.)."""
        # Set default meta title if not provided
        if not content.meta_title:
            content.meta_title = content.title
        
        # Set modified date
        content.modified_date = datetime.now(timezone.utc)
        
        # Set publish date if not set and status is published
        if content.status == PublishStatus.PUBLISHED and not content.publish_date:
            content.publish_date = datetime.now(timezone.utc)
        
        return content
    
    async def backup_before_publish(self, content: ContentItem) -> Optional[str]:
        """Create backup before publishing (optional)."""
        # Default implementation does nothing
        # Override in subclasses that support backups
        return None
    
    async def rollback_publish(self, backup_id: str) -> bool:
        """Rollback a failed publish operation (optional)."""
        # Default implementation does nothing
        # Override in subclasses that support rollbacks
        return False
    
    def generate_slug(self, title: str, max_length: int = 50) -> str:
        """Generate URL-friendly slug from title."""
        import re
        
        # Convert to lowercase
        slug = title.lower()
        
        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Trim and remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Truncate to max length
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip('-')
        
        return slug or "untitled"
    
    def extract_excerpts(self, content: str, length: int = 160) -> str:
        """Extract excerpt from content."""
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Truncate to specified length
        if len(text) <= length:
            return text
        
        # Find last complete word within length limit
        truncated = text[:length]
        last_space = truncated.rfind(' ')
        
        if last_space > length * 0.8:  # If we can keep most of the text
            return text[:last_space] + '...'
        else:
            return truncated + '...'
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"{self.name} CMS Adapter"
    
    def __repr__(self) -> str:
        """Developer representation of the adapter."""
        return f"{self.__class__.__name__}(authenticated={self._authenticated})"
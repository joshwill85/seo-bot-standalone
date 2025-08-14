"""Internal linking and knowledge graph modules for SEO-Bot."""

from .entities import (
    EntityLinkingManager,
    KnowledgeGraph,
    EntityExtractor,
    EntityNormalizer,
    RelationshipExtractor,
    EntityPageGenerator,
    Entity,
    EntityRelationship,
    EntityMention,
    EntityPage,
    create_entity_manager,
)

__all__ = [
    # Main manager
    "EntityLinkingManager",
    "create_entity_manager",
    
    # Core components
    "KnowledgeGraph",
    "EntityExtractor",
    "EntityNormalizer",
    "RelationshipExtractor",
    "EntityPageGenerator",
    
    # Data classes
    "Entity",
    "EntityRelationship",
    "EntityMention",
    "EntityPage",
]
"""Internal knowledge graph and entity linking system."""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote

import networkx as nx
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db_session
from ..logging import get_logger, LoggerMixin
from ..models import Page, Project, InternalLink


@dataclass
class Entity:
    """Represents a named entity in the knowledge graph."""
    name: str
    entity_type: str  # PERSON, ORG, GPE, PRODUCT, CONCEPT, etc.
    aliases: List[str]
    description: Optional[str] = None
    canonical_url: Optional[str] = None
    same_as_urls: List[str] = None  # External references (Wikipedia, Wikidata, etc.)
    confidence_score: float = 1.0
    mentions_count: int = 0
    pages_mentioned: List[str] = None  # Page IDs where entity is mentioned
    
    def __post_init__(self):
        if self.same_as_urls is None:
            self.same_as_urls = []
        if self.pages_mentioned is None:
            self.pages_mentioned = []


@dataclass
class EntityRelationship:
    """Represents a relationship between two entities."""
    source_entity: str
    target_entity: str
    relationship_type: str  # "related_to", "part_of", "instance_of", "caused_by", etc.
    confidence_score: float
    evidence_pages: List[str]  # Page IDs where relationship was observed
    context: Optional[str] = None


@dataclass
class EntityMention:
    """Represents a mention of an entity in content."""
    entity_name: str
    page_id: str
    position: int  # Character position in content
    context: str  # Surrounding text
    confidence_score: float
    anchor_text: str  # Text used to mention the entity
    is_linked: bool = False
    link_target: Optional[str] = None


@dataclass
class EntityPage:
    """Represents a dedicated page for an entity."""
    entity_name: str
    page_id: str
    url: str
    title: str
    description: str
    schema_type: str  # Person, Organization, Place, Thing, etc.
    related_entities: List[str]
    internal_links_in: int
    internal_links_out: int
    content_quality_score: float


class EntityExtractor:
    """Extracts and normalizes entities from content."""
    
    def __init__(self):
        """Initialize entity extractor."""
        self.logger = get_logger(self.__class__.__name__)
        self.nlp = None
        self._setup_nlp()
    
    def _setup_nlp(self):
        """Setup spaCy NLP pipeline for entity extraction."""
        try:
            import spacy
            try:
                self.nlp = spacy.load("en_core_web_sm")
                self.logger.info("Loaded spaCy en_core_web_sm for entity extraction")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_md")
                    self.logger.info("Loaded spaCy en_core_web_md for entity extraction")
                except OSError:
                    self.logger.warning("No spaCy models found, using pattern-based extraction")
                    self.nlp = None
        except ImportError:
            self.logger.warning("spaCy not available, using pattern-based entity extraction")
            self.nlp = None
    
    def extract_entities(self, text: str, page_id: str) -> List[EntityMention]:
        """
        Extract entities from text content.
        
        Args:
            text: Text content to analyze
            page_id: ID of the page containing the text
            
        Returns:
            List of entity mentions found in the text
        """
        if self.nlp:
            return self._extract_entities_spacy(text, page_id)
        else:
            return self._extract_entities_patterns(text, page_id)
    
    def _extract_entities_spacy(self, text: str, page_id: str) -> List[EntityMention]:
        """Extract entities using spaCy NER."""
        entities = []
        
        if len(text) > 1000000:
            text = text[:1000000]
        
        doc = self.nlp(text)
        
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW']:
                # Get surrounding context
                start_context = max(0, ent.start_char - 100)
                end_context = min(len(text), ent.end_char + 100)
                context = text[start_context:end_context].strip()
                
                # Calculate confidence based on entity type and length
                confidence = self._calculate_entity_confidence(ent.text, ent.label_)
                
                entities.append(EntityMention(
                    entity_name=ent.text.strip(),
                    page_id=page_id,
                    position=ent.start_char,
                    context=context,
                    confidence_score=confidence,
                    anchor_text=ent.text.strip()
                ))
        
        # Also extract noun phrases as potential concepts
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 3 and len(chunk.text) < 50:
                # Filter for meaningful concepts
                if any(token.pos_ in ['NOUN', 'PROPN'] for token in chunk):
                    # Skip if already captured as named entity
                    if not any(abs(chunk.start_char - ent.position) < 10 for ent in entities):
                        start_context = max(0, chunk.start_char - 100)
                        end_context = min(len(text), chunk.end_char + 100)
                        context = text[start_context:end_context].strip()
                        
                        entities.append(EntityMention(
                            entity_name=chunk.text.strip(),
                            page_id=page_id,
                            position=chunk.start_char,
                            context=context,
                            confidence_score=0.6,  # Lower confidence for concepts
                            anchor_text=chunk.text.strip()
                        ))
        
        return entities
    
    def _extract_entities_patterns(self, text: str, page_id: str) -> List[EntityMention]:
        """Fallback pattern-based entity extraction."""
        entities = []
        
        # Pattern for proper nouns (potential entities)
        proper_noun_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
        
        for match in proper_noun_pattern.finditer(text):
            entity_text = match.group().strip()
            
            # Skip common words
            if entity_text.lower() in ['The', 'This', 'That', 'Here', 'There']:
                continue
            
            # Get context
            start_context = max(0, match.start() - 100)
            end_context = min(len(text), match.end() + 100)
            context = text[start_context:end_context].strip()
            
            entities.append(EntityMention(
                entity_name=entity_text,
                page_id=page_id,
                position=match.start(),
                context=context,
                confidence_score=0.5,  # Lower confidence for pattern matching
                anchor_text=entity_text
            ))
        
        return entities
    
    def _calculate_entity_confidence(self, entity_text: str, entity_label: str) -> float:
        """Calculate confidence score for an entity."""
        base_confidence = 0.8
        
        # Boost confidence for certain entity types
        if entity_label in ['PERSON', 'ORG', 'GPE']:
            base_confidence = 0.9
        
        # Adjust based on entity length
        if len(entity_text) < 3:
            base_confidence *= 0.5
        elif len(entity_text) > 50:
            base_confidence *= 0.7
        
        # Boost confidence for entities with multiple words
        if len(entity_text.split()) > 1:
            base_confidence *= 1.1
        
        return min(1.0, base_confidence)


class EntityNormalizer:
    """Normalizes and deduplicates entities."""
    
    def __init__(self):
        """Initialize entity normalizer."""
        self.logger = get_logger(self.__class__.__name__)
    
    def normalize_entities(self, entity_mentions: List[EntityMention]) -> List[Entity]:
        """
        Normalize entity mentions into canonical entities.
        
        Args:
            entity_mentions: List of entity mentions to normalize
            
        Returns:
            List of normalized entities
        """
        # Group mentions by normalized name
        entity_groups = defaultdict(list)
        
        for mention in entity_mentions:
            normalized_name = self._normalize_entity_name(mention.entity_name)
            entity_groups[normalized_name].append(mention)
        
        # Create canonical entities
        entities = []
        for canonical_name, mentions in entity_groups.items():
            if len(mentions) < 2:  # Skip entities with only one mention
                continue
            
            # Find the most common entity type
            entity_type = self._determine_entity_type(mentions)
            
            # Collect aliases
            aliases = list(set(mention.entity_name for mention in mentions))
            if canonical_name in aliases:
                aliases.remove(canonical_name)
            
            # Calculate average confidence
            avg_confidence = sum(m.confidence_score for m in mentions) / len(mentions)
            
            # Collect pages where entity is mentioned
            pages_mentioned = list(set(m.page_id for m in mentions))
            
            # Generate description from context
            description = self._generate_entity_description(mentions)
            
            entity = Entity(
                name=canonical_name,
                entity_type=entity_type,
                aliases=aliases,
                description=description,
                confidence_score=avg_confidence,
                mentions_count=len(mentions),
                pages_mentioned=pages_mentioned
            )
            
            entities.append(entity)
        
        return entities
    
    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for grouping."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', name.strip())
        
        # Handle common variations
        normalized = normalized.replace('&', 'and')
        normalized = re.sub(r'\b(Inc|LLC|Corp|Ltd)\.?\b', '', normalized, flags=re.IGNORECASE)
        normalized = normalized.strip()
        
        return normalized
    
    def _determine_entity_type(self, mentions: List[EntityMention]) -> str:
        """Determine the most likely entity type from mentions."""
        # This is a simplified implementation
        # In production, you might use more sophisticated classification
        
        entity_text = mentions[0].entity_name.lower()
        
        # Common patterns for entity types
        if any(word in entity_text for word in ['company', 'corp', 'inc', 'llc', 'ltd']):
            return 'ORG'
        elif any(word in entity_text for word in ['dr', 'prof', 'mr', 'ms', 'mrs']):
            return 'PERSON'
        elif entity_text.endswith(' city') or entity_text.endswith(' state'):
            return 'GPE'
        elif len(entity_text.split()) == 2 and entity_text.istitle():
            return 'PERSON'  # Likely a person name
        else:
            return 'CONCEPT'  # Generic concept
    
    def _generate_entity_description(self, mentions: List[EntityMention]) -> str:
        """Generate a description for an entity from its mentions."""
        # Collect contexts and find common patterns
        contexts = [mention.context for mention in mentions]
        
        # Simple description generation - in production, this could be more sophisticated
        first_context = contexts[0] if contexts else ""
        
        # Extract a sentence containing the entity
        sentences = re.split(r'[.!?]', first_context)
        entity_name = mentions[0].entity_name
        
        for sentence in sentences:
            if entity_name in sentence:
                return sentence.strip()
        
        return f"Entity mentioned {len(mentions)} times across content."


class RelationshipExtractor:
    """Extracts relationships between entities."""
    
    def __init__(self):
        """Initialize relationship extractor."""
        self.logger = get_logger(self.__class__.__name__)
    
    def extract_relationships(
        self, 
        entities: List[Entity], 
        entity_mentions: List[EntityMention]
    ) -> List[EntityRelationship]:
        """
        Extract relationships between entities.
        
        Args:
            entities: List of canonical entities
            entity_mentions: Original entity mentions
            
        Returns:
            List of entity relationships
        """
        relationships = []
        
        # Group mentions by page
        page_mentions = defaultdict(list)
        for mention in entity_mentions:
            page_mentions[mention.page_id].append(mention)
        
        # Look for co-occurrences within pages
        for page_id, mentions in page_mentions.items():
            if len(mentions) < 2:
                continue
            
            # Find entity pairs that appear close together
            for i, mention1 in enumerate(mentions):
                for mention2 in mentions[i+1:]:
                    # Check if mentions are close to each other
                    distance = abs(mention1.position - mention2.position)
                    
                    if distance < 500:  # Within 500 characters
                        relationship_type = self._classify_relationship(
                            mention1, mention2, distance
                        )
                        
                        if relationship_type:
                            # Find canonical entity names
                            entity1_name = self._find_canonical_name(mention1.entity_name, entities)
                            entity2_name = self._find_canonical_name(mention2.entity_name, entities)
                            
                            if entity1_name and entity2_name and entity1_name != entity2_name:
                                confidence = self._calculate_relationship_confidence(
                                    mention1, mention2, distance
                                )
                                
                                relationships.append(EntityRelationship(
                                    source_entity=entity1_name,
                                    target_entity=entity2_name,
                                    relationship_type=relationship_type,
                                    confidence_score=confidence,
                                    evidence_pages=[page_id],
                                    context=self._extract_relationship_context(mention1, mention2)
                                ))
        
        # Merge duplicate relationships
        return self._merge_relationships(relationships)
    
    def _classify_relationship(self, mention1: EntityMention, mention2: EntityMention, distance: int) -> Optional[str]:
        """Classify the relationship between two entity mentions."""
        # Simple relationship classification based on context
        combined_context = (mention1.context + " " + mention2.context).lower()
        
        # Look for relationship patterns
        if any(pattern in combined_context for pattern in ['ceo of', 'president of', 'founder of']):
            return 'leads'
        elif any(pattern in combined_context for pattern in ['works at', 'employed by', 'member of']):
            return 'member_of'
        elif any(pattern in combined_context for pattern in ['located in', 'based in', 'headquarters in']):
            return 'located_in'
        elif any(pattern in combined_context for pattern in ['owns', 'owns by', 'subsidiary of']):
            return 'owns'
        elif distance < 100:  # Very close mentions
            return 'related_to'
        
        return None
    
    def _find_canonical_name(self, mention_name: str, entities: List[Entity]) -> Optional[str]:
        """Find the canonical name for an entity mention."""
        for entity in entities:
            if mention_name == entity.name or mention_name in entity.aliases:
                return entity.name
        return None
    
    def _calculate_relationship_confidence(
        self, 
        mention1: EntityMention, 
        mention2: EntityMention, 
        distance: int
    ) -> float:
        """Calculate confidence score for a relationship."""
        base_confidence = 0.5
        
        # Boost confidence for closer mentions
        if distance < 100:
            base_confidence += 0.3
        elif distance < 200:
            base_confidence += 0.2
        
        # Boost confidence based on entity confidence
        entity_confidence = (mention1.confidence_score + mention2.confidence_score) / 2
        base_confidence += entity_confidence * 0.2
        
        return min(1.0, base_confidence)
    
    def _extract_relationship_context(self, mention1: EntityMention, mention2: EntityMention) -> str:
        """Extract context showing the relationship between entities."""
        # Find the span of text covering both mentions
        start_pos = min(mention1.position, mention2.position)
        end_pos = max(mention1.position + len(mention1.anchor_text), 
                     mention2.position + len(mention2.anchor_text))
        
        # Use the context from the first mention and expand as needed
        context = mention1.context
        if mention2.context and len(mention2.context) > len(context):
            context = mention2.context
        
        return context
    
    def _merge_relationships(self, relationships: List[EntityRelationship]) -> List[EntityRelationship]:
        """Merge duplicate relationships and aggregate evidence."""
        relationship_map = {}
        
        for rel in relationships:
            key = (rel.source_entity, rel.target_entity, rel.relationship_type)
            
            if key in relationship_map:
                existing = relationship_map[key]
                # Merge evidence
                existing.evidence_pages.extend(rel.evidence_pages)
                existing.evidence_pages = list(set(existing.evidence_pages))
                # Update confidence (take maximum)
                existing.confidence_score = max(existing.confidence_score, rel.confidence_score)
            else:
                relationship_map[key] = rel
        
        return list(relationship_map.values())


class KnowledgeGraph:
    """Manages the internal knowledge graph."""
    
    def __init__(self):
        """Initialize knowledge graph."""
        self.logger = get_logger(self.__class__.__name__)
        self.graph = nx.Graph()
        self.entities = {}  # entity_name -> Entity
        self.relationships = []  # List of EntityRelationship
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the knowledge graph."""
        self.entities[entity.name] = entity
        self.graph.add_node(entity.name, **asdict(entity))
        
        self.logger.debug(f"Added entity to knowledge graph: {entity.name}")
    
    def add_relationship(self, relationship: EntityRelationship) -> None:
        """Add a relationship to the knowledge graph."""
        self.relationships.append(relationship)
        
        # Add edge to NetworkX graph
        self.graph.add_edge(
            relationship.source_entity,
            relationship.target_entity,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence_score,
            evidence_pages=relationship.evidence_pages
        )
        
        self.logger.debug(
            f"Added relationship: {relationship.source_entity} -> {relationship.target_entity} "
            f"({relationship.relationship_type})"
        )
    
    def find_related_entities(self, entity_name: str, max_distance: int = 2) -> List[Tuple[str, int]]:
        """
        Find entities related to a given entity within a certain distance.
        
        Args:
            entity_name: Name of the entity to find relations for
            max_distance: Maximum distance in the graph
            
        Returns:
            List of (entity_name, distance) tuples
        """
        if entity_name not in self.graph:
            return []
        
        try:
            # Use NetworkX to find shortest paths
            path_lengths = nx.single_source_shortest_path_length(
                self.graph, entity_name, cutoff=max_distance
            )
            
            # Exclude the source entity itself
            related = [(name, distance) for name, distance in path_lengths.items() 
                      if name != entity_name]
            
            # Sort by distance, then by name
            related.sort(key=lambda x: (x[1], x[0]))
            
            return related
        
        except Exception as e:
            self.logger.error(f"Error finding related entities for {entity_name}: {e}")
            return []
    
    def get_entity_recommendations(self, page_content: str, limit: int = 10) -> List[str]:
        """
        Get entity recommendations for linking in page content.
        
        Args:
            page_content: Content to analyze for entity opportunities
            limit: Maximum number of recommendations
            
        Returns:
            List of entity names recommended for linking
        """
        recommendations = []
        content_lower = page_content.lower()
        
        # Find entities mentioned in content but not yet linked
        for entity_name, entity in self.entities.items():
            # Check if entity or its aliases are mentioned
            mentioned = False
            
            if entity_name.lower() in content_lower:
                mentioned = True
            else:
                for alias in entity.aliases:
                    if alias.lower() in content_lower:
                        mentioned = True
                        break
            
            if mentioned and entity.mentions_count > 2:  # Only recommend frequently mentioned entities
                recommendations.append(entity_name)
        
        # Sort by mention count (popularity)
        recommendations.sort(key=lambda name: self.entities[name].mentions_count, reverse=True)
        
        return recommendations[:limit]
    
    def export_graph(self, output_path: str, format: str = "json") -> None:
        """
        Export the knowledge graph to a file.
        
        Args:
            output_path: Path to save the graph
            format: Export format ("json", "gexf", "graphml")
        """
        try:
            if format == "json":
                graph_data = {
                    'entities': {name: asdict(entity) for name, entity in self.entities.items()},
                    'relationships': [asdict(rel) for rel in self.relationships]
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
            
            elif format == "gexf":
                nx.write_gexf(self.graph, output_path)
            
            elif format == "graphml":
                nx.write_graphml(self.graph, output_path)
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Knowledge graph exported to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to export knowledge graph: {e}")


class EntityPageGenerator:
    """Generates dedicated pages for entities."""
    
    def __init__(self):
        """Initialize entity page generator."""
        self.logger = get_logger(self.__class__.__name__)
    
    def generate_entity_page_content(self, entity: Entity, knowledge_graph: KnowledgeGraph) -> Dict:
        """
        Generate content for an entity page.
        
        Args:
            entity: Entity to generate page for
            knowledge_graph: Knowledge graph for finding related entities
            
        Returns:
            Dictionary with page content structure
        """
        # Find related entities
        related_entities = knowledge_graph.find_related_entities(entity.name, max_distance=2)
        related_names = [name for name, distance in related_entities[:10]]
        
        # Generate page structure
        page_content = {
            'title': entity.name,
            'slug': self._generate_slug(entity.name),
            'meta_description': self._generate_meta_description(entity),
            'schema_type': self._determine_schema_type(entity.entity_type),
            'content_sections': [
                {
                    'type': 'introduction',
                    'title': f"About {entity.name}",
                    'content': entity.description or f"{entity.name} is a {entity.entity_type.lower()} mentioned frequently across our content."
                },
                {
                    'type': 'overview',
                    'title': 'Overview',
                    'content': self._generate_overview_content(entity)
                },
                {
                    'type': 'related',
                    'title': 'Related Topics',
                    'content': self._generate_related_content(entity, related_names)
                }
            ],
            'internal_link_targets': related_names,
            'schema_data': self._generate_schema_data(entity),
            'same_as_urls': entity.same_as_urls
        }
        
        return page_content
    
    def _generate_slug(self, entity_name: str) -> str:
        """Generate URL slug for entity page."""
        slug = entity_name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def _generate_meta_description(self, entity: Entity) -> str:
        """Generate meta description for entity page."""
        if entity.description:
            desc = entity.description[:150]
            if len(entity.description) > 150:
                desc += "..."
            return desc
        else:
            return f"Learn about {entity.name}, a {entity.entity_type.lower()} covered in our comprehensive guides."
    
    def _determine_schema_type(self, entity_type: str) -> str:
        """Determine Schema.org type for entity."""
        schema_mapping = {
            'PERSON': 'Person',
            'ORG': 'Organization',
            'GPE': 'Place',
            'PRODUCT': 'Product',
            'EVENT': 'Event',
            'CONCEPT': 'Thing'
        }
        
        return schema_mapping.get(entity_type, 'Thing')
    
    def _generate_overview_content(self, entity: Entity) -> str:
        """Generate overview content for entity."""
        content_parts = []
        
        if entity.description:
            content_parts.append(entity.description)
        
        content_parts.append(f"{entity.name} is mentioned across {len(entity.pages_mentioned)} pages on our site.")
        
        if entity.aliases:
            aliases_text = ", ".join(entity.aliases[:3])
            content_parts.append(f"Also known as: {aliases_text}.")
        
        return " ".join(content_parts)
    
    def _generate_related_content(self, entity: Entity, related_entities: List[str]) -> str:
        """Generate related content section."""
        if not related_entities:
            return f"Explore other topics related to {entity.name} throughout our content."
        
        related_text = ", ".join(related_entities[:5])
        return f"{entity.name} is closely related to: {related_text}. Discover more connections in our comprehensive guides."
    
    def _generate_schema_data(self, entity: Entity) -> Dict:
        """Generate Schema.org structured data for entity."""
        schema_type = self._determine_schema_type(entity.entity_type)
        
        schema_data = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "name": entity.name,
            "description": entity.description or f"Information about {entity.name}"
        }
        
        if entity.same_as_urls:
            schema_data["sameAs"] = entity.same_as_urls
        
        if entity.aliases:
            schema_data["alternateName"] = entity.aliases
        
        return schema_data


class EntityLinkingManager(LoggerMixin):
    """Main manager for entity linking and knowledge graph operations."""
    
    def __init__(self, project_id: str):
        """Initialize entity linking manager."""
        self.project_id = project_id
        self.entity_extractor = EntityExtractor()
        self.entity_normalizer = EntityNormalizer()
        self.relationship_extractor = RelationshipExtractor()
        self.knowledge_graph = KnowledgeGraph()
        self.page_generator = EntityPageGenerator()
    
    def build_knowledge_graph(self, page_ids: Optional[List[str]] = None) -> KnowledgeGraph:
        """
        Build knowledge graph from project content.
        
        Args:
            page_ids: Optional list of specific page IDs to process
            
        Returns:
            Built knowledge graph
        """
        self.logger.info(f"Building knowledge graph for project {self.project_id}")
        
        with get_db_session() as session:
            # Get pages to process
            query = session.query(Page).filter(Page.project_id == self.project_id)
            if page_ids:
                query = query.filter(Page.id.in_(page_ids))
            
            pages = query.all()
            
            if not pages:
                self.logger.warning("No pages found for knowledge graph building")
                return self.knowledge_graph
            
            # Extract entities from all pages
            all_entity_mentions = []
            
            for page in pages:
                self.logger.debug(f"Processing page: {page.title}")
                
                # Combine title and content for entity extraction
                content = page.title
                if page.meta_description:
                    content += " " + page.meta_description
                # In production, you'd also include the actual page content
                
                mentions = self.entity_extractor.extract_entities(content, page.id)
                all_entity_mentions.extend(mentions)
            
            # Normalize entities
            entities = self.entity_normalizer.normalize_entities(all_entity_mentions)
            
            # Add entities to knowledge graph
            for entity in entities:
                self.knowledge_graph.add_entity(entity)
            
            # Extract relationships
            relationships = self.relationship_extractor.extract_relationships(
                entities, all_entity_mentions
            )
            
            # Add relationships to knowledge graph
            for relationship in relationships:
                self.knowledge_graph.add_relationship(relationship)
            
            self.logger.info(
                f"Knowledge graph built successfully",
                entities_count=len(entities),
                relationships_count=len(relationships),
                pages_processed=len(pages)
            )
            
            return self.knowledge_graph
    
    def suggest_internal_links(self, page_id: str, content: str, limit: int = 10) -> List[Dict]:
        """
        Suggest internal links for a page based on entity mentions.
        
        Args:
            page_id: ID of the page to suggest links for
            content: Page content to analyze
            limit: Maximum number of suggestions
            
        Returns:
            List of link suggestions with context
        """
        suggestions = []
        
        # Get entity recommendations
        entity_recommendations = self.knowledge_graph.get_entity_recommendations(content, limit * 2)
        
        with get_db_session() as session:
            for entity_name in entity_recommendations:
                # Check if entity has a dedicated page
                entity_slug = self.page_generator._generate_slug(entity_name)
                target_page = session.query(Page).filter(
                    Page.project_id == self.project_id,
                    Page.slug == entity_slug
                ).first()
                
                if target_page:
                    # Find mention positions in content
                    entity = self.knowledge_graph.entities.get(entity_name)
                    if entity:
                        # Look for entity name and aliases in content
                        mentions_found = []
                        for name_variant in [entity.name] + entity.aliases:
                            for match in re.finditer(re.escape(name_variant), content, re.IGNORECASE):
                                mentions_found.append({
                                    'position': match.start(),
                                    'text': match.group(),
                                    'entity_name': entity.name
                                })
                        
                        if mentions_found:
                            suggestions.append({
                                'target_page_id': target_page.id,
                                'target_url': target_page.url or f"/{target_page.slug}",
                                'anchor_text': mentions_found[0]['text'],
                                'entity_name': entity.name,
                                'confidence_score': entity.confidence_score,
                                'mentions_count': len(mentions_found),
                                'context_position': mentions_found[0]['position']
                            })
                
                if len(suggestions) >= limit:
                    break
        
        # Sort by confidence and mentions count
        suggestions.sort(key=lambda x: (x['confidence_score'], x['mentions_count']), reverse=True)
        
        return suggestions[:limit]
    
    def generate_entity_pages(self, min_mentions: int = 3) -> List[Dict]:
        """
        Generate content for entity pages.
        
        Args:
            min_mentions: Minimum mentions required to generate a page
            
        Returns:
            List of entity page content structures
        """
        entity_pages = []
        
        for entity_name, entity in self.knowledge_graph.entities.items():
            if entity.mentions_count >= min_mentions:
                page_content = self.page_generator.generate_entity_page_content(
                    entity, self.knowledge_graph
                )
                entity_pages.append(page_content)
        
        self.logger.info(f"Generated {len(entity_pages)} entity pages")
        
        return entity_pages
    
    def export_knowledge_graph(self, output_path: str, format: str = "json") -> None:
        """Export the knowledge graph to a file."""
        self.knowledge_graph.export_graph(output_path, format)


def create_entity_manager(project_id: str) -> EntityLinkingManager:
    """Create an entity linking manager for a specific project."""
    return EntityLinkingManager(project_id)
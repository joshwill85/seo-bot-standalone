"""Content brief generation system with competitive analysis and SEO optimization."""

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

from ..config import ContentQualityConfig, settings
from ..db import get_db_session
from ..logging import get_logger, LoggerMixin
from ..models import ContentBrief, Keyword, Cluster, Project, Author
from ..keywords.serp_gap import SERPGapAnalyzer, SERPAnalysis
from ..linking.entities import EntityLinkingManager


@dataclass
class ContentOutlineSection:
    """Represents a section in the content outline."""
    title: str
    heading_level: int  # H1, H2, H3, etc.
    description: str
    word_count_target: int
    required_points: List[str]
    information_gain_elements: List[str]  # Unique value elements
    entity_mentions: List[str]  # Entities that should be mentioned
    internal_link_targets: List[str]
    source_requirements: List[str]  # Required citation types


@dataclass
class TaskCompleterSpec:
    """Specification for interactive task completers."""
    completer_type: str  # "calculator", "checklist", "tool", "template"
    title: str
    description: str
    purpose: str  # Why this completer adds value
    requirements: List[str]  # Technical/content requirements
    placement_suggestion: str  # Where in content to place
    user_value: str  # How it helps users complete tasks


@dataclass
class CompetitiveAdvantage:
    """Represents a competitive advantage opportunity."""
    advantage_type: str  # "content_gap", "format_innovation", "depth_advantage", "entity_coverage"
    description: str
    implementation: str
    expected_impact: str
    evidence: Dict  # Supporting data from SERP analysis
    priority: float  # 0-1 priority score


@dataclass
class ContentBriefRequirements:
    """Complete content brief with all requirements."""
    brief_id: str
    title: str
    slug: str
    content_type: str
    target_audience: str
    user_intent: str
    
    # SEO requirements
    primary_keyword: str
    secondary_keywords: List[str]
    target_word_count: int
    readability_target: int
    
    # Content structure
    outline: List[ContentOutlineSection]
    
    # Competitive differentiation
    competitive_advantages: List[CompetitiveAdvantage]
    serp_analysis_summary: Dict
    
    # Information gain requirements
    required_info_gain_elements: List[str]
    task_completers: List[TaskCompleterSpec]
    
    # Trust signals
    citations_required: int
    expert_review_needed: bool
    author_expertise_required: List[str]
    
    # Internal linking
    internal_link_strategy: Dict
    entity_coverage_plan: List[str]
    
    # Technical requirements
    schema_markup_required: str
    featured_snippet_optimization: Dict
    
    # Quality gates
    completion_criteria: List[str]
    success_metrics: List[str]


class SERPAnalysisProcessor:
    """Processes SERP analysis for content brief generation."""
    
    def __init__(self):
        """Initialize SERP analysis processor."""
        self.logger = get_logger(self.__class__.__name__)
    
    def extract_content_requirements(self, serp_analysis: SERPAnalysis) -> Dict:
        """
        Extract content requirements from SERP analysis.
        
        Args:
            serp_analysis: SERP analysis results
            
        Returns:
            Dictionary with content requirements
        """
        requirements = {
            'target_word_count': int(serp_analysis.avg_word_count * 1.1),  # 10% above average
            'required_topics': [],
            'content_gaps': [],
            'competitive_advantages': [],
            'entity_requirements': [],
            'format_opportunities': []
        }
        
        # Extract required topics from common entities
        requirements['required_topics'] = [
            entity for entity, count in serp_analysis.common_entities[:10]
            if count >= len(serp_analysis.serp_results) * 0.3  # In 30%+ of results
        ]
        
        # Process content gaps
        for gap in serp_analysis.content_gaps:
            if gap.priority > 0.7:  # High priority gaps
                requirements['content_gaps'].append({
                    'type': gap.gap_type,
                    'description': gap.description,
                    'action': gap.suggested_action,
                    'priority': gap.priority
                })
        
        # Extract competitive advantages from differentiation opportunities
        for i, opportunity in enumerate(serp_analysis.differentiation_opportunities):
            requirements['competitive_advantages'].append({
                'type': 'differentiation',
                'description': opportunity,
                'priority': 0.8 - (i * 0.1)  # Decreasing priority
            })
        
        # Entity requirements
        requirements['entity_requirements'] = [
            entity for entity, count in serp_analysis.common_entities[:15]
        ]
        
        return requirements
    
    def identify_information_gain_opportunities(self, serp_analysis: SERPAnalysis) -> List[str]:
        """Identify opportunities for unique information gain."""
        opportunities = []
        
        # Analyze content clusters for gaps
        if serp_analysis.content_clusters:
            cluster_themes = set()
            for cluster in serp_analysis.content_clusters:
                cluster_themes.add(cluster.get('theme', 'unknown'))
            
            if len(cluster_themes) < 3:
                opportunities.append("Introduce unique perspective not covered by competitors")
        
        # Check for missing expert insights
        has_expert_content = any(
            'expert' in result.title.lower() or 'interview' in result.title.lower()
            for result in serp_analysis.serp_results
        )
        
        if not has_expert_content:
            opportunities.append("Include expert interviews or expert-validated insights")
        
        # Check for original research opportunities
        has_research = any(
            'study' in result.title.lower() or 'research' in result.title.lower()
            for result in serp_analysis.serp_results
        )
        
        if not has_research:
            opportunities.append("Conduct and include original research or data analysis")
        
        # Check for interactive content gaps
        has_interactive = any(
            'calculator' in result.title.lower() or 'tool' in result.title.lower()
            for result in serp_analysis.serp_results
        )
        
        if not has_interactive:
            opportunities.append("Create interactive tools or calculators")
        
        # Look for format gaps
        content_formats = set()
        for result in serp_analysis.serp_results:
            if 'video' in result.title.lower():
                content_formats.add('video')
            if 'guide' in result.title.lower():
                content_formats.add('guide')
            if 'comparison' in result.title.lower():
                content_formats.add('comparison')
        
        if 'comparison' not in content_formats:
            opportunities.append("Add comprehensive comparison tables or matrices")
        
        return opportunities[:5]  # Top 5 opportunities
    
    def extract_outline_structure(self, serp_analysis: SERPAnalysis) -> List[Dict]:
        """Extract outline structure from top-performing competitors."""
        outline_structure = []
        
        # Analyze headings from top 3 results
        top_results = serp_analysis.serp_results[:3]
        heading_patterns = []
        
        for result in top_results:
            if result.headings:
                heading_patterns.append(result.headings)
        
        if not heading_patterns:
            return self._generate_default_outline(serp_analysis.query)
        
        # Find common heading patterns
        common_headings = self._find_common_headings(heading_patterns)
        
        # Generate outline sections
        for i, heading in enumerate(common_headings):
            section = {
                'title': heading,
                'level': 2,  # H2 by default
                'description': f"Cover {heading.lower()} comprehensively",
                'word_count_target': max(200, int(serp_analysis.avg_word_count / len(common_headings))),
                'source_requirements': ['primary_source'] if i < 3 else ['authoritative_source']
            }
            outline_structure.append(section)
        
        return outline_structure
    
    def _find_common_headings(self, heading_patterns: List[List[str]]) -> List[str]:
        """Find headings that appear across multiple competitors."""
        heading_counts = {}
        
        for headings in heading_patterns:
            for heading in headings:
                # Normalize heading for comparison
                normalized = self._normalize_heading(heading)
                heading_counts[normalized] = heading_counts.get(normalized, 0) + 1
        
        # Filter headings that appear in multiple sources
        min_appearances = max(1, len(heading_patterns) // 2)
        common_headings = [
            heading for heading, count in heading_counts.items()
            if count >= min_appearances
        ]
        
        # Sort by frequency
        common_headings.sort(key=lambda h: heading_counts[h], reverse=True)
        
        return common_headings[:8]  # Top 8 common headings
    
    def _normalize_heading(self, heading: str) -> str:
        """Normalize heading for comparison."""
        # Remove common words and normalize
        normalized = heading.lower()
        normalized = re.sub(r'\b(what|how|why|when|where|the|a|an|is|are|of|to|for|in|on)\b', '', normalized)
        normalized = re.sub(r'[^a-z\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _generate_default_outline(self, query: str) -> List[Dict]:
        """Generate default outline structure when SERP data is insufficient."""
        return [
            {
                'title': f"What is {query}?",
                'level': 2,
                'description': f"Comprehensive introduction to {query}",
                'word_count_target': 300,
                'source_requirements': ['primary_source']
            },
            {
                'title': f"How {query} Works",
                'level': 2,
                'description': f"Detailed explanation of {query} mechanics",
                'word_count_target': 400,
                'source_requirements': ['authoritative_source']
            },
            {
                'title': f"Benefits and Advantages",
                'level': 2,
                'description': f"Key benefits and advantages of {query}",
                'word_count_target': 300,
                'source_requirements': ['expert_source']
            },
            {
                'title': f"Best Practices",
                'level': 2,
                'description': f"Industry best practices for {query}",
                'word_count_target': 350,
                'source_requirements': ['authoritative_source']
            },
            {
                'title': "Conclusion",
                'level': 2,
                'description': f"Summary and key takeaways about {query}",
                'word_count_target': 200,
                'source_requirements': []
            }
        ]


class TaskCompleterGenerator:
    """Generates specifications for interactive task completers."""
    
    def __init__(self):
        """Initialize task completer generator."""
        self.logger = get_logger(self.__class__.__name__)
    
    def generate_task_completers(
        self, 
        content_type: str, 
        primary_keyword: str, 
        user_intent: str,
        serp_analysis: SERPAnalysis
    ) -> List[TaskCompleterSpec]:
        """
        Generate task completer specifications based on content analysis.
        
        Args:
            content_type: Type of content being created
            primary_keyword: Primary target keyword
            user_intent: User intent for the content
            serp_analysis: SERP analysis results
            
        Returns:
            List of task completer specifications
        """
        task_completers = []
        
        # Analyze user intent and keyword for completer opportunities
        keyword_lower = primary_keyword.lower()
        
        # Calculator opportunities
        if any(word in keyword_lower for word in ['cost', 'price', 'calculate', 'budget', 'roi']):
            task_completers.append(TaskCompleterSpec(
                completer_type="calculator",
                title=f"{primary_keyword.title()} Calculator",
                description=f"Interactive calculator to help users estimate {primary_keyword}",
                purpose="Provides immediate value and practical utility to users",
                requirements=[
                    "Input fields for relevant variables",
                    "Real-time calculation display",
                    "Option to save/share results",
                    "Clear explanation of calculation methodology"
                ],
                placement_suggestion="After introduction section, before detailed explanations",
                user_value="Enables users to get personalized estimates quickly"
            ))
        
        # Comparison tools
        if any(word in keyword_lower for word in ['vs', 'versus', 'compare', 'best', 'alternatives']):
            task_completers.append(TaskCompleterSpec(
                completer_type="tool",
                title=f"{primary_keyword.title()} Comparison Tool",
                description="Interactive comparison matrix for evaluating options",
                purpose="Helps users make informed decisions by comparing alternatives",
                requirements=[
                    "Customizable comparison criteria",
                    "Visual comparison matrix",
                    "Filtering and sorting capabilities",
                    "Export comparison results"
                ],
                placement_suggestion="In dedicated comparison section",
                user_value="Simplifies complex decision-making process"
            ))
        
        # Checklists for how-to content
        if any(word in keyword_lower for word in ['how to', 'guide', 'steps', 'process']):
            task_completers.append(TaskCompleterSpec(
                completer_type="checklist",
                title=f"{primary_keyword.title()} Checklist",
                description="Step-by-step interactive checklist for implementation",
                purpose="Ensures users don't miss critical steps in the process",
                requirements=[
                    "Checkable items with progress tracking",
                    "Optional sub-tasks for detailed steps",
                    "Progress saving capability",
                    "Printable format option"
                ],
                placement_suggestion="After step-by-step instructions",
                user_value="Provides actionable implementation guidance"
            ))
        
        # Templates for planning content
        if any(word in keyword_lower for word in ['plan', 'template', 'strategy', 'framework']):
            task_completers.append(TaskCompleterSpec(
                completer_type="template",
                title=f"{primary_keyword.title()} Template",
                description="Customizable template for implementation",
                purpose="Gives users a head start with proven frameworks",
                requirements=[
                    "Downloadable/copyable template",
                    "Customization instructions",
                    "Example implementations",
                    "Integration with popular tools"
                ],
                placement_suggestion="Near the end, before conclusion",
                user_value="Saves time and ensures proper implementation"
            ))
        
        # Assessment tools
        if 'assessment' in user_intent.lower() or 'evaluate' in keyword_lower:
            task_completers.append(TaskCompleterSpec(
                completer_type="tool",
                title=f"{primary_keyword.title()} Assessment",
                description="Self-assessment tool to evaluate current state",
                purpose="Helps users understand their current situation and needs",
                requirements=[
                    "Scoring methodology",
                    "Personalized recommendations",
                    "Benchmark comparisons",
                    "Action plan generation"
                ],
                placement_suggestion="Early in content, after problem identification",
                user_value="Provides personalized insights and recommendations"
            ))
        
        return task_completers[:3]  # Limit to top 3 most relevant


class InternalLinkingStrategy:
    """Develops internal linking strategy for content briefs."""
    
    def __init__(self, entity_manager: Optional[EntityLinkingManager] = None):
        """Initialize internal linking strategy."""
        self.logger = get_logger(self.__class__.__name__)
        self.entity_manager = entity_manager
    
    def develop_linking_strategy(
        self,
        primary_keyword: str,
        secondary_keywords: List[str],
        content_outline: List[Dict],
        project_id: str
    ) -> Dict:
        """
        Develop comprehensive internal linking strategy.
        
        Args:
            primary_keyword: Primary target keyword
            secondary_keywords: Secondary keywords
            content_outline: Content outline structure
            project_id: Project ID for finding existing pages
            
        Returns:
            Internal linking strategy
        """
        strategy = {
            'hub_page_opportunities': [],
            'spoke_page_targets': [],
            'entity_linking_plan': [],
            'contextual_link_suggestions': [],
            'anchor_text_strategy': {},
            'link_distribution_plan': {}
        }
        
        with get_db_session() as session:
            # Find existing related pages
            all_keywords = [primary_keyword] + secondary_keywords
            related_pages = self._find_related_pages(session, project_id, all_keywords)
            
            # Develop hub-spoke strategy
            strategy['hub_page_opportunities'] = self._identify_hub_opportunities(
                primary_keyword, related_pages
            )
            
            strategy['spoke_page_targets'] = self._identify_spoke_targets(
                secondary_keywords, related_pages
            )
            
            # Entity linking if entity manager is available
            if self.entity_manager:
                strategy['entity_linking_plan'] = self._develop_entity_linking_plan(
                    all_keywords, content_outline
                )
            
            # Contextual linking suggestions
            strategy['contextual_link_suggestions'] = self._generate_contextual_suggestions(
                content_outline, related_pages
            )
            
            # Anchor text strategy
            strategy['anchor_text_strategy'] = self._develop_anchor_text_strategy(
                primary_keyword, secondary_keywords
            )
        
        return strategy
    
    def _find_related_pages(self, session: Session, project_id: str, keywords: List[str]) -> List[Dict]:
        """Find existing pages related to the keywords."""
        related_pages = []
        
        # Search for pages with related target keywords
        for keyword in keywords:
            pages = session.query(Page).filter(
                Page.project_id == project_id,
                Page.target_keywords.contains([keyword])  # JSON contains
            ).all()
            
            for page in pages:
                related_pages.append({
                    'id': page.id,
                    'title': page.title,
                    'slug': page.slug,
                    'url': page.url,
                    'target_keywords': page.target_keywords or [],
                    'content_type': page.content_type
                })
        
        return related_pages
    
    def _identify_hub_opportunities(self, primary_keyword: str, related_pages: List[Dict]) -> List[Dict]:
        """Identify opportunities for hub page creation."""
        opportunities = []
        
        # Look for broad topic opportunities
        keyword_parts = primary_keyword.split()
        if len(keyword_parts) > 1:
            # Check if we have related content that could be organized under a hub
            related_count = len([p for p in related_pages if any(part in ' '.join(p['target_keywords']) for part in keyword_parts)])
            
            if related_count >= 3:
                opportunities.append({
                    'hub_topic': keyword_parts[0] if keyword_parts else primary_keyword,
                    'related_pages_count': related_count,
                    'suggested_hub_title': f"Complete Guide to {keyword_parts[0].title()}",
                    'linking_strategy': 'Create comprehensive hub page linking to all related content'
                })
        
        return opportunities
    
    def _identify_spoke_targets(self, secondary_keywords: List[str], related_pages: List[Dict]) -> List[Dict]:
        """Identify spoke page linking targets."""
        targets = []
        
        for keyword in secondary_keywords:
            # Find pages that could be targeted for this keyword
            relevant_pages = [
                p for p in related_pages
                if keyword.lower() in ' '.join(p['target_keywords']).lower()
                or keyword.lower() in p['title'].lower()
            ]
            
            if relevant_pages:
                targets.append({
                    'keyword': keyword,
                    'target_pages': relevant_pages[:3],  # Top 3 most relevant
                    'linking_priority': 'high' if len(relevant_pages) > 1 else 'medium'
                })
        
        return targets
    
    def _develop_entity_linking_plan(self, keywords: List[str], content_outline: List[Dict]) -> List[Dict]:
        """Develop entity-based linking plan."""
        plan = []
        
        # This would integrate with the entity manager to find linking opportunities
        # For now, return a placeholder structure
        for section in content_outline:
            section_title = section.get('title', '')
            
            plan.append({
                'section': section_title,
                'entity_opportunities': [],  # Would be populated by entity manager
                'linking_density_target': '2-3 entity links per section',
                'context_requirements': 'Links should flow naturally within content'
            })
        
        return plan
    
    def _generate_contextual_suggestions(self, content_outline: List[Dict], related_pages: List[Dict]) -> List[Dict]:
        """Generate contextual linking suggestions for each content section."""
        suggestions = []
        
        for section in content_outline:
            section_title = section.get('title', '').lower()
            section_suggestions = []
            
            # Find related pages that could be linked from this section
            for page in related_pages:
                page_keywords = [kw.lower() for kw in page.get('target_keywords', [])]
                
                # Simple relevance matching
                if any(keyword in section_title for keyword in page_keywords):
                    section_suggestions.append({
                        'target_page': page,
                        'suggested_context': f"Link when discussing {page['title'].lower()}",
                        'anchor_text_suggestion': page['title'],
                        'link_type': 'contextual'
                    })
            
            if section_suggestions:
                suggestions.append({
                    'section': section.get('title'),
                    'link_suggestions': section_suggestions[:2]  # Max 2 per section
                })
        
        return suggestions
    
    def _develop_anchor_text_strategy(self, primary_keyword: str, secondary_keywords: List[str]) -> Dict:
        """Develop anchor text strategy for natural linking."""
        strategy = {
            'primary_keyword_variants': self._generate_anchor_variants(primary_keyword),
            'secondary_keyword_variants': {},
            'guidelines': [
                "Use natural, contextual anchor text",
                "Vary anchor text to avoid over-optimization",
                "Include related terms and synonyms",
                "Ensure anchor text flows naturally in sentences"
            ]
        }
        
        for keyword in secondary_keywords:
            strategy['secondary_keyword_variants'][keyword] = self._generate_anchor_variants(keyword)
        
        return strategy
    
    def _generate_anchor_variants(self, keyword: str) -> List[str]:
        """Generate natural anchor text variants for a keyword."""
        variants = [keyword]
        
        # Add partial matches
        if len(keyword.split()) > 1:
            variants.append(keyword.split()[-1])  # Last word
            variants.append(' '.join(keyword.split()[:-1]))  # All but last word
        
        # Add common variations
        variants.extend([
            f"learn about {keyword}",
            f"{keyword} guide",
            f"how to {keyword}",
            f"{keyword} explained"
        ])
        
        return variants[:5]  # Top 5 variants


class ContentBriefGenerator(LoggerMixin):
    """Main content brief generation system."""
    
    def __init__(self, project_id: str, quality_config: Optional[ContentQualityConfig] = None):
        """Initialize content brief generator."""
        self.project_id = project_id
        self.quality_config = quality_config or ContentQualityConfig()
        self.serp_processor = SERPAnalysisProcessor()
        self.task_generator = TaskCompleterGenerator()
        self.linking_strategy = InternalLinkingStrategy()
        
        # Initialize SERP gap analyzer
        self.serp_analyzer = SERPGapAnalyzer()
    
    def generate_content_brief(
        self,
        cluster: Cluster,
        primary_keyword: str,
        secondary_keywords: List[str],
        target_audience: str,
        user_intent: str,
        author_requirements: Optional[List[str]] = None
    ) -> ContentBriefRequirements:
        """
        Generate comprehensive content brief.
        
        Args:
            cluster: Keyword cluster
            primary_keyword: Primary target keyword
            secondary_keywords: List of secondary keywords
            target_audience: Target audience description
            user_intent: User intent for the content
            author_requirements: Required author expertise areas
            
        Returns:
            Complete content brief requirements
        """
        self.logger.info(f"Generating content brief for keyword: {primary_keyword}")
        
        # Perform SERP analysis
        serp_analysis = self.serp_analyzer.analyze_serp_gaps(
            primary_keyword,
            num_results=10,
            analyze_content=True
        )
        
        # Extract content requirements from SERP analysis
        content_requirements = self.serp_processor.extract_content_requirements(serp_analysis)
        
        # Generate outline structure
        outline_data = self.serp_processor.extract_outline_structure(serp_analysis)
        outline = self._create_detailed_outline(outline_data, content_requirements, serp_analysis)
        
        # Identify competitive advantages
        competitive_advantages = self._identify_competitive_advantages(serp_analysis, content_requirements)
        
        # Generate task completers
        task_completers = self.task_generator.generate_task_completers(
            cluster.cluster_type, primary_keyword, user_intent, serp_analysis
        )
        
        # Develop internal linking strategy
        linking_strategy = self.linking_strategy.develop_linking_strategy(
            primary_keyword, secondary_keywords, outline_data, self.project_id
        )
        
        # Generate information gain requirements
        info_gain_elements = self.serp_processor.identify_information_gain_opportunities(serp_analysis)
        
        # Determine trust signal requirements
        citations_required, expert_review_needed = self._determine_trust_requirements(
            primary_keyword, user_intent
        )
        
        # Calculate target word count
        target_word_count = max(
            self.quality_config.word_count_bounds[0],
            content_requirements.get('target_word_count', 1000)
        )
        
        # Generate completion criteria
        completion_criteria = self._generate_completion_criteria(
            target_word_count, len(info_gain_elements), citations_required
        )
        
        brief = ContentBriefRequirements(
            brief_id=cluster.id,
            title=self._generate_content_title(primary_keyword, competitive_advantages),
            slug=cluster.slug,
            content_type=cluster.cluster_type,
            target_audience=target_audience,
            user_intent=user_intent,
            primary_keyword=primary_keyword,
            secondary_keywords=secondary_keywords,
            target_word_count=target_word_count,
            readability_target=self.quality_config.min_readability_score,
            outline=outline,
            competitive_advantages=competitive_advantages,
            serp_analysis_summary=self._summarize_serp_analysis(serp_analysis),
            required_info_gain_elements=info_gain_elements,
            task_completers=task_completers,
            citations_required=citations_required,
            expert_review_needed=expert_review_needed,
            author_expertise_required=author_requirements or [],
            internal_link_strategy=linking_strategy,
            entity_coverage_plan=content_requirements.get('entity_requirements', []),
            schema_markup_required=self._determine_schema_type(cluster.cluster_type),
            featured_snippet_optimization=self._generate_snippet_optimization(primary_keyword),
            completion_criteria=completion_criteria,
            success_metrics=self._generate_success_metrics(primary_keyword, target_word_count)
        )
        
        self.logger.info(
            f"Content brief generated successfully",
            primary_keyword=primary_keyword,
            target_word_count=target_word_count,
            sections_count=len(outline),
            competitive_advantages_count=len(competitive_advantages)
        )
        
        return brief
    
    def _create_detailed_outline(
        self, 
        outline_data: List[Dict], 
        content_requirements: Dict,
        serp_analysis: SERPAnalysis
    ) -> List[ContentOutlineSection]:
        """Create detailed content outline with all requirements."""
        sections = []
        
        for section_data in outline_data:
            # Determine entities to mention in this section
            section_entities = self._assign_entities_to_section(
                section_data['title'], content_requirements.get('entity_requirements', [])
            )
            
            # Identify information gain elements for this section
            section_info_gain = self._assign_info_gain_to_section(
                section_data['title'], content_requirements.get('content_gaps', [])
            )
            
            # Generate internal link targets
            section_links = self._generate_section_link_targets(section_data['title'])
            
            section = ContentOutlineSection(
                title=section_data['title'],
                heading_level=section_data.get('level', 2),
                description=section_data['description'],
                word_count_target=section_data['word_count_target'],
                required_points=self._generate_required_points(section_data['title']),
                information_gain_elements=section_info_gain,
                entity_mentions=section_entities,
                internal_link_targets=section_links,
                source_requirements=section_data.get('source_requirements', [])
            )
            sections.append(section)
        
        return sections
    
    def _identify_competitive_advantages(
        self, 
        serp_analysis: SERPAnalysis, 
        content_requirements: Dict
    ) -> List[CompetitiveAdvantage]:
        """Identify competitive advantages from analysis."""
        advantages = []
        
        # Content gap advantages
        for gap in serp_analysis.content_gaps:
            if gap.priority > 0.7:
                advantages.append(CompetitiveAdvantage(
                    advantage_type=gap.gap_type,
                    description=f"Address {gap.description}",
                    implementation=gap.suggested_action,
                    expected_impact="Provide information not available on competing pages",
                    evidence=gap.evidence,
                    priority=gap.priority
                ))
        
        # Format innovation advantages
        for opportunity in serp_analysis.differentiation_opportunities:
            if 'format' in opportunity.lower() or 'interactive' in opportunity.lower():
                advantages.append(CompetitiveAdvantage(
                    advantage_type="format_innovation",
                    description=opportunity,
                    implementation="Create interactive content elements",
                    expected_impact="Provide better user experience than static competitors",
                    evidence={"opportunity": opportunity},
                    priority=0.8
                ))
        
        # Depth advantages
        if serp_analysis.avg_word_count < 2000:
            advantages.append(CompetitiveAdvantage(
                advantage_type="depth_advantage",
                description="Create more comprehensive content than competitors",
                implementation=f"Target {int(serp_analysis.avg_word_count * 1.3)} words vs competitor average of {int(serp_analysis.avg_word_count)}",
                expected_impact="Become the most authoritative resource on the topic",
                evidence={"competitor_avg_words": serp_analysis.avg_word_count},
                priority=0.7
            ))
        
        return advantages
    
    def _determine_trust_requirements(self, primary_keyword: str, user_intent: str) -> Tuple[int, bool]:
        """Determine trust signal requirements based on content."""
        keyword_lower = primary_keyword.lower()
        intent_lower = user_intent.lower()
        
        # YMYL topics require more citations and expert review
        ymyl_keywords = ['health', 'medical', 'financial', 'legal', 'safety', 'investment', 'insurance']
        is_ymyl = any(keyword in keyword_lower for keyword in ymyl_keywords)
        
        if is_ymyl:
            return 5, True  # 5 citations, expert review required
        elif 'commercial' in intent_lower:
            return 3, False  # 3 citations, no expert review required
        else:
            return self.quality_config.min_citations_per_page, False
    
    def _generate_content_title(self, primary_keyword: str, competitive_advantages: List[CompetitiveAdvantage]) -> str:
        """Generate compelling content title."""
        keyword_parts = primary_keyword.split()
        
        # Check for specific advantage types to customize title
        has_comprehensive = any(adv.advantage_type == "depth_advantage" for adv in competitive_advantages)
        has_interactive = any(adv.advantage_type == "format_innovation" for adv in competitive_advantages)
        
        if has_comprehensive:
            return f"The Complete Guide to {primary_keyword.title()}"
        elif has_interactive:
            return f"{primary_keyword.title()}: Interactive Guide and Tools"
        elif len(keyword_parts) > 2:
            return f"Ultimate {primary_keyword.title()} Guide"
        else:
            return f"{primary_keyword.title()}: Everything You Need to Know"
    
    def _summarize_serp_analysis(self, serp_analysis: SERPAnalysis) -> Dict:
        """Create summary of SERP analysis for brief."""
        return {
            'query': serp_analysis.query,
            'results_analyzed': serp_analysis.total_results,
            'average_word_count': serp_analysis.avg_word_count,
            'top_domains': serp_analysis.top_domains[:5],
            'common_topics': [topic for topic, score in serp_analysis.common_topics[:5]],
            'gaps_identified': len(serp_analysis.content_gaps),
            'opportunities_found': len(serp_analysis.differentiation_opportunities)
        }
    
    def _determine_schema_type(self, content_type: str) -> str:
        """Determine appropriate Schema.org type."""
        schema_mapping = {
            'hub': 'Article',
            'spoke': 'Article',
            'howto': 'HowTo',
            'comparison': 'Article',
            'product': 'Product',
            'review': 'Review'
        }
        
        return schema_mapping.get(content_type, 'Article')
    
    def _generate_snippet_optimization(self, primary_keyword: str) -> Dict:
        """Generate featured snippet optimization strategy."""
        return {
            'target_snippet_type': 'paragraph',  # or 'list', 'table'
            'optimization_strategy': f"Create concise, definitive answer to '{primary_keyword}' in first 50-60 words",
            'question_format': f"What is {primary_keyword}?",
            'answer_structure': "Definition + key benefit + primary use case",
            'placement': "Immediately after H1, before table of contents"
        }
    
    def _generate_completion_criteria(self, word_count: int, info_gain_count: int, citations: int) -> List[str]:
        """Generate completion criteria for the content."""
        criteria = [
            f"Content must be {word_count}+ words",
            f"Include at least {info_gain_count} unique information-gain elements",
            f"Include {citations} high-quality citations",
            f"Pass readability score of {self.quality_config.min_readability_score}+",
            "All required sections completed with target word counts met",
            "Internal linking strategy implemented",
            "Schema markup added and validated",
            "Meta title and description optimized"
        ]
        
        return criteria
    
    def _generate_success_metrics(self, primary_keyword: str, word_count: int) -> List[str]:
        """Generate success metrics for content performance."""
        return [
            f"Rank in top 10 for '{primary_keyword}' within 3 months",
            "Achieve featured snippet for primary keyword",
            "Generate 25% more engagement than average page",
            f"Maintain bounce rate under 60%",
            "Receive backlinks from 5+ authoritative domains",
            "Generate social shares and engagement"
        ]
    
    def _assign_entities_to_section(self, section_title: str, entities: List[str]) -> List[str]:
        """Assign relevant entities to content sections."""
        # Simple relevance matching - could be enhanced with NLP
        section_lower = section_title.lower()
        relevant_entities = []
        
        for entity in entities:
            if any(word in section_lower for word in entity.lower().split()):
                relevant_entities.append(entity)
        
        return relevant_entities[:3]  # Max 3 entities per section
    
    def _assign_info_gain_to_section(self, section_title: str, gaps: List[Dict]) -> List[str]:
        """Assign information gain elements to sections."""
        section_lower = section_title.lower()
        section_elements = []
        
        for gap in gaps:
            if gap['type'] == 'missing_topic' and any(word in section_lower for word in gap['description'].lower().split()):
                section_elements.append(gap['action'])
        
        return section_elements
    
    def _generate_section_link_targets(self, section_title: str) -> List[str]:
        """Generate internal link targets for a section."""
        # This would integrate with existing page analysis
        # For now, return placeholder based on common patterns
        section_lower = section_title.lower()
        
        targets = []
        if 'benefits' in section_lower:
            targets.append('/benefits-guide')
        if 'how to' in section_lower or 'steps' in section_lower:
            targets.append('/implementation-guide')
        if 'best practices' in section_lower:
            targets.append('/best-practices')
        
        return targets
    
    def _generate_required_points(self, section_title: str) -> List[str]:
        """Generate required points for a content section."""
        section_lower = section_title.lower()
        points = []
        
        if 'introduction' in section_lower or 'what is' in section_lower:
            points = [
                "Clear definition of the topic",
                "Why this topic matters to users",
                "Brief overview of what will be covered"
            ]
        elif 'benefits' in section_lower:
            points = [
                "At least 3 specific benefits",
                "Real-world examples or case studies",
                "Quantitative data where possible"
            ]
        elif 'how to' in section_lower or 'steps' in section_lower:
            points = [
                "Step-by-step instructions",
                "Prerequisites or requirements",
                "Common pitfalls to avoid"
            ]
        elif 'conclusion' in section_lower:
            points = [
                "Summary of key points",
                "Clear next steps for readers",
                "Call to action"
            ]
        else:
            points = [
                "Comprehensive coverage of the topic",
                "Actionable insights or advice",
                "Supporting evidence or examples"
            ]
        
        return points
    
    def export_brief(self, brief: ContentBriefRequirements, output_path: str) -> None:
        """Export content brief to JSON file."""
        try:
            brief_dict = asdict(brief)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(brief_dict, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Content brief exported to {output_path}")
        
        except Exception as e:
            self.logger.error(f"Failed to export content brief: {e}")


def create_brief_generator(project_id: str) -> ContentBriefGenerator:
    """Create a content brief generator for a specific project."""
    with get_db_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get content quality config from project config
        quality_config = ContentQualityConfig()
        if project.config and 'content_quality' in project.config:
            quality_config = ContentQualityConfig(**project.config['content_quality'])
        
        return ContentBriefGenerator(project_id, quality_config)
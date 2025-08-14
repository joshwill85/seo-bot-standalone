"""Keyword discovery and expansion functionality."""

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from ..config import KeywordsConfig, settings
from ..db import get_db_session
from ..logging import get_logger, LoggerMixin
from ..models import GSCData, Keyword, Project
from .score import KeywordScorer, SearchIntent


@dataclass
class KeywordSeed:
    """Seed keyword with expansion data."""
    term: str
    category: Optional[str] = None
    priority: float = 1.0
    modifiers: Optional[List[str]] = None


@dataclass
class DiscoveredKeyword:
    """Discovered keyword with metadata."""
    query: str
    source: str
    search_volume: Optional[int] = None
    cpc: Optional[float] = None
    competition: Optional[float] = None
    serp_features: Optional[List[str]] = None
    parent_seed: Optional[str] = None
    expansion_method: Optional[str] = None


class GSCIntegrator:
    """Google Search Console data integration."""
    
    def __init__(self, credentials_file: Optional[str] = None):
        """Initialize GSC integrator."""
        self.logger = get_logger(self.__class__.__name__)
        self.credentials_file = credentials_file or settings.google_search_console_credentials_file
        self._service = None
    
    def get_service(self):
        """Get authenticated GSC service."""
        if not self.credentials_file:
            self.logger.warning("No GSC credentials file provided")
            return None
        
        if self._service is None:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
                )
                self._service = build('searchconsole', 'v1', credentials=credentials)
                self.logger.info("GSC service authenticated successfully")
            except Exception as e:
                self.logger.error(f"Failed to authenticate GSC service: {e}")
                return None
        
        return self._service
    
    def fetch_queries(
        self,
        site_url: str,
        days: int = 30,
        min_impressions: int = 10,
        max_queries: int = 1000
    ) -> List[Dict]:
        """
        Fetch queries from Google Search Console.
        
        Args:
            site_url: Site URL in GSC
            days: Days back to fetch data
            min_impressions: Minimum impressions threshold
            max_queries: Maximum queries to return
            
        Returns:
            List of query data dictionaries
        """
        service = self.get_service()
        if not service:
            return []
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': ['query'],
            'rowLimit': max_queries,
            'startRow': 0
        }
        
        try:
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()
            
            queries = []
            for row in response.get('rows', []):
                if row['impressions'] >= min_impressions:
                    queries.append({
                        'query': row['keys'][0],
                        'impressions': row['impressions'],
                        'clicks': row['clicks'],
                        'ctr': row['ctr'],
                        'position': row['position']
                    })
            
            self.logger.info(
                f"Fetched {len(queries)} queries from GSC",
                site_url=site_url,
                date_range=f"{start_date} to {end_date}"
            )
            
            return queries
        
        except Exception as e:
            self.logger.error(f"Failed to fetch GSC queries: {e}")
            return []
    
    def get_existing_gsc_keywords(self, session: Session, project_id: str) -> List[str]:
        """Get existing keywords from GSC data in database."""
        try:
            gsc_data = session.query(GSCData).filter(
                GSCData.project_id == project_id,
                GSCData.query.isnot(None)
            ).distinct(GSCData.query).limit(5000).all()
            
            keywords = [data.query for data in gsc_data if data.query]
            self.logger.info(f"Found {len(keywords)} existing GSC keywords in database")
            return keywords
        
        except Exception as e:
            self.logger.error(f"Failed to get GSC keywords from database: {e}")
            return []


class SERPAPIClient:
    """SERP API client for keyword data."""
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "serpapi"):
        """Initialize SERP API client."""
        self.api_key = api_key or settings.serp_api_key
        self.provider = provider
        self.logger = get_logger(self.__class__.__name__)
        
        if provider == "serpapi":
            self.base_url = "https://serpapi.com/search"
        elif provider == "dataforseo":
            self.base_url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
        else:
            raise ValueError(f"Unsupported SERP provider: {provider}")
    
    def search_suggestions(self, query: str, location: str = "United States") -> List[str]:
        """Get search suggestions for a query."""
        if not self.api_key:
            self.logger.warning("No SERP API key provided")
            return []
        
        try:
            if self.provider == "serpapi":
                params = {
                    'engine': 'google_autocomplete',
                    'q': query,
                    'gl': 'us',
                    'api_key': self.api_key
                }
                
                response = httpx.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                suggestions = []
                
                for suggestion in data.get('suggestions', []):
                    if 'value' in suggestion:
                        suggestions.append(suggestion['value'])
                
                self.logger.debug(f"Got {len(suggestions)} suggestions for '{query}'")
                return suggestions[:20]  # Limit to top 20
            
            else:
                # DataForSEO or other providers would be implemented here
                self.logger.warning(f"Search suggestions not implemented for {self.provider}")
                return []
        
        except Exception as e:
            self.logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    def get_keyword_data(self, keywords: List[str], location: str = "US") -> List[Dict]:
        """Get keyword data including volume and competition."""
        if not self.api_key or not keywords:
            return []
        
        # This would implement actual SERP API calls for keyword data
        # For now, return placeholder data
        self.logger.warning("Keyword data fetching not fully implemented - returning mock data")
        
        results = []
        for keyword in keywords:
            results.append({
                'keyword': keyword,
                'search_volume': None,  # Would come from API
                'cpc': None,           # Would come from API
                'competition': None,   # Would come from API
                'serp_features': []    # Would come from API
            })
        
        return results


class KeywordExpander:
    """Expands seed keywords using various techniques."""
    
    INTENT_MODIFIERS = {
        'informational': [
            'what is', 'how to', 'why', 'when', 'where', 'who',
            'guide', 'tutorial', 'tips', 'best practices', 'examples',
            'vs', 'versus', 'difference between', 'compare'
        ],
        'transactional': [
            'buy', 'purchase', 'order', 'shop', 'sale', 'deal',
            'cheap', 'discount', 'coupon', 'price', 'cost',
            'near me', 'local', 'hire', 'book', 'schedule'
        ],
        'commercial': [
            'best', 'top', 'review', 'rating', 'comparison',
            'service', 'company', 'provider', 'professional',
            'quote', 'estimate', 'consultation'
        ]
    }
    
    TEMPORAL_MODIFIERS = ['2024', '2025', 'latest', 'new', 'updated', 'current']
    
    QUALIFIER_MODIFIERS = ['best', 'top', 'cheap', 'free', 'premium', 'professional']
    
    def __init__(self):
        """Initialize keyword expander."""
        self.logger = get_logger(self.__class__.__name__)
    
    def expand_seed_keywords(
        self,
        seeds: List[KeywordSeed],
        max_per_seed: int = 50
    ) -> List[DiscoveredKeyword]:
        """
        Expand seed keywords into a larger set of related keywords.
        
        Args:
            seeds: List of seed keywords to expand
            max_per_seed: Maximum keywords per seed
            
        Returns:
            List of discovered keywords
        """
        discovered = []
        
        for seed in seeds:
            seed_keywords = self._expand_single_seed(seed, max_per_seed)
            discovered.extend(seed_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in discovered:
            if kw.query not in seen:
                seen.add(kw.query)
                unique_keywords.append(kw)
        
        self.logger.info(
            f"Expanded {len(seeds)} seeds into {len(unique_keywords)} unique keywords"
        )
        
        return unique_keywords
    
    def _expand_single_seed(self, seed: KeywordSeed, max_keywords: int) -> List[DiscoveredKeyword]:
        """Expand a single seed keyword."""
        keywords = []
        base_term = seed.term.lower().strip()
        
        # Use custom modifiers if provided
        if seed.modifiers:
            modifiers = seed.modifiers
        else:
            # Use all intent modifiers
            modifiers = []
            for intent_mods in self.INTENT_MODIFIERS.values():
                modifiers.extend(intent_mods)
            modifiers.extend(self.TEMPORAL_MODIFIERS)
            modifiers.extend(self.QUALIFIER_MODIFIERS)
        
        # Generate variations
        variations = set()
        
        # Add base term
        variations.add(base_term)
        
        # Prefix modifiers
        for modifier in modifiers:
            variations.add(f"{modifier} {base_term}")
            
            # Also try modifier variations
            if len(modifier.split()) == 1:  # Single word modifier
                variations.add(f"{base_term} {modifier}")
        
        # Question variations
        question_starters = ['how to', 'what is', 'why', 'when to', 'where to']
        for starter in question_starters:
            if base_term.startswith(tuple(question_starters)):
                continue  # Skip if already a question
            variations.add(f"{starter} {base_term}")
        
        # Location variations
        location_modifiers = ['near me', 'local', 'in my area', 'nearby']
        for loc_mod in location_modifiers:
            variations.add(f"{base_term} {loc_mod}")
        
        # Convert to DiscoveredKeyword objects
        count = 0
        for variation in variations:
            if count >= max_keywords:
                break
            
            # Skip very short or very long keywords
            word_count = len(variation.split())
            if word_count < 2 or word_count > 8:
                continue
            
            keywords.append(DiscoveredKeyword(
                query=variation,
                source="seed_expansion",
                parent_seed=seed.term,
                expansion_method="modifier_expansion"
            ))
            count += 1
        
        self.logger.debug(f"Generated {len(keywords)} variations for seed '{seed.term}'")
        return keywords


class KeywordDiscoverer(LoggerMixin):
    """Main keyword discovery service."""
    
    def __init__(self, config: Optional[KeywordsConfig] = None):
        """Initialize keyword discoverer."""
        self.config = config or KeywordsConfig()
        self.gsc_integrator = GSCIntegrator()
        self.serp_client = SERPAPIClient()
        self.expander = KeywordExpander()
        self.scorer = KeywordScorer(config)
    
    def discover_keywords(
        self,
        project_id: str,
        seeds: Optional[List[KeywordSeed]] = None,
        use_gsc: bool = True,
        use_serp_api: bool = False,
        max_keywords: int = None
    ) -> List[DiscoveredKeyword]:
        """
        Discover keywords for a project.
        
        Args:
            project_id: Project ID
            seeds: Seed keywords to expand
            use_gsc: Whether to use GSC data
            use_serp_api: Whether to use SERP APIs
            max_keywords: Maximum keywords to return
            
        Returns:
            List of discovered keywords
        """
        max_keywords = max_keywords or self.config.max_keywords_per_run
        discovered_keywords = []
        
        # Get project info
        with get_db_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Expand seed keywords
            if seeds:
                self.logger.info(f"Expanding {len(seeds)} seed keywords")
                expanded = self.expander.expand_seed_keywords(seeds)
                discovered_keywords.extend(expanded)
            
            # Get keywords from GSC
            if use_gsc and self.gsc_integrator.credentials_file:
                self.logger.info("Fetching keywords from Google Search Console")
                
                # Try API first
                gsc_queries = self.gsc_integrator.fetch_queries(project.base_url)
                if gsc_queries:
                    for query_data in gsc_queries:
                        discovered_keywords.append(DiscoveredKeyword(
                            query=query_data['query'],
                            source="gsc_api",
                            search_volume=query_data.get('impressions'),
                        ))
                
                # Also get from database
                existing_gsc = self.gsc_integrator.get_existing_gsc_keywords(session, project_id)
                for query in existing_gsc:
                    if query not in [kw.query for kw in discovered_keywords]:
                        discovered_keywords.append(DiscoveredKeyword(
                            query=query,
                            source="gsc_database"
                        ))
            
            # Get suggestions from SERP API
            if use_serp_api and self.serp_client.api_key:
                self.logger.info("Fetching keyword suggestions from SERP API")
                
                # Get suggestions for seed terms
                base_terms = []
                if seeds:
                    base_terms = [seed.term for seed in seeds]
                else:
                    # Use existing keywords as base for suggestions
                    base_terms = list(set([kw.query for kw in discovered_keywords[:10]]))
                
                for base_term in base_terms:
                    suggestions = self.serp_client.search_suggestions(base_term)
                    for suggestion in suggestions:
                        if suggestion not in [kw.query for kw in discovered_keywords]:
                            discovered_keywords.append(DiscoveredKeyword(
                                query=suggestion,
                                source="serp_suggestions",
                                parent_seed=base_term,
                                expansion_method="api_suggestions"
                            ))
        
        # Remove duplicates and limit results
        unique_keywords = []
        seen = set()
        
        for kw in discovered_keywords:
            if kw.query not in seen and len(unique_keywords) < max_keywords:
                seen.add(kw.query)
                unique_keywords.append(kw)
        
        self.logger.info(
            f"Discovered {len(unique_keywords)} unique keywords",
            sources={
                source: len([kw for kw in unique_keywords if kw.source == source])
                for source in set(kw.source for kw in unique_keywords)
            }
        )
        
        return unique_keywords
    
    def save_keywords_to_db(
        self,
        project_id: str,
        keywords: List[DiscoveredKeyword],
        score_keywords: bool = True
    ) -> int:
        """
        Save discovered keywords to database.
        
        Args:
            project_id: Project ID
            keywords: Discovered keywords to save
            score_keywords: Whether to score keywords before saving
            
        Returns:
            Number of keywords saved
        """
        saved_count = 0
        
        with get_db_session() as session:
            for kw_data in keywords:
                try:
                    # Check if keyword already exists
                    existing = session.query(Keyword).filter(
                        Keyword.project_id == project_id,
                        Keyword.query == kw_data.query
                    ).first()
                    
                    if existing:
                        self.logger.debug(f"Keyword '{kw_data.query}' already exists, skipping")
                        continue
                    
                    # Score keyword if requested
                    score_data = {}
                    if score_keywords:
                        try:
                            score_result = self.scorer.score_keyword(
                                query=kw_data.query,
                                search_volume=kw_data.search_volume,
                                cpc=kw_data.cpc,
                                competition=kw_data.competition
                            )
                            score_data = {
                                'intent': score_result.intent.value,
                                'value_score': score_result.value_score,
                                'difficulty_proxy': score_result.difficulty_proxy
                            }
                        except Exception as e:
                            self.logger.warning(f"Failed to score keyword '{kw_data.query}': {e}")
                    
                    # Create keyword record
                    keyword = Keyword(
                        project_id=project_id,
                        query=kw_data.query,
                        source=kw_data.source,
                        search_volume=kw_data.search_volume,
                        cpc=kw_data.cpc,
                        competition=kw_data.competition,
                        serp_features=kw_data.serp_features or [],
                        **score_data
                    )
                    
                    session.add(keyword)
                    saved_count += 1
                    
                    if saved_count % 100 == 0:
                        session.commit()  # Commit in batches
                        self.logger.debug(f"Saved {saved_count} keywords so far")
                
                except Exception as e:
                    self.logger.error(f"Failed to save keyword '{kw_data.query}': {e}")
                    continue
            
            session.commit()
        
        self.logger.info(f"Saved {saved_count} keywords to database")
        return saved_count
    
    def export_keywords_to_csv(
        self,
        keywords: List[DiscoveredKeyword],
        output_path: Union[str, Path]
    ) -> None:
        """
        Export discovered keywords to CSV file.
        
        Args:
            keywords: Keywords to export
            output_path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionaries
        data = []
        for kw in keywords:
            kw_dict = asdict(kw)
            kw_dict['serp_features'] = json.dumps(kw_dict.get('serp_features') or [])
            data.append(kw_dict)
        
        # Write to CSV
        if data:
            try:
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(output_path, index=False)
                self.logger.info(f"Exported {len(keywords)} keywords to {output_path}")
            except ImportError:
                # Fallback to standard CSV writer
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    if data:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                self.logger.info(f"Exported {len(keywords)} keywords to {output_path} (using csv module)")
        else:
            self.logger.warning("No keywords to export")
    
    def run_keyword_discovery(
        self,
        project_id: str,
        seed_terms: Optional[List[str]] = None,
        output_csv: Optional[str] = None,
        save_to_db: bool = True
    ) -> List[DiscoveredKeyword]:
        """
        Run complete keyword discovery pipeline.
        
        Args:
            project_id: Project ID
            seed_terms: List of seed terms
            output_csv: Optional CSV output path
            save_to_db: Whether to save to database
            
        Returns:
            List of discovered keywords
        """
        self.logger.info(f"Starting keyword discovery for project {project_id}")
        
        # Convert seed terms to KeywordSeed objects
        seeds = []
        if seed_terms:
            seeds = [KeywordSeed(term=term) for term in seed_terms]
        elif self.config.seed_terms:
            seeds = [KeywordSeed(term=term) for term in self.config.seed_terms]
        
        # Discover keywords
        keywords = self.discover_keywords(
            project_id=project_id,
            seeds=seeds,
            use_gsc=True,
            use_serp_api=bool(self.serp_client.api_key)
        )
        
        # Filter by quality thresholds
        filtered_keywords = self._filter_keywords(keywords)
        
        # Save to database
        if save_to_db:
            self.save_keywords_to_db(project_id, filtered_keywords)
        
        # Export to CSV
        if output_csv:
            self.export_keywords_to_csv(filtered_keywords, output_csv)
        
        self.logger.info(f"Keyword discovery completed: {len(filtered_keywords)} keywords")
        return filtered_keywords
    
    def _filter_keywords(self, keywords: List[DiscoveredKeyword]) -> List[DiscoveredKeyword]:
        """Filter keywords based on quality thresholds."""
        filtered = []
        
        for kw in keywords:
            # Skip very short or long queries
            word_count = len(kw.query.split())
            if word_count < 2 or word_count > 10:
                continue
            
            # Skip queries with special characters (except hyphens and apostrophes)
            if not all(c.isalnum() or c.isspace() or c in "'-" for c in kw.query):
                continue
            
            # Skip overly branded queries (contain too many capital letters)
            if sum(1 for c in kw.query if c.isupper()) > len(kw.query) * 0.3:
                continue
            
            filtered.append(kw)
        
        self.logger.info(f"Filtered {len(keywords)} keywords to {len(filtered)} quality keywords")
        return filtered
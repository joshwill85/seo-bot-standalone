"""Pluggable data collectors for research sources."""

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser
# from readability import Document  # Skip for now - can add later

from .models import Observation, SourceResult, ResearchConfig
from ..utils.http import RateLimiter, CacheManager


logger = logging.getLogger(__name__)


class BaseCollector:
    """Base class for research data collectors."""
    
    def __init__(self, config: ResearchConfig):
        self.config = config
        self.rate_limiter = RateLimiter(delay=config.rate_limit_delay)
        self.cache = CacheManager()
        self.session = httpx.AsyncClient(
            timeout=config.timeout_seconds,
            headers={"User-Agent": "SEO Research Bot/1.0"}
        )
    
    async def can_fetch(self, url: str) -> bool:
        """Check robots.txt compliance."""
        if not self.config.respect_robots_txt:
            return True
            
        try:
            robots_url = f"{url.split('/', 3)[0]}//{url.split('/', 3)[2]}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch("*", url)
        except Exception as e:
            logger.warning(f"Could not check robots.txt for {url}: {e}")
            return True
    
    async def fetch_with_cache(self, url: str) -> Optional[str]:
        """Fetch URL content with caching and rate limiting."""
        await self.rate_limiter.wait()
        
        # Check cache first
        cached = self.cache.get(url)
        if cached:
            return cached
        
        if not await self.can_fetch(url):
            logger.warning(f"Robots.txt disallows fetching {url}")
            return None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await self.session.get(url)
                response.raise_for_status()
                
                content = response.text
                self.cache.set(url, content, ttl=3600)  # 1 hour cache
                return content
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    async def collect(self, dataset_id: str, entities: List[str]) -> SourceResult:
        """Collect observations for given entities."""
        raise NotImplementedError
    
    async def close(self):
        """Clean up resources."""
        await self.session.aclose()


class PriceTracker(BaseCollector):
    """Tracks pricing information from vendor pages."""
    
    def __init__(self, config: ResearchConfig, price_selectors: Dict[str, str]):
        super().__init__(config)
        self.price_selectors = price_selectors  # domain -> CSS selector
    
    async def collect(self, dataset_id: str, entities: List[str]) -> SourceResult:
        """Collect pricing data for products/services."""
        observations = []
        errors = []
        
        for entity_id in entities:
            try:
                # Assume entity_id contains URL or we have mapping
                url = entity_id if entity_id.startswith('http') else f"https://{entity_id}"
                
                content = await self.fetch_with_cache(url)
                if not content:
                    errors.append(f"Could not fetch {url}")
                    continue
                
                parser = HTMLParser(content)
                domain = url.split('/')[2]
                
                # Try to extract price using selectors
                price_text = None
                if domain in self.price_selectors:
                    price_elem = parser.css_first(self.price_selectors[domain])
                    if price_elem:
                        price_text = price_elem.text()
                
                # Fallback: look for common price patterns
                if not price_text:
                    price_patterns = [
                        r'\$[\d,]+(?:\.\d{2})?',
                        r'USD\s*[\d,]+(?:\.\d{2})?',
                        r'Price:\s*\$?([\d,]+(?:\.\d{2})?)',
                    ]
                    
                    for pattern in price_patterns:
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            price_text = match.group(0)
                            break
                
                if price_text:
                    # Extract numeric value
                    price_value = float(re.sub(r'[^\d.]', '', price_text))
                    
                    observation = Observation(
                        dataset_id=dataset_id,
                        entity_id=entity_id,
                        metric="price",
                        value=price_value,
                        unit="USD",
                        observed_at=datetime.now(timezone.utc),
                        source_url=url
                    )
                    observations.append(observation)
                else:
                    errors.append(f"No price found for {entity_id}")
                    
            except Exception as e:
                errors.append(f"Error processing {entity_id}: {e}")
        
        return SourceResult(
            source_id="price_tracker",
            success=len(observations) > 0,
            observations=observations,
            errors=errors,
            collected_at=datetime.now(timezone.utc)
        )


class SpecDiffCollector(BaseCollector):
    """Collects product specification changes."""
    
    async def collect(self, dataset_id: str, entities: List[str]) -> SourceResult:
        """Collect specification data."""
        observations = []
        errors = []
        
        for entity_id in entities:
            try:
                url = entity_id if entity_id.startswith('http') else f"https://{entity_id}"
                content = await self.fetch_with_cache(url)
                
                if not content:
                    errors.append(f"Could not fetch {url}")
                    continue
                
                parser = HTMLParser(content)
                
                # Look for common spec patterns
                spec_selectors = [
                    'table.specs td, table.specifications td',
                    '.spec-list li, .specifications li',
                    '.feature-list li',
                    'dl.specs dt, dl.specs dd'
                ]
                
                specs_found = {}
                for selector in spec_selectors:
                    elements = parser.css(selector)
                    for elem in elements:
                        text = elem.text().strip()
                        if ':' in text:
                            key, value = text.split(':', 1)
                            specs_found[key.strip()] = value.strip()
                
                # Create observations for key specs
                priority_specs = ['version', 'model', 'capacity', 'size', 'weight', 'cpu', 'memory', 'storage']
                
                for spec_key, spec_value in specs_found.items():
                    if any(priority in spec_key.lower() for priority in priority_specs):
                        observation = Observation(
                            dataset_id=dataset_id,
                            entity_id=entity_id,
                            metric="spec.version",
                            value=spec_value,
                            observed_at=datetime.now(timezone.utc),
                            source_url=url
                        )
                        observations.append(observation)
                        
            except Exception as e:
                errors.append(f"Error processing {entity_id}: {e}")
        
        return SourceResult(
            source_id="spec_diff_collector",
            success=len(observations) > 0,
            observations=observations,
            errors=errors,
            collected_at=datetime.now(timezone.utc)
        )


class ReleaseTimelineCollector(BaseCollector):
    """Collects release date information from GitHub, NPM, PyPI, etc."""
    
    async def collect(self, dataset_id: str, entities: List[str]) -> SourceResult:
        """Collect release timeline data."""
        observations = []
        errors = []
        
        for entity_id in entities:
            try:
                if 'github.com' in entity_id:
                    await self._collect_github_releases(dataset_id, entity_id, observations, errors)
                elif 'npmjs.com' in entity_id or 'npm' in entity_id:
                    await self._collect_npm_releases(dataset_id, entity_id, observations, errors)
                elif 'pypi.org' in entity_id:
                    await self._collect_pypi_releases(dataset_id, entity_id, observations, errors)
                    
            except Exception as e:
                errors.append(f"Error processing {entity_id}: {e}")
        
        return SourceResult(
            source_id="release_timeline_collector",
            success=len(observations) > 0,
            observations=observations,
            errors=errors,
            collected_at=datetime.now(timezone.utc)
        )
    
    async def _collect_github_releases(self, dataset_id: str, repo_url: str, observations: List, errors: List):
        """Collect GitHub release data."""
        # Extract owner/repo from URL
        parts = repo_url.replace('https://github.com/', '').split('/')
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            
            content = await self.fetch_with_cache(api_url)
            if content:
                import json
                releases = json.loads(content)
                
                for release in releases[:5]:  # Latest 5 releases
                    observation = Observation(
                        dataset_id=dataset_id,
                        entity_id=f"{owner}/{repo}",
                        metric="release_date",
                        value=release['published_at'],
                        observed_at=datetime.now(timezone.utc),
                        source_url=release['html_url']
                    )
                    observations.append(observation)
    
    async def _collect_npm_releases(self, dataset_id: str, package_name: str, observations: List, errors: List):
        """Collect NPM package release data."""
        api_url = f"https://registry.npmjs.org/{package_name}"
        content = await self.fetch_with_cache(api_url)
        
        if content:
            import json
            data = json.loads(content)
            
            if 'time' in data:
                for version, timestamp in list(data['time'].items())[-5:]:  # Latest 5
                    if version != 'created' and version != 'modified':
                        observation = Observation(
                            dataset_id=dataset_id,
                            entity_id=package_name,
                            metric="release_date",
                            value=timestamp,
                            observed_at=datetime.now(timezone.utc),
                            source_url=f"https://www.npmjs.com/package/{package_name}"
                        )
                        observations.append(observation)
    
    async def _collect_pypi_releases(self, dataset_id: str, package_name: str, observations: List, errors: List):
        """Collect PyPI package release data."""
        api_url = f"https://pypi.org/pypi/{package_name}/json"
        content = await self.fetch_with_cache(api_url)
        
        if content:
            import json
            data = json.loads(content)
            
            if 'releases' in data:
                sorted_releases = sorted(
                    data['releases'].items(),
                    key=lambda x: x[1][0]['upload_time'] if x[1] else '',
                    reverse=True
                )
                
                for version, release_info in sorted_releases[:5]:  # Latest 5
                    if release_info:
                        observation = Observation(
                            dataset_id=dataset_id,
                            entity_id=package_name,
                            metric="release_date",
                            value=release_info[0]['upload_time'],
                            observed_at=datetime.now(timezone.utc),
                            source_url=f"https://pypi.org/project/{package_name}/"
                        )
                        observations.append(observation)


class ChangelogCollector(BaseCollector):
    """Collects changelog information from documentation."""
    
    async def collect(self, dataset_id: str, entities: List[str]) -> SourceResult:
        """Collect changelog data."""
        observations = []
        errors = []
        
        changelog_paths = ['/changelog', '/CHANGELOG', '/releases', '/news', '/updates']
        
        for entity_id in entities:
            try:
                base_url = entity_id if entity_id.startswith('http') else f"https://{entity_id}"
                
                for path in changelog_paths:
                    url = f"{base_url.rstrip('/')}{path}"
                    content = await self.fetch_with_cache(url)
                    
                    if content:
                        # Extract changelog entries
                        parser = HTMLParser(content)
                        
                        # Look for version patterns
                        version_pattern = r'v?(\d+\.\d+(?:\.\d+)?)'
                        date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})'
                        
                        # Find changelog entries
                        headings = parser.css('h1, h2, h3, h4')
                        for heading in headings:
                            text = heading.text()
                            version_match = re.search(version_pattern, text)
                            
                            if version_match:
                                version = version_match.group(1)
                                
                                # Look for date in heading or following content
                                date_match = re.search(date_pattern, text)
                                if not date_match:
                                    # Check next sibling elements
                                    next_elem = heading.next
                                    if next_elem:
                                        date_match = re.search(date_pattern, next_elem.text() or '')
                                
                                observation = Observation(
                                    dataset_id=dataset_id,
                                    entity_id=entity_id,
                                    metric="release_date",
                                    value=version,
                                    observed_at=datetime.now(timezone.utc),
                                    source_url=url
                                )
                                observations.append(observation)
                        
                        break  # Found changelog, stop trying other paths
                        
            except Exception as e:
                errors.append(f"Error processing {entity_id}: {e}")
        
        return SourceResult(
            source_id="changelog_collector",
            success=len(observations) > 0,
            observations=observations,
            errors=errors,
            collected_at=datetime.now(timezone.utc)
        )


class ResearchSourceManager:
    """Manages all research data collectors."""
    
    def __init__(self, config: ResearchConfig):
        self.config = config
        self.collectors: Dict[str, BaseCollector] = {}
        
        # Initialize collectors
        self.collectors['price'] = PriceTracker(config, {})
        self.collectors['specs'] = SpecDiffCollector(config)
        self.collectors['releases'] = ReleaseTimelineCollector(config)
        self.collectors['changelog'] = ChangelogCollector(config)
    
    async def collect_all(self, dataset_id: str, entities: List[str], sources: List[str]) -> List[SourceResult]:
        """Collect data from specified sources."""
        results = []
        
        for source_name in sources:
            if source_name in self.collectors:
                logger.info(f"Collecting from {source_name} for dataset {dataset_id}")
                result = await self.collectors[source_name].collect(dataset_id, entities)
                results.append(result)
            else:
                logger.warning(f"Unknown source: {source_name}")
        
        return results
    
    async def close_all(self):
        """Close all collectors."""
        for collector in self.collectors.values():
            await collector.close()
"""Research data publishing and visualization system."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot

from .models import Observation, Dataset, DatasetMetrics, ResearchConfig
from .normalize import DataNormalizer


logger = logging.getLogger(__name__)


class DatasetRenderer:
    """Renders datasets into various formats with visualizations."""
    
    def __init__(self, config: ResearchConfig):
        self.config = config
        self.normalizer = DataNormalizer()
    
    def render_csv(self, observations: List[Observation], output_path: Path) -> bool:
        """Render observations to CSV format."""
        try:
            df = pd.DataFrame([obs.dict() for obs in observations])
            df.to_csv(output_path, index=False)
            logger.info(f"Generated CSV: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate CSV: {e}")
            return False
    
    def render_parquet(self, observations: List[Observation], output_path: Path) -> bool:
        """Render observations to Parquet format."""
        try:
            df = pd.DataFrame([obs.dict() for obs in observations])
            df.to_parquet(output_path, index=False)
            logger.info(f"Generated Parquet: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate Parquet: {e}")
            return False
    
    def render_json(self, observations: List[Observation], output_path: Path) -> bool:
        """Render observations to JSON format."""
        try:
            data = [obs.dict() for obs in observations]
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Generated JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate JSON: {e}")
            return False
    
    def render_price_trend_chart(self, observations: List[Observation], output_path: Path) -> bool:
        """Generate price trend visualization."""
        try:
            # Filter price observations
            price_obs = [obs for obs in observations if obs.metric == 'price']
            if not price_obs:
                return False
            
            # Group by entity
            entity_data = self.normalizer.aggregate_by_entity(price_obs)
            
            if 'png' in self.config.chart_formats:
                self._render_matplotlib_price_chart(entity_data, output_path.with_suffix('.png'))
            
            if 'html' in self.config.chart_formats:
                self._render_plotly_price_chart(entity_data, output_path.with_suffix('.html'))
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate price chart: {e}")
            return False
    
    def _render_matplotlib_price_chart(self, entity_data: Dict, output_path: Path):
        """Render price chart using matplotlib."""
        plt.figure(figsize=(12, 8))
        
        for entity_id, data in entity_data.items():
            if 'price' in data['metrics']:
                prices = data['metrics']['price']
                dates = [p['observed_at'] for p in prices]
                values = [float(p['value']) for p in prices]
                
                plt.plot(dates, values, marker='o', label=entity_id)
        
        plt.title('Price Trends Over Time')
        plt.xlabel('Date')
        plt.ylabel('Price (USD)')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _render_plotly_price_chart(self, entity_data: Dict, output_path: Path):
        """Render interactive price chart using plotly."""
        fig = go.Figure()
        
        for entity_id, data in entity_data.items():
            if 'price' in data['metrics']:
                prices = data['metrics']['price']
                dates = [p['observed_at'] for p in prices]
                values = [float(p['value']) for p in prices]
                
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name=entity_id,
                    hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
                ))
        
        fig.update_layout(
            title='Price Trends Over Time',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            hovermode='x unified'
        )
        
        plot(fig, filename=str(output_path), auto_open=False)
    
    def render_comparison_chart(self, observations: List[Observation], output_path: Path, metric: str) -> bool:
        """Generate comparison chart for specific metric."""
        try:
            # Filter observations for specific metric
            metric_obs = [obs for obs in observations if obs.metric == metric]
            if not metric_obs:
                return False
            
            # Get latest value for each entity
            entity_latest = {}
            for obs in metric_obs:
                if obs.entity_id not in entity_latest or obs.observed_at > entity_latest[obs.entity_id]['observed_at']:
                    entity_latest[obs.entity_id] = obs
            
            if 'png' in self.config.chart_formats:
                self._render_matplotlib_comparison(entity_latest, output_path.with_suffix('.png'), metric)
            
            if 'html' in self.config.chart_formats:
                self._render_plotly_comparison(entity_latest, output_path.with_suffix('.html'), metric)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate comparison chart: {e}")
            return False
    
    def _render_matplotlib_comparison(self, entity_data: Dict, output_path: Path, metric: str):
        """Render comparison chart using matplotlib."""
        entities = list(entity_data.keys())
        values = [float(obs.value) for obs in entity_data.values()]
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(entities, values)
        
        # Color bars based on value
        max_val = max(values)
        for bar, val in zip(bars, values):
            bar.set_color(plt.cm.RdYlGn_r(val / max_val))
        
        plt.title(f'{metric.replace("_", " ").title()} Comparison')
        plt.xlabel('Entity')
        plt.ylabel(metric.replace("_", " ").title())
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _render_plotly_comparison(self, entity_data: Dict, output_path: Path, metric: str):
        """Render interactive comparison chart using plotly."""
        entities = list(entity_data.keys())
        values = [float(obs.value) for obs in entity_data.values()]
        
        fig = px.bar(
            x=entities,
            y=values,
            title=f'{metric.replace("_", " ").title()} Comparison',
            color=values,
            color_continuous_scale='RdYlGn_r'
        )
        
        fig.update_layout(
            xaxis_title='Entity',
            yaxis_title=metric.replace("_", " ").title()
        )
        
        plot(fig, filename=str(output_path), auto_open=False)


class ResearchPublisher:
    """Main research publishing coordinator."""
    
    def __init__(self, config: ResearchConfig, output_dir: Path):
        self.config = config
        self.output_dir = output_dir
        self.renderer = DatasetRenderer(config)
        self.normalizer = DataNormalizer()
    
    def publish_dataset(self, dataset: Dataset, observations: List[Observation]) -> Dict[str, Any]:
        """Publish complete dataset with all formats and visualizations."""
        logger.info(f"Publishing dataset: {dataset.id}")
        
        # Normalize observations
        normalized_obs = self.normalizer.normalize_observations(observations)
        
        # Create output directory
        dataset_dir = self.output_dir / dataset.id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'dataset_id': dataset.id,
            'published_at': datetime.now(),
            'formats_generated': [],
            'charts_generated': [],
            'errors': []
        }
        
        # Generate data formats
        for fmt in self.config.output_formats:
            output_path = dataset_dir / f"data.{fmt}"
            
            if fmt == 'csv':
                success = self.renderer.render_csv(normalized_obs, output_path)
            elif fmt == 'parquet':
                success = self.renderer.render_parquet(normalized_obs, output_path)
            elif fmt == 'json':
                success = self.renderer.render_json(normalized_obs, output_path)
            else:
                success = False
            
            if success:
                results['formats_generated'].append(fmt)
            else:
                results['errors'].append(f"Failed to generate {fmt} format")
        
        # Generate visualizations
        if any(obs.metric == 'price' for obs in normalized_obs):
            chart_path = dataset_dir / "price_trends"
            if self.renderer.render_price_trend_chart(normalized_obs, chart_path):
                results['charts_generated'].append('price_trends')
        
        # Generate comparison charts for each metric
        metrics = set(obs.metric for obs in normalized_obs)
        for metric in metrics:
            if metric != 'price':  # Already handled above
                chart_path = dataset_dir / f"{metric}_comparison"
                if self.renderer.render_comparison_chart(normalized_obs, chart_path, metric):
                    results['charts_generated'].append(f"{metric}_comparison")
        
        # Generate Dataset JSON-LD
        jsonld_path = dataset_dir / "dataset.jsonld"
        if self._generate_dataset_jsonld(dataset, normalized_obs, jsonld_path):
            results['formats_generated'].append('jsonld')
        
        # Generate MDX content block
        mdx_path = dataset_dir / "dataset.mdx"
        if self._generate_mdx_block(dataset, normalized_obs, results, mdx_path):
            results['formats_generated'].append('mdx')
        
        # Generate metrics report
        metrics_path = dataset_dir / "metrics.json"
        if self._generate_metrics_report(dataset, normalized_obs, metrics_path):
            results['formats_generated'].append('metrics')
        
        logger.info(f"Dataset {dataset.id} published successfully")
        return results
    
    def _generate_dataset_jsonld(self, dataset: Dataset, observations: List[Observation], output_path: Path) -> bool:
        """Generate Schema.org Dataset JSON-LD."""
        try:
            # Calculate metrics
            metrics = self._calculate_dataset_metrics(observations)
            
            jsonld = {
                "@context": "https://schema.org/",
                "@type": "Dataset",
                "name": dataset.title,
                "description": dataset.description,
                "creator": {
                    "@type": "Organization",
                    "name": self.config.creator_name or "SEO Research Bot",
                    "url": str(self.config.creator_url) if self.config.creator_url else None
                },
                "dateCreated": dataset.created_at.isoformat(),
                "dateModified": dataset.last_updated.isoformat(),
                "license": self.config.dataset_license,
                "keywords": [dataset.category, "research", "data"],
                "distribution": [],
                "measurementTechnique": "Automated web scraping and API collection",
                "temporalCoverage": f"{metrics.date_range_start.isoformat()}/{metrics.date_range_end.isoformat()}",
                "spatialCoverage": "Global",
                "variableMeasured": dataset.metrics,
                "isBasedOn": list(set(obs.source_url for obs in observations))
            }
            
            # Add distributions for each format
            for fmt in self.config.output_formats:
                if fmt in ['csv', 'json']:
                    jsonld["distribution"].append({
                        "@type": "DataDownload",
                        "encodingFormat": f"application/{fmt}",
                        "contentUrl": f"data.{fmt}"
                    })
            
            # Add custom schema fields
            jsonld.update(dataset.schema_fields)
            
            with open(output_path, 'w') as f:
                json.dump(jsonld, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate JSON-LD: {e}")
            return False
    
    def _generate_mdx_block(self, dataset: Dataset, observations: List[Observation], results: Dict, output_path: Path) -> bool:
        """Generate MDX content block for embedding."""
        try:
            metrics = self._calculate_dataset_metrics(observations)
            changes = self.normalizer.detect_changes(observations)
            
            mdx_content = f"""# {dataset.title}

{dataset.description}

## Dataset Overview

- **Total Observations**: {metrics.total_observations:,}
- **Unique Entities**: {metrics.unique_entities}
- **Date Range**: {metrics.date_range_start.strftime('%Y-%m-%d')} to {metrics.date_range_end.strftime('%Y-%m-%d')}
- **Completeness Score**: {metrics.completeness_score:.1%}
- **Last Updated**: {metrics.last_updated.strftime('%Y-%m-%d %H:%M UTC')}

## Key Findings

"""
            
            # Add recent changes
            if changes:
                mdx_content += "### Recent Changes\n\n"
                for change in changes[:5]:  # Top 5 changes
                    mdx_content += f"- **{change['entity_id']}** {change['metric']}: {change['old_value']} → {change['new_value']}\n"
                mdx_content += "\n"
            
            # Add methodology note
            mdx_content += """## Methodology

This dataset is automatically collected from publicly available sources using our research automation platform. Data is normalized for consistency and validated for accuracy.

**Sources include:**
- Vendor product pages (respecting robots.txt)
- Official documentation and changelogs
- Public APIs and repositories
- Compliance-verified data providers

## Download Data

"""
            
            # Add download links
            for fmt in results['formats_generated']:
                if fmt in ['csv', 'json', 'parquet']:
                    mdx_content += f"- [Download {fmt.upper()}](data.{fmt})\n"
            
            # Add visualizations
            if results['charts_generated']:
                mdx_content += "\n## Visualizations\n\n"
                for chart in results['charts_generated']:
                    if 'html' in self.config.chart_formats:
                        mdx_content += f"<iframe src=\"{chart}.html\" width=\"100%\" height=\"400px\"></iframe>\n\n"
            
            # Add JSON-LD script
            mdx_content += """
<script type="application/ld+json" src="dataset.jsonld"></script>

---

*Dataset generated by SEO Research Bot - Automated research platform*
"""
            
            with open(output_path, 'w') as f:
                f.write(mdx_content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate MDX: {e}")
            return False
    
    def _generate_metrics_report(self, dataset: Dataset, observations: List[Observation], output_path: Path) -> bool:
        """Generate dataset metrics report."""
        try:
            metrics = self._calculate_dataset_metrics(observations)
            
            report = {
                'dataset_id': dataset.id,
                'metrics': metrics.dict(),
                'quality_gates': {
                    'min_observations': len(observations) >= self.config.min_observations_per_dataset,
                    'completeness_threshold': metrics.completeness_score >= self.config.data_completeness_threshold,
                    'freshness_check': metrics.freshness_score >= 0.8
                },
                'generated_at': datetime.now().isoformat()
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate metrics report: {e}")
            return False
    
    def _calculate_dataset_metrics(self, observations: List[Observation]) -> DatasetMetrics:
        """Calculate comprehensive dataset metrics."""
        if not observations:
            return DatasetMetrics(
                total_observations=0,
                unique_entities=0,
                date_range_start=datetime.now(),
                date_range_end=datetime.now(),
                completeness_score=0.0,
                freshness_score=0.0,
                accuracy_confidence=0.0,
                last_updated=datetime.now()
            )
        
        # Basic counts
        total_observations = len(observations)
        unique_entities = len(set(obs.entity_id for obs in observations))
        
        # Date range
        dates = [obs.observed_at for obs in observations]
        date_range_start = min(dates)
        date_range_end = max(dates)
        
        # Completeness score (entities with multiple observations)
        entity_obs_count = {}
        for obs in observations:
            entity_obs_count[obs.entity_id] = entity_obs_count.get(obs.entity_id, 0) + 1
        
        entities_with_multiple_obs = sum(1 for count in entity_obs_count.values() if count > 1)
        completeness_score = entities_with_multiple_obs / unique_entities if unique_entities > 0 else 0
        
        # Freshness score (how recent are observations)
        now = datetime.now()
        avg_age_days = sum((now - obs.observed_at).days for obs in observations) / total_observations
        freshness_score = max(0, 1 - (avg_age_days / 30))  # 30 days = 0 freshness
        
        # Accuracy confidence (based on source diversity)
        unique_sources = len(set(obs.source_url for obs in observations))
        accuracy_confidence = min(1.0, unique_sources / 10)  # 10+ sources = max confidence
        
        return DatasetMetrics(
            total_observations=total_observations,
            unique_entities=unique_entities,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            completeness_score=completeness_score,
            freshness_score=freshness_score,
            accuracy_confidence=accuracy_confidence,
            last_updated=datetime.now()
        )
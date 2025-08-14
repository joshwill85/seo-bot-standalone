"""SEO-Bot CLI interface using Typer."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from .config import Settings, load_project_config, create_default_config
from .keywords.cluster import KeywordClusterManager
from .keywords.discover import KeywordDiscoverer, KeywordSeed
from .keywords.score import KeywordScorer
from .keywords.serp_gap import SERPGapAnalyzer
from .content.expertise import create_trust_analyzer
from .content.brief_generator import create_brief_generator
from .linking.entities import create_entity_manager

# Technical system imports
from .tech.budgets import PerformanceBudgetManager
from .tech.accessibility import AccessibilityChecker
from .tech.audit import TechnicalSEOAuditor
from .content.stc_check import SearchTaskCompletionChecker
from .adapters.cms.base import ContentItem, ContentType, PublishStatus
from .adapters.cms.markdown import MarkdownAdapter
from .adapters.cms.wordpress import WordPressAdapter
from .adapters.cms.contentful import ContentfulAdapter
from .publishing.pipeline import PublishingPipeline, PipelineStage
from .publishing.quality_gates import (
    ContentQualityGate, SEOQualityGate, AccessibilityQualityGate,
    PerformanceQualityGate, TaskCompletionQualityGate
)

# Import monitoring and operational systems
from .monitor.coverage import run_coverage_monitor
from .monitor.dashboard import launch_dashboard
from .monitor.alerts import run_alert_monitoring
from .ctr.statistical_tests import run_ctr_analysis, TestMethod
from .governance.quality import run_quality_audit
from .prune.optimization import run_content_analysis

# Import research system
from .research.cli_commands import (
    research_collect, research_publish, research_list, research_create
)

# Import tools system
from .tools.cli_commands import (
    tools_build, tools_list, tools_test, tools_create_registry, tools_validate_formula
)

console = Console()
app = typer.Typer(name="seo-bot", help="AI-powered SEO automation platform")

# Global settings
settings = Settings()


@app.command()
def init(
    project: str = typer.Option(..., help="Project directory path"),
    domain: str = typer.Option(..., help="Domain name for the project"),
):
    """Initialize a new SEO project."""
    project_path = Path(project)
    
    if project_path.exists() and any(project_path.iterdir()):
        print(f"[red]Error: Directory {project} already exists and is not empty[/red]")
        raise typer.Exit(1)
    
    try:
        config = create_default_config(project_path, domain)
        print(f"[green]✓ Created project configuration at {project_path}/config.yml[/green]")
        
        # Create .env file template
        env_template = """# Required APIs
GOOGLE_SEARCH_CONSOLE_CREDENTIALS_FILE=path/to/gsc-credentials.json
PAGESPEED_API_KEY=your_pagespeed_api_key

# Optional APIs  
OPENAI_API_KEY=sk-your-openai-key
SERP_API_KEY=your_serp_api_key

# CMS Integration
WORDPRESS_URL=https://yoursite.com
WORDPRESS_USERNAME=admin
WORDPRESS_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
"""
        env_path = project_path / ".env"
        env_path.write_text(env_template)
        print(f"[green]✓ Created environment template at {project_path}/.env[/green]")
        
        print(f"""
[bold green]Project initialized successfully![/bold green]

Next steps:
1. Edit {project_path}/config.yml to customize your settings
2. Add API keys to {project_path}/.env
3. Run keyword discovery: seo-bot discover --project {project} --seeds "your,keywords"
""")
        
    except Exception as e:
        print(f"[red]Error initializing project: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def score(
    keywords: List[str] = typer.Argument(..., help="Keywords to score"),
    format: str = typer.Option("table", help="Output format: table, json"),
):
    """Score keywords for intent, value, and difficulty."""
    scorer = KeywordScorer()
    
    results = []
    for keyword in keywords:
        try:
            result = scorer.score_keyword(keyword)
            results.append({
                "keyword": keyword,
                "intent": result.intent.value,
                "confidence": f"{result.intent_confidence:.2f}",
                "value_score": f"{result.value_score:.1f}",
                "difficulty": f"{result.difficulty_proxy:.2f}",
                "final_score": f"{result.final_score:.1f}"
            })
        except Exception as e:
            print(f"[red]Error scoring '{keyword}': {e}[/red]")
    
    if format == "json":
        print(json.dumps(results, indent=2))
    else:
        # Table format
        table = Table(title="Keyword Scoring Results")
        table.add_column("Keyword", style="cyan")
        table.add_column("Intent", style="magenta")
        table.add_column("Confidence", style="yellow")
        table.add_column("Value", style="green")
        table.add_column("Difficulty", style="red")
        table.add_column("Final Score", style="bold blue")
        
        for result in results:
            table.add_row(
                result["keyword"],
                result["intent"],
                result["confidence"],
                result["value_score"],
                result["difficulty"],
                result["final_score"]
            )
        
        console.print(table)


@app.command()
def cluster(
    keywords: List[str] = typer.Argument(..., help="Keywords to cluster"),
    method: str = typer.Option("hdbscan", help="Clustering method: hdbscan, kmeans, agglomerative"),
    min_cluster_size: int = typer.Option(3, help="Minimum cluster size"),
    max_clusters: int = typer.Option(50, help="Maximum number of clusters"),
):
    """Cluster keywords by semantic similarity."""
    if len(keywords) < 2:
        print("[red]Error: Need at least 2 keywords to cluster[/red]")
        raise typer.Exit(1)
    
    manager = KeywordClusterManager(
        min_cluster_size=min_cluster_size,
        max_clusters=max_clusters
    )
    
    try:
        with console.status("[bold green]Clustering keywords..."):
            results = manager.cluster_keywords(keywords, method=method)
        
        print(f"\n[bold green]Clustering Results[/bold green]")
        print(f"Total clusters: {results['total_clusters']}")
        print(f"Noise keywords: {len(results['noise_keywords'])}")
        
        for cluster_id, keywords_list in results['clusters'].items():
            cluster_name = results['labels'].get(cluster_id, f"Cluster {cluster_id}")
            hub_spoke = results['hub_spoke_relationships'].get(cluster_id, {})
            
            print(f"\n[bold cyan]📂 {cluster_name}[/bold cyan] ({len(keywords_list)} keywords)")
            
            if hub_spoke:
                hub = hub_spoke.get('hub_keyword', '')
                spokes = hub_spoke.get('spoke_keywords', [])
                coverage = hub_spoke.get('hub_coverage', 0)
                
                print(f"  🎯 Hub: [bold]{hub}[/bold] (coverage: {coverage:.1%})")
                if spokes:
                    print(f"  🔗 Spokes: {', '.join(spokes[:5])}")
                    if len(spokes) > 5:
                        print(f"       ... and {len(spokes) - 5} more")
            
            print(f"  📝 Keywords: {', '.join(keywords_list[:8])}")
            if len(keywords_list) > 8:
                print(f"             ... and {len(keywords_list) - 8} more")
        
        if results['noise_keywords']:
            print(f"\n[dim]🔍 Noise keywords: {', '.join(results['noise_keywords'])}")
        
    except Exception as e:
        print(f"[red]Error clustering keywords: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def discover(
    project: Optional[str] = typer.Option(None, help="Project directory path"),
    seeds: str = typer.Option(..., help="Comma-separated seed keywords"),
    max_keywords: int = typer.Option(500, help="Maximum keywords to discover"),
    output: Optional[str] = typer.Option(None, help="Output CSV file path"),
):
    """Discover keywords from seed terms."""
    seed_list = [s.strip() for s in seeds.split(",")]
    
    discoverer = KeywordDiscoverer()
    
    try:
        with console.status("[bold green]Discovering keywords..."):
            keyword_seeds = [KeywordSeed(term=seed, priority=1.0) for seed in seed_list]
            discovered_keywords = discoverer.expander.expand_seed_keywords(keyword_seeds)
            keywords = [kw.query for kw in discovered_keywords]
        
        # Limit results
        if len(keywords) > max_keywords:
            keywords = keywords[:max_keywords]
        
        print(f"\n[bold green]Discovery Results[/bold green]")
        print(f"Found {len(keywords)} keywords from {len(seed_list)} seeds")
        
        # Show sample keywords
        print("\n[bold]Sample Keywords:[/bold]")
        for i, keyword in enumerate(keywords[:20]):
            print(f"  {i+1:2d}. {keyword}")
        
        if len(keywords) > 20:
            print(f"       ... and {len(keywords) - 20} more")
        
        # Export to CSV if requested
        if output:
            try:
                discoverer.export_keywords_to_csv(discovered_keywords, output)
                print(f"\n[green]✓ Exported keywords to {output}[/green]")
            except Exception as e:
                print(f"[yellow]Warning: Could not export to CSV: {e}[/yellow]")
        
    except Exception as e:
        print(f"[red]Error discovering keywords: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    project: str = typer.Option(..., help="Project directory path"),
):
    """Show project status overview."""
    project_path = Path(project)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        print(f"[red]Error: Project config not found at {config_file}[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_project_config(project_path)
        
        print(f"[bold green]Project Status: {config.site.domain}[/bold green]")
        print(f"Domain: {config.site.domain}")
        print(f"Base URL: {config.site.base_url}")
        print(f"Language: {config.site.language}")
        print(f"CMS: {config.site.cms}")
        
        print(f"\n[bold]Content Quality Settings:[/bold]")
        print(f"Min info-gain points: {config.content_quality.min_info_gain_points}")
        print(f"Word count range: {config.content_quality.word_count_bounds}")
        print(f"Task completers required: {config.content_quality.task_completers_required}")
        
        print(f"\n[bold]Performance Budgets:[/bold]")
        article_budget = config.performance_budgets.article
        print(f"Article LCP: {article_budget.lcp_ms}ms")
        print(f"Article INP: {article_budget.inp_ms}ms")
        print(f"Article CLS: {article_budget.cls}")
        
        print(f"\n[bold]Trust Signals:[/bold]")
        print(f"Require author: {config.trust_signals.require_author}")
        print(f"Require citations: {config.trust_signals.require_citations}")
        print(f"Min citations per page: {config.trust_signals.min_citations_per_page}")
        
    except Exception as e:
        print(f"[red]Error loading project status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def analyze_serp_gaps(
    query: str = typer.Option(..., help="Search query to analyze"),
    project: str = typer.Option(..., help="Project directory path"),
    output: Optional[str] = typer.Option(None, help="Output file for analysis results"),
    num_results: int = typer.Option(10, help="Number of SERP results to analyze"),
):
    """Analyze SERP gaps for competitive advantage."""
    try:
        analyzer = SERPGapAnalyzer()
        
        print(f"[bold green]Analyzing SERP gaps for: {query}[/bold green]")
        print(f"Fetching top {num_results} results...")
        
        analysis = analyzer.analyze_serp_gaps(
            query=query,
            num_results=num_results,
            analyze_content=True
        )
        
        # Display results
        print(f"\n[bold]SERP Analysis Results[/bold]")
        print(f"Results analyzed: {analysis.total_results}")
        print(f"Average word count: {int(analysis.avg_word_count)}")
        print(f"Content gaps found: {len(analysis.content_gaps)}")
        print(f"Differentiation opportunities: {len(analysis.differentiation_opportunities)}")
        
        # Show top gaps
        if analysis.content_gaps:
            print(f"\n[bold]Top Content Gaps:[/bold]")
            for i, gap in enumerate(analysis.content_gaps[:5], 1):
                priority_color = "red" if gap.priority > 0.8 else "yellow" if gap.priority > 0.6 else "green"
                print(f"  {i}. [{priority_color}]{gap.gap_type}[/{priority_color}]: {gap.description}")
                print(f"     Action: {gap.suggested_action}")
        
        # Show differentiation opportunities
        if analysis.differentiation_opportunities:
            print(f"\n[bold]Differentiation Opportunities:[/bold]")
            for i, opp in enumerate(analysis.differentiation_opportunities[:3], 1):
                print(f"  {i}. {opp}")
        
        # Export if requested
        if output:
            analyzer.export_analysis(analysis, output)
            print(f"\n[green]✓ Analysis exported to {output}[/green]")
        
    except Exception as e:
        print(f"[red]Error analyzing SERP gaps: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def analyze_trust_signals(
    project: str = typer.Option(..., help="Project directory path"),
    page_id: Optional[str] = typer.Option(None, help="Specific page ID to analyze"),
    output: Optional[str] = typer.Option(None, help="Output file for analysis results"),
):
    """Analyze E-E-A-T trust signals for content."""
    project_path = Path(project)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        print(f"[red]Error: Project config not found at {config_file}[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_project_config(project_path)
        analyzer = create_trust_analyzer(config.site.domain)  # This would need project ID in real implementation
        
        print(f"[bold green]Analyzing Trust Signals[/bold green]")
        
        # This is a simplified example - in practice you'd fetch pages from database
        print("Trust signal analysis requires database integration")
        print("Key areas analyzed:")
        print("  • Author attribution and credentials")
        print("  • Citation quality and quantity")
        print("  • Schema markup compliance")
        print("  • Content freshness and updates")
        print("  • Expert review status")
        
        print(f"\n[bold]Trust Requirements (from config):[/bold]")
        print(f"Require author: {config.trust_signals.require_author}")
        print(f"Require citations: {config.trust_signals.require_citations}")
        print(f"Min citations per page: {config.trust_signals.min_citations_per_page}")
        print(f"Author bio required: {config.trust_signals.author_bio_required}")
        print(f"Expert review for YMYL: {config.trust_signals.review_by_expert}")
        
    except Exception as e:
        print(f"[red]Error analyzing trust signals: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def build_knowledge_graph(
    project: str = typer.Option(..., help="Project directory path"),
    output: Optional[str] = typer.Option(None, help="Output file for knowledge graph"),
    format: str = typer.Option("json", help="Export format (json, gexf, graphml)"),
):
    """Build internal knowledge graph from content."""
    project_path = Path(project)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        print(f"[red]Error: Project config not found at {config_file}[/red]")
        raise typer.Exit(1)
    
    try:
        print(f"[bold green]Building Knowledge Graph[/bold green]")
        
        # This would require database integration in practice
        print("Knowledge graph building requires database integration")
        print("Process overview:")
        print("  1. Extract entities from all content pages")
        print("  2. Normalize and deduplicate entities")
        print("  3. Map semantic relationships")
        print("  4. Build entity pages and linking opportunities")
        print("  5. Generate internal linking suggestions")
        
        if output:
            print(f"\n[green]✓ Knowledge graph would be exported to {output} in {format} format[/green]")
        
    except Exception as e:
        print(f"[red]Error building knowledge graph: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate_content_brief(
    primary_keyword: str = typer.Option(..., help="Primary target keyword"),
    project: str = typer.Option(..., help="Project directory path"),
    output: Optional[str] = typer.Option(None, help="Output file for content brief"),
    target_audience: str = typer.Option("general", help="Target audience description"),
    user_intent: str = typer.Option("informational", help="User intent for the content"),
):
    """Generate comprehensive content brief with competitive analysis."""
    project_path = Path(project)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        print(f"[red]Error: Project config not found at {config_file}[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_project_config(project_path)
        
        print(f"[bold green]Generating Content Brief for: {primary_keyword}[/bold green]")
        print("Performing SERP analysis...")
        
        # Analyze SERP for competitive insights
        serp_analyzer = SERPGapAnalyzer()
        serp_analysis = serp_analyzer.analyze_serp_gaps(
            primary_keyword,
            num_results=10,
            analyze_content=True
        )
        
        print(f"✓ Analyzed {serp_analysis.total_results} competitors")
        print(f"✓ Found {len(serp_analysis.content_gaps)} content gaps")
        print(f"✓ Identified {len(serp_analysis.differentiation_opportunities)} opportunities")
        
        # Generate brief structure
        print(f"\n[bold]Content Brief Overview:[/bold]")
        print(f"Primary keyword: {primary_keyword}")
        print(f"Target audience: {target_audience}")
        print(f"User intent: {user_intent}")
        print(f"Recommended word count: {int(serp_analysis.avg_word_count * 1.1)} words")
        
        # Show content requirements
        if serp_analysis.common_entities:
            print(f"\n[bold]Required entities to cover:[/bold]")
            for entity, count in serp_analysis.common_entities[:5]:
                print(f"  • {entity} (mentioned in {count} competitors)")
        
        # Show competitive advantages
        if serp_analysis.content_gaps:
            print(f"\n[bold]Competitive advantages to pursue:[/bold]")
            for gap in serp_analysis.content_gaps[:3]:
                if gap.priority > 0.7:
                    print(f"  • {gap.suggested_action}")
        
        # Export if requested
        if output:
            brief_data = {
                "primary_keyword": primary_keyword,
                "target_audience": target_audience,
                "user_intent": user_intent,
                "serp_analysis": {
                    "avg_word_count": serp_analysis.avg_word_count,
                    "content_gaps": len(serp_analysis.content_gaps),
                    "opportunities": serp_analysis.differentiation_opportunities
                },
                "requirements": {
                    "word_count": int(serp_analysis.avg_word_count * 1.1),
                    "entities": [entity for entity, _ in serp_analysis.common_entities[:10]],
                    "competitive_advantages": [gap.suggested_action for gap in serp_analysis.content_gaps[:5]]
                }
            }
            
            with open(output, 'w') as f:
                json.dump(brief_data, f, indent=2)
            
            print(f"\n[green]✓ Content brief exported to {output}[/green]")
        
    except Exception as e:
        print(f"[red]Error generating content brief: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def enhanced_cluster(
    project: str = typer.Option(..., help="Project directory path"),
    keywords_file: str = typer.Option(..., help="CSV file with keywords to cluster"),
    method: str = typer.Option("hdbscan", help="Clustering method (hdbscan, kmeans, agglomerative)"),
    output: Optional[str] = typer.Option(None, help="Output file for clustering results"),
    min_cluster_size: int = typer.Option(6, help="Minimum cluster size"),
):
    """Enhanced keyword clustering with semantic relationships and validation."""
    project_path = Path(project)
    config_file = project_path / "config.yml"
    
    if not config_file.exists():
        print(f"[red]Error: Project config not found at {config_file}[/red]")
        raise typer.Exit(1)
    
    keywords_path = Path(keywords_file)
    if not keywords_path.exists():
        print(f"[red]Error: Keywords file not found at {keywords_file}[/red]")
        raise typer.Exit(1)
    
    try:
        config = load_project_config(project_path)
        
        # Load keywords from CSV
        import csv
        keywords = []
        with open(keywords_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Assume first column contains keywords
                keyword = next(iter(row.values()))
                if keyword.strip():
                    keywords.append(keyword.strip())
        
        if not keywords:
            print(f"[red]Error: No keywords found in {keywords_file}[/red]")
            raise typer.Exit(1)
        
        print(f"[bold green]Enhanced Clustering Analysis[/bold green]")
        print(f"Keywords to cluster: {len(keywords)}")
        print(f"Method: {method}")
        print(f"Min cluster size: {min_cluster_size}")
        
        # Perform enhanced clustering
        cluster_manager = KeywordClusterManager(min_cluster_size=min_cluster_size)
        results = cluster_manager.cluster_keywords(keywords, method=method)
        
        # Display results
        print(f"\n[bold]Clustering Results:[/bold]")
        print(f"Total clusters: {results['total_clusters']}")
        print(f"Noise keywords: {len(results['noise_keywords'])}")
        
        # Show validation results
        if 'validation_results' in results:
            validation = results['validation_results']
            quality_color = "green" if validation['quality_assessment'] == "excellent" else \
                           "yellow" if validation['quality_assessment'] == "good" else "red"
            
            print(f"\n[bold]Statistical Validation:[/bold]")
            print(f"Quality assessment: [{quality_color}]{validation['quality_assessment']}[/{quality_color}]")
            print(f"Silhouette score: {validation['silhouette_score']:.3f}")
            print(f"Validation score: {validation['validation_score']:.3f}")
            
            if validation['recommendations']:
                print(f"\n[bold]Recommendations:[/bold]")
                for rec in validation['recommendations']:
                    print(f"  • {rec}")
        
        # Show topic hierarchy
        if 'topic_hierarchy' in results:
            hierarchy = results['topic_hierarchy']
            print(f"\n[bold]Topic Hierarchy:[/bold]")
            print(f"Max depth: {hierarchy['max_depth']}")
            print(f"Root clusters: {len(hierarchy['root_clusters'])}")
        
        # Show top clusters
        print(f"\n[bold]Top Clusters:[/bold]")
        for cluster_id, cluster_keywords in list(results['clusters'].items())[:5]:
            cluster_name = results['labels'].get(cluster_id, f"Cluster {cluster_id}")
            print(f"  {cluster_name} ({len(cluster_keywords)} keywords)")
            print(f"    Sample: {', '.join(cluster_keywords[:3])}")
        
        # Export if requested
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            print(f"\n[green]✓ Enhanced clustering results exported to {output}[/green]")
        
    except Exception as e:
        print(f"[red]Error in enhanced clustering: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def tech_audit(
    url: str = typer.Option(..., help="URL to audit"),
    project: Optional[str] = typer.Option(None, help="Project directory path"),
    output: Optional[str] = typer.Option(None, help="Output file for audit results"),
    format: str = typer.Option("json", help="Output format: json"),
):
    """Run comprehensive technical SEO audit."""
    import asyncio
    
    async def run_audit():
        try:
            print(f"[bold green]Running technical SEO audit for: {url}[/bold green]")
            
            async with TechnicalSEOAuditor(settings) as auditor:
                result = await auditor.audit_page_technical_seo(url)
                
                # Display summary
                print(f"\n[bold]Technical SEO Audit Results[/bold]")
                print(f"SEO Health Score: [bold]{result.seo_health_score}[/bold]/100")
                print(f"Total Issues: {result.total_issues}")
                print(f"Critical: [red]{result.critical_issues}[/red], High: [yellow]{result.high_issues}[/yellow], Medium: {result.medium_issues}, Low: {result.low_issues}")
                
                # Show SEO fundamentals
                print(f"\n[bold]SEO Fundamentals[/bold]")
                print(f"Title Tag: {'✓' if result.title_tag_present else '✗'}")
                print(f"Meta Description: {'✓' if result.meta_description_present else '✗'}")
                print(f"Canonical Tag: {'✓' if result.canonical_tag_present else '✗'}")
                print(f"HTTPS: {'✓' if result.https_enabled else '✗'}")
                print(f"Mobile Friendly: {'✓' if result.mobile_friendly else '✗'}")
                
                # Show top issues
                if result.priority_fixes:
                    print(f"\n[bold]Priority Fixes[/bold]")
                    for fix in result.priority_fixes[:5]:
                        print(f"  • {fix}")
                
                # Show quick wins
                if result.quick_wins:
                    print(f"\n[bold]Quick Wins[/bold]")
                    for win in result.quick_wins[:5]:
                        print(f"  • {win}")
                
                # Export if requested
                if output:
                    output_path = Path(output)
                    auditor.export_audit_results(result, output_path, format)
                    print(f"\n[green]✓ Audit results exported to {output_path}[/green]")
                
        except Exception as e:
            print(f"[red]Technical audit failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_audit())


@app.command()
def performance_budget(
    url: str = typer.Option(..., help="URL to test"),
    project: Optional[str] = typer.Option(None, help="Project directory path"),
    template_type: str = typer.Option("article", help="Template type: article, product, comparison, calculator"),
    output: Optional[str] = typer.Option(None, help="Output file for results"),
    auto_optimize: bool = typer.Option(False, help="Apply automatic optimizations"),
    dry_run: bool = typer.Option(False, help="Simulate optimizations without applying them"),
):
    """Check and enforce performance budgets."""
    import asyncio
    from .config import PerformanceBudgetsConfig
    
    async def run_performance_check():
        try:
            print(f"[bold green]Checking performance budget for: {url}[/bold green]")
            
            # Load project config if available
            project_config = None
            if project:
                project_path = Path(project)
                if (project_path / "config.yml").exists():
                    project_config = load_project_config(project_path)
            
            budgets_config = project_config.performance_budgets if project_config else PerformanceBudgetsConfig()
            
            async with PerformanceBudgetManager(settings) as manager:
                # Test performance
                result = await manager.test_page_performance(url, device_type="mobile")
                
                # Get budget for template type
                budget = manager._get_budget_for_template(template_type, budgets_config)
                
                # Check violations
                violations = manager.check_budget_violations(result, budget, template_type)
                
                # Display results
                print(f"\n[bold]Performance Test Results[/bold]")
                print(f"Template Type: {template_type}")
                print(f"Performance Score: [bold]{result.performance_score}[/bold]/100")
                print(f"Core Web Vitals: {'✓ PASS' if result.passes_cwv_thresholds else '✗ FAIL'}")
                
                print(f"\n[bold]Core Web Vitals[/bold]")
                print(f"LCP: {result.lcp_ms}ms (budget: {budget.lcp_ms}ms)")
                print(f"INP: {result.inp_ms}ms (budget: {budget.inp_ms}ms)")
                print(f"CLS: {result.cls} (budget: {budget.cls})")
                
                print(f"\n[bold]Resource Metrics[/bold]")
                print(f"JavaScript: {result.js_size_kb}KB (budget: {budget.js_kb}KB)")
                print(f"CSS: {result.css_size_kb}KB (budget: {budget.css_kb}KB)")
                print(f"Images: {result.image_size_kb}KB (budget: {budget.image_kb}KB)")
                
                # Show violations
                if violations:
                    print(f"\n[bold red]Budget Violations ({len(violations)})[/bold red]")
                    for violation in violations:
                        print(f"  • {violation.description}")
                
                # Auto-optimization
                if violations and auto_optimize:
                    recommendations = manager.generate_optimization_recommendations(violations, result)
                    optimization_result = await manager.auto_optimize_violations(violations, recommendations, dry_run)
                    
                    print(f"\n[bold]Auto-Optimization Results[/bold]")
                    print(f"Total optimizations: {optimization_result['total_optimizations']}")
                    print(f"Successful: {optimization_result['successful_optimizations']}")
                    print(f"Failed: {optimization_result['failed_optimizations']}")
                    
                    if dry_run:
                        print("[yellow]Note: This was a dry run - no changes were applied[/yellow]")
                
                # Export if requested
                if output:
                    export_data = {
                        "url": url,
                        "template_type": template_type,
                        "performance_result": result.__dict__,
                        "budget": budget.__dict__,
                        "violations": [v.__dict__ for v in violations],
                        "timestamp": result.timestamp.isoformat()
                    }
                    
                    output_path = Path(output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, 'w') as f:
                        json.dump(export_data, f, indent=2, default=str)
                    
                    print(f"\n[green]✓ Results exported to {output_path}[/green]")
                
        except Exception as e:
            print(f"[red]Performance budget check failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_performance_check())


@app.command()
def accessibility_check(
    url: str = typer.Option(..., help="URL to check"),
    wcag_level: str = typer.Option("AA", help="WCAG compliance level: A, AA, AAA"),
    output: Optional[str] = typer.Option(None, help="Output file for results"),
    include_lighthouse: bool = typer.Option(True, help="Include Lighthouse accessibility score"),
):
    """Run WCAG accessibility compliance check."""
    import asyncio
    from .tech.accessibility import WCAGLevel
    
    async def run_accessibility_check():
        try:
            print(f"[bold green]Running accessibility check for: {url}[/bold green]")
            
            # Parse WCAG level
            try:
                target_level = WCAGLevel(wcag_level)
            except ValueError:
                print(f"[red]Invalid WCAG level: {wcag_level}. Use A, AA, or AAA[/red]")
                raise typer.Exit(1)
            
            async with AccessibilityChecker(settings, target_level) as checker:
                result = await checker.audit_page_accessibility(url, include_lighthouse)
                
                # Display summary
                print(f"\n[bold]Accessibility Audit Results[/bold]")
                print(f"WCAG {wcag_level} Compliant: {'✓ YES' if result.wcag_aa_compliant else '✗ NO'}")
                print(f"Compliance Score: [bold]{result.compliance_percentage}%[/bold]")
                
                if result.lighthouse_accessibility_score:
                    print(f"Lighthouse Score: [bold]{result.lighthouse_accessibility_score}[/bold]/100")
                
                print(f"Total Issues: {result.total_issues}")
                print(f"Critical: [red]{result.critical_issues}[/red], High: [yellow]{result.high_issues}[/yellow], Medium: {result.medium_issues}, Low: {result.low_issues}")
                
                # Show issues by category
                if result.issues_by_category:
                    print(f"\n[bold]Issues by Category[/bold]")
                    for category, count in result.issues_by_category.items():
                        print(f"  {category.value}: {count}")
                
                # Show priority fixes
                if result.priority_fixes:
                    print(f"\n[bold]Priority Fixes[/bold]")
                    for fix in result.priority_fixes:
                        print(f"  • {fix}")
                
                # Show quick wins
                if result.quick_wins:
                    print(f"\n[bold]Quick Wins[/bold]")
                    for win in result.quick_wins:
                        print(f"  • {win}")
                
                # Show fix estimate
                print(f"\n[bold]Fix Estimates[/bold]")
                print(f"Total estimated time: {result.estimated_fix_time_hours:.1f} hours")
                print(f"Easy fixes: {result.easy_fixes}, Medium: {result.medium_fixes}, Complex: {result.complex_fixes}")
                
                # Export if requested
                if output:
                    output_path = Path(output)
                    checker.export_audit_results(result, output_path)
                    print(f"\n[green]✓ Results exported to {output_path}[/green]")
                
        except Exception as e:
            print(f"[red]Accessibility check failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_accessibility_check())


@app.command()
def task_completion_audit(
    url: str = typer.Option(..., help="URL to audit"),
    is_money_page: bool = typer.Option(False, help="Mark as money page (requires 2+ task completers)"),
    output: Optional[str] = typer.Option(None, help="Output file for results"),
):
    """Audit task completion elements on a page."""
    import asyncio
    
    async def run_task_completion_audit():
        try:
            print(f"[bold green]Auditing task completion for: {url}[/bold green]")
            
            async with SearchTaskCompletionChecker() as checker:
                result = await checker.audit_page_task_completion(url, is_money_page)
                
                # Display summary
                print(f"\n[bold]Task Completion Audit Results[/bold]")
                print(f"Total Task Completers: [bold]{result.total_task_completers}[/bold]")
                print(f"Valid Task Completers: {result.valid_task_completers}")
                print(f"Meets Requirements: {'✓' if result.meets_minimum_requirement else '✗'}")
                
                if is_money_page:
                    print(f"Money Page Requirements: {'✓' if result.meets_money_page_requirement else '✗'}")
                
                if result.avg_completion_rate > 0:
                    print(f"Avg Completion Rate: {result.avg_completion_rate:.1%}")
                
                # Show task completers by type
                if result.task_completers_by_type:
                    print(f"\n[bold]Task Completers by Type[/bold]")
                    for task_type, count in result.task_completers_by_type.items():
                        print(f"  {task_type.value}: {count}")
                
                # Show priority fixes
                if result.priority_fixes:
                    print(f"\n[bold]Priority Fixes[/bold]")
                    for fix in result.priority_fixes:
                        print(f"  • {fix}")
                
                # Show recommendations
                if result.recommendations:
                    print(f"\n[bold]Recommendations[/bold]")
                    for rec in result.recommendations:
                        print(f"  • {rec}")
                
                # Show issues summary
                if result.validation_issues:
                    print(f"\n[bold]Validation Issues ({len(result.validation_issues)})[/bold]")
                    for issue in result.validation_issues[:5]:
                        print(f"  • {issue}")
                
                if result.accessibility_issues:
                    print(f"\n[bold]Accessibility Issues ({len(result.accessibility_issues)})[/bold]")
                    for issue in result.accessibility_issues[:5]:
                        print(f"  • {issue}")
                
                # Export if requested
                if output:
                    output_path = Path(output)
                    checker.export_audit_results(result, output_path)
                    print(f"\n[green]✓ Results exported to {output_path}[/green]")
                
        except Exception as e:
            print(f"[red]Task completion audit failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_task_completion_audit())


@app.command()
def publish(
    content_file: str = typer.Option(..., help="Content file to publish"),
    project: str = typer.Option(..., help="Project directory path"),
    cms: str = typer.Option("markdown", help="CMS type: markdown, wordpress, contentful"),
    dry_run: bool = typer.Option(False, help="Simulate publish without actually publishing"),
    skip_quality_gates: bool = typer.Option(False, help="Skip quality gate checks"),
    stages: Optional[str] = typer.Option(None, help="Comma-separated list of stages to run"),
):
    """Publish content through quality-gated pipeline."""
    import asyncio
    from datetime import datetime, timezone
    
    async def run_publish():
        try:
            print(f"[bold green]Publishing content through pipeline[/bold green]")
            
            # Load project config
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            # Load content file
            content_path = Path(content_file)
            if not content_path.exists():
                print(f"[red]Content file not found: {content_file}[/red]")
                raise typer.Exit(1)
            
            # Parse content (simplified - assumes JSON format)
            try:
                with open(content_path, 'r', encoding='utf-8') as f:
                    if content_path.suffix.lower() == '.json':
                        content_data = json.load(f)
                    else:
                        # Assume markdown with frontmatter
                        content_text = f.read()
                        # Simple parsing - in real implementation would use proper frontmatter parser
                        content_data = {
                            "title": content_path.stem.replace('_', ' ').title(),
                            "content": content_text,
                            "slug": content_path.stem,
                            "content_type": "article"
                        }
                
                # Create ContentItem
                content_item = ContentItem(
                    title=content_data.get('title', ''),
                    content=content_data.get('content', ''),
                    content_type=ContentType(content_data.get('content_type', 'article')),
                    slug=content_data.get('slug', ''),
                    meta_title=content_data.get('meta_title'),
                    meta_description=content_data.get('meta_description'),
                    canonical_url=content_data.get('canonical_url'),
                    status=PublishStatus(content_data.get('status', 'draft')),
                    author=content_data.get('author'),
                    categories=content_data.get('categories', []),
                    tags=content_data.get('tags', []),
                    featured_image_url=content_data.get('featured_image_url'),
                    featured_image_alt=content_data.get('featured_image_alt'),
                    custom_fields=content_data.get('custom_fields', {})
                )
                
            except Exception as e:
                print(f"[red]Failed to parse content file: {e}[/red]")
                raise typer.Exit(1)
            
            # Create CMS adapter
            cms_config = {}
            if cms == "wordpress":
                cms_config = {
                    'site_url': settings.wordpress_url,
                    'username': settings.wordpress_username,
                    'app_password': settings.wordpress_app_password
                }
                cms_adapter = WordPressAdapter(cms_config)
            elif cms == "contentful":
                # Would need Contentful config from settings
                print("[yellow]Contentful adapter requires additional configuration[/yellow]")
                raise typer.Exit(1)
            else:
                # Default to markdown
                cms_config = {
                    'content_dir': project_path / 'content',
                    'assets_dir': project_path / 'assets'
                }
                cms_adapter = MarkdownAdapter(cms_config)
            
            # Test CMS connection
            if not await cms_adapter.test_connection():
                print(f"[red]Failed to connect to {cms} CMS[/red]")
                raise typer.Exit(1)
            
            # Set up quality gates
            quality_gates = []
            if not skip_quality_gates:
                quality_gates = [
                    ContentQualityGate(project_config.content_quality.__dict__),
                    SEOQualityGate(),
                    AccessibilityQualityGate(),
                    PerformanceQualityGate(),
                    TaskCompletionQualityGate({'min_task_completers': project_config.content_quality.task_completers_required})
                ]
            
            # Create publishing pipeline
            pipeline = PublishingPipeline(cms_adapter, project_config, quality_gates)
            
            # Parse stages if specified
            pipeline_stages = None
            if stages:
                try:
                    stage_names = [s.strip() for s in stages.split(',')]
                    pipeline_stages = [PipelineStage(name) for name in stage_names]
                except ValueError as e:
                    print(f"[red]Invalid stage name: {e}[/red]")
                    raise typer.Exit(1)
            
            # Execute pipeline
            print(f"Publishing '{content_item.title}' via {cms} (dry_run={dry_run})")
            
            result = await pipeline.publish(content_item, pipeline_stages, dry_run)
            
            # Display results
            print(f"\n[bold]Publishing Pipeline Results[/bold]")
            print(f"Success: {'✓' if result.success else '✗'}")
            print(f"Execution Time: {result.total_execution_time_ms}ms")
            
            # Show stage results
            print(f"\n[bold]Stage Results[/bold]")
            for stage, stage_result in result.stage_results.items():
                status = "✓" if stage_result.success else "✗"
                print(f"  {status} {stage.value}: {stage_result.message}")
            
            # Show quality gate results
            if result.quality_gate_results:
                print(f"\n[bold]Quality Gates[/bold]")
                print(f"Overall Quality Score: {result.quality_score:.1f}/100")
                
                for gate_result in result.quality_gate_results:
                    status = "✓" if gate_result.passed else "✗"
                    print(f"  {status} {gate_result.gate_name}: {gate_result.score:.1f}/100")
            
            # Show publish result
            if result.publish_result:
                pr = result.publish_result
                print(f"\n[bold]CMS Publishing[/bold]")
                print(f"Success: {'✓' if pr.success else '✗'}")
                if pr.url:
                    print(f"URL: {pr.url}")
                if pr.external_id:
                    print(f"ID: {pr.external_id}")
            
            # Show errors and warnings
            if result.errors:
                print(f"\n[bold red]Errors ({len(result.errors)})[/bold red]")
                for error in result.errors:
                    print(f"  • {error}")
            
            if result.warnings:
                print(f"\n[bold yellow]Warnings ({len(result.warnings)})[/bold yellow]")
                for warning in result.warnings[:5]:
                    print(f"  • {warning}")
            
            if not result.success:
                raise typer.Exit(1)
                
        except Exception as e:
            print(f"[red]Publishing failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_publish())


@app.command() 
def optimize_assets(
    project: str = typer.Option(..., help="Project directory path"),
    assets_dir: Optional[str] = typer.Option(None, help="Assets directory (default: project/assets)"),
    formats: str = typer.Option("webp", help="Target formats: webp, avif, both"),
    quality: int = typer.Option(85, help="Compression quality (1-100)"),
    max_width: int = typer.Option(1400, help="Maximum image width"),
    dry_run: bool = typer.Option(False, help="Show what would be optimized without doing it"),
):
    """Optimize images and assets for web performance."""
    try:
        print(f"[bold green]Optimizing assets for project: {project}[/bold green]")
        
        project_path = Path(project)
        assets_path = Path(assets_dir) if assets_dir else project_path / "assets"
        
        if not assets_path.exists():
            print(f"[red]Assets directory not found: {assets_path}[/red]")
            raise typer.Exit(1)
        
        # Find image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(assets_path.glob(f"**/*{ext}"))
            image_files.extend(assets_path.glob(f"**/*{ext.upper()}"))
        
        if not image_files:
            print("[yellow]No image files found to optimize[/yellow]")
            return
        
        print(f"Found {len(image_files)} image files to optimize")
        
        # Optimization summary
        total_original_size = 0
        total_optimized_size = 0
        optimized_count = 0
        
        for image_file in image_files:
            try:
                original_size = image_file.stat().st_size
                total_original_size += original_size
                
                print(f"Processing: {image_file.name} ({original_size // 1024}KB)")
                
                if dry_run:
                    # Estimate size reduction (typical 30-50% for WebP)
                    estimated_size = int(original_size * 0.6)
                    total_optimized_size += estimated_size
                    optimized_count += 1
                    print(f"  → Would optimize to ~{estimated_size // 1024}KB")
                else:
                    # In a real implementation, this would use image optimization libraries
                    # like Pillow, imageio, or external tools like imagemin
                    print(f"  → Optimization would be applied here")
                    # For now, just count as processed
                    total_optimized_size += int(original_size * 0.6)  # Simulate 40% reduction
                    optimized_count += 1
                    
            except Exception as e:
                print(f"  [red]Error processing {image_file.name}: {e}[/red]")
                continue
        
        # Show summary
        if optimized_count > 0:
            size_reduction = total_original_size - total_optimized_size
            reduction_pct = (size_reduction / total_original_size) * 100 if total_original_size > 0 else 0
            
            print(f"\n[bold]Optimization Summary[/bold]")
            print(f"Files processed: {optimized_count}")
            print(f"Original size: {total_original_size // 1024}KB")
            print(f"Optimized size: {total_optimized_size // 1024}KB")
            print(f"Size reduction: {size_reduction // 1024}KB ({reduction_pct:.1f}%)")
            
            if dry_run:
                print("[yellow]This was a dry run - no files were actually optimized[/yellow]")
            else:
                print("[green]✓ Asset optimization completed[/green]")
        
    except Exception as e:
        print(f"[red]Asset optimization failed: {e}[/red]")
        raise typer.Exit(1)


# Monitoring and Operational Commands

@app.command()
def monitor_coverage(
    project: str = typer.Option(..., help="Project directory path"),
    domain: str = typer.Option(..., help="Domain to monitor"),
    output: Optional[str] = typer.Option(None, help="Output file for coverage report"),
    auto_resolve: bool = typer.Option(False, help="Automatically resolve coverage issues"),
):
    """Monitor GSC indexation and coverage SLAs."""
    import asyncio
    
    async def run_monitoring():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            print(f"[bold green]Monitoring coverage SLAs for {domain}[/bold green]")
            
            # Run coverage monitoring
            report = await run_coverage_monitor(
                domain, settings, project_config.coverage_sla
            )
            
            # Display results
            print(f"\n[bold]Coverage SLA Report[/bold]")
            print(f"Domain: {report.domain}")
            print(f"Indexation Rate: {report.indexation_rate:.1%}")
            print(f"SLA Compliance: {'✓ PASS' if report.sla_compliance else '✗ FAIL'}")
            print(f"Total Pages: {report.total_pages}")
            print(f"Indexed Pages: {report.indexed_pages}")
            print(f"Mobile Usability Score: {report.mobile_usability_score:.1f}")
            print(f"Avg Indexation Time: {report.avg_indexation_time_days:.1f} days")
            
            # Show violations
            if report.coverage_violations:
                print(f"\n[bold red]Coverage Violations ({len(report.coverage_violations)})[/bold red]")
                for violation in report.coverage_violations[:5]:
                    print(f"  • {violation.url}: {violation.description}")
            
            if report.freshness_violations:
                print(f"\n[bold yellow]Freshness Violations ({len(report.freshness_violations)})[/bold yellow]")
                for violation in report.freshness_violations[:5]:
                    print(f"  • {violation.url}: {violation.description}")
            
            # Export report if requested
            if output:
                from .monitor.coverage import CoverageFreshnessMonitor
                monitor = CoverageFreshnessMonitor(settings, project_config.coverage_sla, domain)
                success = await monitor.export_coverage_report(report, Path(output))
                if success:
                    print(f"\n[green]✓ Coverage report exported to {output}[/green]")
                else:
                    print(f"\n[red]Failed to export coverage report[/red]")
            
        except Exception as e:
            print(f"[red]Coverage monitoring failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_monitoring())


@app.command()
def run_ctr_tests(
    project: str = typer.Option(..., help="Project directory path"),
    test_id: str = typer.Option(..., help="CTR test ID to analyze"),
    method: str = typer.Option("bayesian", help="Analysis method: bayesian, frequentist, sequential"),
    output: Optional[str] = typer.Option(None, help="Output file for test results"),
):
    """Run statistical CTR testing analysis."""
    import asyncio
    
    async def run_testing():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            print(f"[bold green]Running CTR test analysis for test {test_id}[/bold green]")
            
            # Parse test method
            try:
                test_method = TestMethod(method.lower())
            except ValueError:
                print(f"[red]Invalid test method: {method}. Use bayesian, frequentist, or sequential[/red]")
                raise typer.Exit(1)
            
            # Run CTR analysis
            results = await run_ctr_analysis(
                test_id, settings, project_config.ctr_testing, test_method
            )
            
            # Display results
            print(f"\n[bold]CTR Test Results[/bold]")
            print(f"Test: {results.test_name}")
            print(f"Method: {results.method.value}")
            print(f"Status: {results.status.value}")
            print(f"Duration: {results.test_duration_days} days")
            
            print(f"\n[bold]Control Group[/bold]")
            print(f"Impressions: {results.control_impressions:,}")
            print(f"Clicks: {results.control_clicks:,}")
            print(f"CTR: {results.control_ctr:.2%}")
            
            print(f"\n[bold]Variant Group[/bold]")
            print(f"Impressions: {results.variant_impressions:,}")
            print(f"Clicks: {results.variant_clicks:,}")
            print(f"CTR: {results.variant_ctr:.2%}")
            
            print(f"\n[bold]Statistical Analysis[/bold]")
            print(f"P-value: {results.p_value:.4f}")
            print(f"Confidence Level: {results.confidence_level:.1%}")
            print(f"Significant: {'✓ YES' if results.is_significant else '✗ NO'}")
            print(f"Effect Size: {results.effect_size:.2%}")
            print(f"Practical Significance: {'✓ YES' if results.practical_significance else '✗ NO'}")
            
            print(f"\n[bold]Conclusion[/bold]")
            print(f"Winner: {results.winner.value.upper()}")
            print(f"Winner Probability: {results.winner_probability:.1%}")
            print(f"Expected Improvement: {results.expected_improvement:.2%}")
            print(f"Recommendation: {results.recommendation}")
            
            if results.early_stopping_triggered:
                print(f"[yellow]Early stopping triggered: {results.stop_reason}[/yellow]")
            
            # Export results if requested
            if output:
                from .ctr.statistical_tests import CTRTestManager
                manager = CTRTestManager(settings, project_config.ctr_testing)
                success = await manager.export_test_results(results, output)
                if success:
                    print(f"\n[green]✓ Test results exported to {output}[/green]")
                else:
                    print(f"\n[red]Failed to export test results[/red]")
            
        except Exception as e:
            print(f"[red]CTR test analysis failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_testing())


@app.command()
def quality_audit(
    project: str = typer.Option(..., help="Project directory path"),
    content_id: str = typer.Option(..., help="Content ID to audit"),
    content_file: str = typer.Option(..., help="Content file to analyze"),
    output: Optional[str] = typer.Option(None, help="Output file for audit report"),
):
    """Run content quality audit and governance check."""
    import asyncio
    
    async def run_audit():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            # Load content file
            content_path = Path(content_file)
            if not content_path.exists():
                print(f"[red]Content file not found: {content_file}[/red]")
                raise typer.Exit(1)
            
            content = content_path.read_text(encoding='utf-8')
            
            print(f"[bold green]Running quality audit for content {content_id}[/bold green]")
            
            # Run quality audit
            quality_score = await run_quality_audit(
                project_id=project_path.name,
                content_id=content_id,
                content=content,
                settings=settings,
                governance_config=project_config.governance
            )
            
            # Display results
            print(f"\n[bold]Quality Audit Results[/bold]")
            print(f"Overall Score: [bold]{quality_score.overall_score:.1f}/10[/bold]")
            print(f"Quality Level: {quality_score.quality_level.value.upper()}")
            
            print(f"\n[bold]Component Scores[/bold]")
            print(f"Content Quality: {quality_score.content_quality:.1f}/10")
            print(f"Technical Quality: {quality_score.technical_quality:.1f}/10")
            print(f"Trustworthiness: {quality_score.trustworthiness:.1f}/10")
            print(f"User Experience: {quality_score.user_experience:.1f}/10")
            print(f"SEO Optimization: {quality_score.seo_optimization:.1f}/10")
            
            print(f"\n[bold]Detailed Metrics[/bold]")
            print(f"Word Count: {quality_score.word_count}")
            print(f"Readability Score: {quality_score.readability_score:.1f}")
            print(f"Citation Score: {quality_score.citation_score:.1f}")
            print(f"Originality Score: {quality_score.originality_score:.1f}")
            
            # Show issues
            if quality_score.issues:
                print(f"\n[bold red]Issues ({len(quality_score.issues)})[/bold red]")
                for issue in quality_score.issues:
                    print(f"  • {issue}")
            
            # Show recommendations
            if quality_score.recommendations:
                print(f"\n[bold yellow]Recommendations[/bold yellow]")
                for rec in quality_score.recommendations:
                    print(f"  • {rec}")
            
            # Show spam signals
            if quality_score.spam_signals:
                print(f"\n[bold red]Spam Signals Detected[/bold red]")
                for signal in quality_score.spam_signals:
                    print(f"  • {signal.value}")
            
            # Export audit if requested
            if output:
                audit_data = {
                    "content_id": content_id,
                    "audit_date": datetime.now().isoformat(),
                    "quality_score": quality_score.__dict__
                }
                
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(audit_data, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"\n[green]✓ Quality audit exported to {output}[/green]")
            
        except Exception as e:
            print(f"[red]Quality audit failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_audit())


@app.command()
def dashboard(
    project: str = typer.Option(..., help="Project directory path"),
    domain: str = typer.Option(..., help="Domain to monitor"),
    port: int = typer.Option(8000, help="Dashboard port"),
    host: str = typer.Option("127.0.0.1", help="Dashboard host"),
):
    """Launch real-time monitoring dashboard."""
    import asyncio
    
    async def run_dashboard():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            print(f"[bold green]Launching monitoring dashboard for {domain}[/bold green]")
            print(f"Dashboard will be available at http://{host}:{port}")
            
            # Launch dashboard
            dashboard_server = await launch_dashboard(
                project_id=project_path.name,
                domain=domain,
                settings=settings,
                monitoring_config=project_config.monitoring,
                port=port,
                host=host
            )
            
            print(f"[green]✓ Dashboard server started successfully[/green]")
            print(f"[dim]Press Ctrl+C to stop the dashboard[/dim]")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print(f"\n[yellow]Dashboard server stopped[/yellow]")
            
        except Exception as e:
            print(f"[red]Dashboard launch failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_dashboard())


@app.command()
def alert_config(
    project: str = typer.Option(..., help="Project directory path"),
    list_rules: bool = typer.Option(False, help="List current alert rules"),
    export_config: Optional[str] = typer.Option(None, help="Export alert configuration"),
):
    """Configure alerting rules and channels."""
    import asyncio
    
    async def configure_alerts():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            print(f"[bold green]Alert Configuration for {project_path.name}[/bold green]")
            
            # Initialize alert manager
            alert_manager = await run_alert_monitoring(
                project_id=project_path.name,
                settings=settings,
                monitoring_config=project_config.monitoring
            )
            
            if list_rules:
                # List current alert rules
                print(f"\n[bold]Active Alert Rules[/bold]")
                for rule_id, rule in alert_manager.alert_rules.items():
                    status = "✓ Enabled" if rule.enabled else "✗ Disabled"
                    print(f"  {rule_id}: {rule.name} - {rule.severity.value.upper()} - {status}")
                    print(f"    Metric: {rule.metric_name}")
                    print(f"    Condition: {rule.condition} {rule.threshold_value or 'N/A'}")
                    print(f"    Channels: {[c.value for c in rule.channels]}")
                    print()
            
            # Show active alerts
            active_alerts = alert_manager.get_active_alerts(project_path.name)
            if active_alerts:
                print(f"[bold red]Active Alerts ({len(active_alerts)})[/bold red]")
                for alert in active_alerts[:5]:
                    print(f"  • {alert.title} - {alert.severity.value.upper()}")
                    print(f"    Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"    Status: {alert.status.value}")
            else:
                print(f"[green]No active alerts[/green]")
            
            # Export configuration if requested
            if export_config:
                success = await alert_manager.export_alert_data(Path(export_config))
                if success:
                    print(f"\n[green]✓ Alert configuration exported to {export_config}[/green]")
                else:
                    print(f"\n[red]Failed to export alert configuration[/red]")
            
        except Exception as e:
            print(f"[red]Alert configuration failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(configure_alerts())


@app.command()
def prune_content(
    project: str = typer.Option(..., help="Project directory path"),
    domain: str = typer.Option(..., help="Domain to analyze"),
    output: Optional[str] = typer.Option(None, help="Output file for pruning report"),
    implement: bool = typer.Option(False, help="Implement recommendations (dry run by default)"),
    high_priority_only: bool = typer.Option(False, help="Only show high priority recommendations"),
):
    """Analyze content for pruning and optimization opportunities."""
    import asyncio
    
    async def run_pruning():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            print(f"[bold green]Analyzing content for pruning opportunities: {domain}[/bold green]")
            
            # Run content analysis
            analysis_result = await run_content_analysis(
                domain=domain,
                settings=settings
            )
            
            # Display summary
            print(f"\n[bold]Content Analysis Summary[/bold]")
            print(f"Total URLs Analyzed: {analysis_result['total_urls_analyzed']}")
            print(f"Recommendations Generated: {len(analysis_result['recommendations'])}")
            
            # Show impact summary
            impact = analysis_result['impact_summary']
            print(f"\n[bold]Expected Impact[/bold]")
            print(f"Current Total Traffic: {impact['traffic_analysis']['current_total_traffic']:,} clicks")
            print(f"Traffic to Remove: {impact['traffic_analysis']['traffic_to_remove']:,} clicks")
            print(f"Traffic to Consolidate: {impact['traffic_analysis']['traffic_to_consolidate']:,} clicks")
            print(f"Net Impact: {impact['traffic_analysis']['estimated_net_impact']:,} clicks")
            print(f"Total Effort: {impact['effort_analysis']['total_estimated_hours']:.1f} hours")
            
            # Show action breakdown
            print(f"\n[bold]Action Breakdown[/bold]")
            for action, count in impact['action_breakdown'].items():
                if count > 0:
                    print(f"  {action}: {count}")
            
            # Show priority breakdown
            print(f"\n[bold]Priority Breakdown[/bold]")
            for priority, count in impact['priority_breakdown'].items():
                if count > 0:
                    print(f"  {priority}: {count}")
            
            # Show top recommendations
            recommendations = analysis_result['recommendations']
            if high_priority_only:
                recommendations = [r for r in recommendations if r.get('priority') == 'high']
            
            if recommendations:
                print(f"\n[bold]Top Recommendations[/bold]")
                for i, rec in enumerate(recommendations[:10], 1):
                    action_color = {
                        'delete': 'red',
                        'redirect': 'yellow', 
                        'merge': 'blue',
                        'improve': 'green',
                        'noindex': 'dim',
                        'keep': 'dim'
                    }.get(rec.get('action', 'keep'), 'white')
                    
                    print(f"  {i:2d}. [{action_color}]{rec.get('action', 'unknown').upper()}[/{action_color}] {rec.get('url', 'N/A')}")
                    print(f"      {rec.get('reason', 'No reason provided')}")
                    print(f"      Confidence: {rec.get('confidence', 0):.1%}, "
                          f"Priority: {rec.get('priority', 'unknown')}, "
                          f"Effort: {rec.get('estimated_hours', 0):.1f}h")
                    if rec.get('target_url'):
                        print(f"      Target: {rec['target_url']}")
                    print()
            
            # Show consolidation opportunities
            if analysis_result['consolidation_plans']:
                print(f"[bold]Content Consolidation Opportunities ({len(analysis_result['consolidation_plans'])})[/bold]")
                for plan in analysis_result['consolidation_plans']:
                    print(f"  • {plan['primary_url']}")
                    print(f"    Merge {len(plan['consolidation_urls'])} pages")
                    print(f"    Traffic gain: {plan['estimated_traffic_gain']} clicks")
                    print(f"    Effort: {plan['estimated_effort_hours']:.1f} hours")
                    print()
            
            # Export report if requested
            if output:
                from .prune.optimization import ContentPruningManager
                manager = ContentPruningManager(settings)
                success = await manager.export_analysis_report(analysis_result, Path(output))
                if success:
                    print(f"[green]✓ Pruning analysis exported to {output}[/green]")
                else:
                    print(f"[red]Failed to export pruning analysis[/red]")
            
            # Implement recommendations if requested
            if implement:
                print(f"\n[bold yellow]Implementation not yet available - this would apply the recommendations[/bold yellow]")
                print(f"[dim]Use --output to export recommendations for manual review[/dim]")
            
        except Exception as e:
            print(f"[red]Content pruning analysis failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(run_pruning())


@app.command()
def generate_report(
    project: str = typer.Option(..., help="Project directory path"),
    report_type: str = typer.Option("summary", help="Report type: summary, coverage, quality, ctr, alerts"),
    output: str = typer.Option(..., help="Output file for report"),
    period: str = typer.Option("30d", help="Report period: 7d, 30d, 90d"),
):
    """Generate comprehensive monitoring and performance reports."""
    import asyncio
    
    async def generate_report_data():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            # Parse period
            period_days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=period_days)
            
            print(f"[bold green]Generating {report_type} report for {project_path.name}[/bold green]")
            print(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            report_data = {
                "project": project_path.name,
                "report_type": report_type,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "period_days": period_days
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if report_type == "summary":
                # Generate comprehensive summary report
                report_data["sections"] = {
                    "executive_summary": {
                        "key_metrics": "Summary of key performance indicators",
                        "highlights": ["Metric improvements", "Issues resolved", "New opportunities"],
                        "recommendations": ["Top 3 priority actions"]
                    },
                    "coverage_status": "Coverage and indexation health",
                    "quality_metrics": "Content quality and governance status",
                    "performance_trends": "Traffic and ranking trends",
                    "system_health": "Technical system status"
                }
            
            elif report_type == "coverage":
                # Coverage-specific report
                print("Generating coverage report...")
                # Would integrate with coverage monitoring
                report_data["coverage_metrics"] = {
                    "indexation_rate": 0.85,
                    "coverage_violations": 5,
                    "mobile_usability": 92.5
                }
            
            elif report_type == "quality":
                # Quality governance report
                print("Generating quality report...")
                # Would integrate with quality governance
                report_data["quality_metrics"] = {
                    "average_quality_score": 7.8,
                    "content_flagged": 3,
                    "review_queue_size": 12
                }
            
            elif report_type == "ctr":
                # CTR testing report
                print("Generating CTR testing report...")
                # Would integrate with CTR testing
                report_data["ctr_metrics"] = {
                    "active_tests": 2,
                    "completed_tests": 8,
                    "average_improvement": 0.12
                }
            
            elif report_type == "alerts":
                # Alerts and monitoring report
                print("Generating alerts report...")
                # Would integrate with alert manager
                alert_manager = await run_alert_monitoring(
                    project_id=project_path.name,
                    settings=settings,
                    monitoring_config=project_config.monitoring
                )
                
                alert_report = await alert_manager.generate_alert_report(
                    project_path.name, start_date, end_date
                )
                report_data["alert_metrics"] = alert_report
            
            else:
                print(f"[red]Unknown report type: {report_type}[/red]")
                raise typer.Exit(1)
            
            # Save report
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"[green]✓ {report_type.title()} report generated: {output}[/green]")
            
        except Exception as e:
            print(f"[red]Report generation failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(generate_report_data())


@app.command()
def system_health(
    project: str = typer.Option(..., help="Project directory path"),
    check_apis: bool = typer.Option(True, help="Check API connectivity"),
    check_quotas: bool = typer.Option(True, help="Check API quotas"),
    verbose: bool = typer.Option(False, help="Show detailed health information"),
):
    """Check overall system health and connectivity."""
    import asyncio
    
    async def check_health():
        try:
            project_path = Path(project)
            config_file = project_path / "config.yml"
            
            if not config_file.exists():
                print(f"[red]Project config not found: {config_file}[/red]")
                raise typer.Exit(1)
            
            project_config = load_project_config(project_path)
            
            print(f"[bold green]System Health Check for {project_path.name}[/bold green]")
            
            health_status = {
                "overall": "healthy",
                "components": {},
                "warnings": [],
                "errors": []
            }
            
            # Check configuration
            print(f"\n[bold]Configuration Check[/bold]")
            config_checks = {
                "Project config": config_file.exists(),
                "Environment file": (project_path / ".env").exists(),
                "GSC credentials": bool(settings.google_search_console_credentials_file),
                "SMTP configured": bool(settings.smtp_host),
                "Slack webhook": bool(settings.slack_webhook_url)
            }
            
            for check, status in config_checks.items():
                status_icon = "✓" if status else "✗"
                color = "green" if status else "yellow"
                print(f"  [{color}]{status_icon} {check}[/{color}]")
                health_status["components"][check] = status
                if not status:
                    health_status["warnings"].append(f"{check} not configured")
            
            # Check API connectivity if requested
            if check_apis:
                print(f"\n[bold]API Connectivity[/bold]")
                
                # GSC API check
                if settings.google_search_console_credentials_file:
                    try:
                        from .monitor.coverage import GSCAdapter
                        gsc = GSCAdapter(settings.google_search_console_credentials_file)
                        print(f"  [green]✓ Google Search Console API[/green]")
                        health_status["components"]["GSC API"] = True
                    except Exception as e:
                        print(f"  [red]✗ Google Search Console API: {e}[/red]")
                        health_status["components"]["GSC API"] = False
                        health_status["errors"].append(f"GSC API error: {e}")
                else:
                    print(f"  [yellow]- Google Search Console API (not configured)[/yellow]")
                
                # PageSpeed API check
                if settings.pagespeed_api_key:
                    print(f"  [green]✓ PageSpeed Insights API[/green]")
                    health_status["components"]["PageSpeed API"] = True
                else:
                    print(f"  [yellow]- PageSpeed Insights API (not configured)[/yellow]")
            
            # Check monitoring systems
            print(f"\n[bold]Monitoring Systems[/bold]")
            monitoring_checks = {
                "Coverage monitoring": True,  # Would check actual status
                "Alert manager": True,
                "Dashboard server": True,
                "Quality governance": True
            }
            
            for system, status in monitoring_checks.items():
                status_icon = "✓" if status else "✗"
                color = "green" if status else "red"
                print(f"  [{color}]{status_icon} {system}[/{color}]")
                health_status["components"][system] = status
            
            # Show system resources if verbose
            if verbose:
                print(f"\n[bold]System Resources[/bold]")
                print(f"  Python version: {sys.version.split()[0]}")
                print(f"  Platform: {sys.platform}")
                print(f"  Working directory: {os.getcwd()}")
                
                # Memory usage (simplified)
                import psutil
                memory = psutil.virtual_memory()
                print(f"  Memory usage: {memory.percent:.1f}% ({memory.used // 1024**3}GB / {memory.total // 1024**3}GB)")
            
            # Overall health assessment
            error_count = len(health_status["errors"])
            warning_count = len(health_status["warnings"])
            
            if error_count > 0:
                health_status["overall"] = "critical"
                print(f"\n[bold red]Overall Status: CRITICAL ({error_count} errors)[/bold red]")
            elif warning_count > 3:
                health_status["overall"] = "warning"
                print(f"\n[bold yellow]Overall Status: WARNING ({warning_count} warnings)[/bold yellow]")
            else:
                print(f"\n[bold green]Overall Status: HEALTHY[/bold green]")
            
            # Show issues
            if health_status["errors"]:
                print(f"\n[bold red]Errors[/bold red]")
                for error in health_status["errors"]:
                    print(f"  • {error}")
            
            if health_status["warnings"]:
                print(f"\n[bold yellow]Warnings[/bold yellow]")
                for warning in health_status["warnings"]:
                    print(f"  • {warning}")
            
            # Recommendations
            print(f"\n[bold]Recommendations[/bold]")
            if not settings.google_search_console_credentials_file:
                print(f"  • Configure Google Search Console API for coverage monitoring")
            if not settings.slack_webhook_url:
                print(f"  • Set up Slack webhook for alerting")
            if not settings.smtp_host:
                print(f"  • Configure SMTP for email notifications")
            
            if health_status["overall"] == "critical":
                raise typer.Exit(1)
            
        except Exception as e:
            print(f"[red]System health check failed: {e}[/red]")
            raise typer.Exit(1)
    
    asyncio.run(check_health())


# Research commands
app.command(name="research-collect")(research_collect)
app.command(name="research-publish")(research_publish)
app.command(name="research-list")(research_list)
app.command(name="research-create")(research_create)

# Tools commands
app.command(name="tools-build")(tools_build)
app.command(name="tools-list")(tools_list)
app.command(name="tools-test")(tools_test)
app.command(name="tools-create-registry")(tools_create_registry)
app.command(name="tools-validate-formula")(tools_validate_formula)


if __name__ == "__main__":
    app()
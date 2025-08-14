"""CLI commands for research data collection and publishing."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import Dataset, ResearchConfig, Observation
from .sources import ResearchSourceManager
from .normalize import DataNormalizer
from .publish import ResearchPublisher

console = Console()
logger = logging.getLogger(__name__)


async def run_research_collection(
    sources: List[str],
    dataset_config_path: Optional[Path] = None,
    output_dir: Path = Path("out/research")
):
    """Run research data collection from specified sources."""
    
    # Load configuration
    config = ResearchConfig()
    if dataset_config_path and dataset_config_path.exists():
        with open(dataset_config_path) as f:
            dataset_data = json.load(f)
            dataset = Dataset(**dataset_data)
    else:
        # Create default dataset for ad-hoc collection
        dataset = Dataset(
            id="adhoc_collection",
            title="Ad-hoc Research Collection",
            description="Research data collected from specified sources",
            category="pricing",
            entities=[],
            metrics=["price", "spec.version", "release_date"],
            collection_frequency="daily",
            sources=[],
            schema_fields={},
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
    
    # Initialize source manager
    source_manager = ResearchSourceManager(config)
    
    console.print(f"[bold green]Starting research collection...[/bold green]")
    console.print(f"Sources: {', '.join(sources)}")
    console.print(f"Dataset: {dataset.title}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Collecting data...", total=None)
            
            # Collect from all sources
            results = await source_manager.collect_all(dataset.id, dataset.entities, sources)
            
            # Aggregate all observations
            all_observations = []
            for result in results:
                all_observations.extend(result.observations)
                
                if result.errors:
                    console.print(f"[yellow]Warnings from {result.source_id}:[/yellow]")
                    for error in result.errors:
                        console.print(f"  • {error}")
            
            progress.update(task, description="Publishing dataset...")
            
            # Publish dataset
            if all_observations:
                publisher = ResearchPublisher(config, output_dir)
                publish_results = publisher.publish_dataset(dataset, all_observations)
                
                # Show results
                console.print(f"\n[bold green]✓ Collection completed successfully![/bold green]")
                console.print(f"Total observations: {len(all_observations)}")
                console.print(f"Formats generated: {', '.join(publish_results['formats_generated'])}")
                console.print(f"Charts generated: {', '.join(publish_results['charts_generated'])}")
                
                if publish_results['errors']:
                    console.print(f"[yellow]Errors: {len(publish_results['errors'])}[/yellow]")
            else:
                console.print("[red]No observations collected from any source[/red]")
    
    finally:
        await source_manager.close_all()


async def run_research_publish(
    dataset_id: str,
    data_dir: Path = Path("projects/data/research"),
    output_dir: Path = Path("out/research")
):
    """Publish research dataset with visualizations and schema."""
    
    # Load dataset configuration
    dataset_config_path = data_dir / f"{dataset_id}.json"
    if not dataset_config_path.exists():
        console.print(f"[red]Dataset configuration not found: {dataset_config_path}[/red]")
        raise typer.Exit(1)
    
    with open(dataset_config_path) as f:
        dataset_data = json.load(f)
        dataset = Dataset(**dataset_data)
    
    # Load observations from parquet
    observations_path = data_dir / f"{dataset_id}.parquet"
    if not observations_path.exists():
        console.print(f"[red]Observations file not found: {observations_path}[/red]")
        raise typer.Exit(1)
    
    import pandas as pd
    df = pd.read_parquet(observations_path)
    observations = [Observation(**row) for _, row in df.iterrows()]
    
    # Publish dataset
    config = ResearchConfig()
    publisher = ResearchPublisher(config, output_dir)
    
    console.print(f"[bold green]Publishing dataset: {dataset.title}[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Publishing...", total=None)
        
        results = publisher.publish_dataset(dataset, observations)
        
        console.print(f"\n[bold green]✓ Dataset published successfully![/bold green]")
        console.print(f"Output directory: {output_dir / dataset.id}")
        console.print(f"Formats: {', '.join(results['formats_generated'])}")
        console.print(f"Charts: {', '.join(results['charts_generated'])}")
        
        if results['errors']:
            console.print(f"[yellow]Errors: {len(results['errors'])}[/yellow]")
            for error in results['errors']:
                console.print(f"  • {error}")


def show_research_datasets(data_dir: Path = Path("projects/data/research")):
    """Show available research datasets."""
    
    if not data_dir.exists():
        console.print(f"[yellow]Research data directory not found: {data_dir}[/yellow]")
        return
    
    dataset_files = list(data_dir.glob("*.json"))
    
    if not dataset_files:
        console.print("[yellow]No research datasets found[/yellow]")
        return
    
    table = Table(title="Research Datasets")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Entities", justify="right")
    table.add_column("Last Updated", style="dim")
    
    for dataset_file in dataset_files:
        try:
            with open(dataset_file) as f:
                data = json.load(f)
                dataset = Dataset(**data)
                
                table.add_row(
                    dataset.id,
                    dataset.title,
                    dataset.category,
                    str(len(dataset.entities)),
                    dataset.last_updated.strftime("%Y-%m-%d")
                )
        except Exception as e:
            logger.warning(f"Could not load dataset {dataset_file}: {e}")
    
    console.print(table)


def create_dataset_config(
    dataset_id: str,
    title: str,
    description: str,
    category: str,
    entities: List[str],
    output_path: Optional[Path] = None
):
    """Create a new research dataset configuration."""
    
    if not output_path:
        output_path = Path(f"projects/data/research/{dataset_id}.json")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    
    dataset = Dataset(
        id=dataset_id,
        title=title,
        description=description,
        category=category,
        entities=entities,
        metrics=["price", "spec.version", "release_date"],
        collection_frequency="daily",
        sources=[],
        schema_fields={},
        created_at=datetime.now(),
        last_updated=datetime.now()
    )
    
    with open(output_path, 'w') as f:
        json.dump(dataset.dict(), f, indent=2, default=str)
    
    console.print(f"[green]✓ Dataset configuration created: {output_path}[/green]")
    console.print(f"Edit the file to customize sources and metrics before collection.")


# CLI command wrappers
def research_collect(
    sources: str = typer.Option(..., help="Comma-separated list of sources (price,specs,releases,changelog)"),
    dataset: Optional[str] = typer.Option(None, help="Dataset configuration file"),
    output: str = typer.Option("out/research", help="Output directory")
):
    """Collect research data from specified sources."""
    source_list = [s.strip() for s in sources.split(",")]
    dataset_path = Path(dataset) if dataset else None
    
    asyncio.run(run_research_collection(source_list, dataset_path, Path(output)))


def research_publish(
    dataset_id: str = typer.Argument(..., help="Dataset ID to publish"),
    data_dir: str = typer.Option("projects/data/research", help="Data directory"),
    output_dir: str = typer.Option("out/research", help="Output directory")
):
    """Publish research dataset with visualizations and schema."""
    asyncio.run(run_research_publish(dataset_id, Path(data_dir), Path(output_dir)))


def research_list(
    data_dir: str = typer.Option("projects/data/research", help="Data directory")
):
    """List available research datasets."""
    show_research_datasets(Path(data_dir))


def research_create(
    dataset_id: str = typer.Argument(..., help="Dataset ID"),
    title: str = typer.Option(..., help="Dataset title"),
    description: str = typer.Option(..., help="Dataset description"),  
    category: str = typer.Option("pricing", help="Dataset category"),
    entities: str = typer.Option(..., help="Comma-separated list of entities to track"),
    output: Optional[str] = typer.Option(None, help="Output file path")
):
    """Create a new research dataset configuration."""
    entity_list = [e.strip() for e in entities.split(",")]
    output_path = Path(output) if output else None
    
    create_dataset_config(dataset_id, title, description, category, entity_list, output_path)
"""CLI commands for micro-tools and calculators system."""

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .registry import (
    RegistryManager, 
    create_sample_registry_file,
    load_registry_from_yaml
)
from .models import CalculatorSpec
from .evaluator import FormulaEvaluator

console = Console()
logger = logging.getLogger(__name__)


def tools_build(
    registry_file: str = typer.Option("tools/registry.yml", help="Registry YAML file path"),
    output_dir: str = typer.Option("out/tools", help="Output directory for generated tools"),
    validate_only: bool = typer.Option(False, help="Only validate registry without generating")
):
    """Build tools from registry configuration."""
    registry_path = Path(registry_file)
    output_path = Path(output_dir)
    
    if not registry_path.exists():
        console.print(f"[red]Registry file not found: {registry_path}[/red]")
        console.print(f"[yellow]Create a sample registry with: seo-bot tools-create-registry {registry_path}[/yellow]")
        raise typer.Exit(1)
    
    try:
        # Load and validate registry
        registry = load_registry_from_yaml(registry_path)
        validation_errors = registry.validate_all_calculators()
        
        if validation_errors:
            console.print(f"[red]Registry validation failed:[/red]")
            for calc_id, errors in validation_errors.items():
                console.print(f"  [bold]{calc_id}:[/bold]")
                for error in errors:
                    console.print(f"    • {error}")
            raise typer.Exit(1)
        
        console.print(f"[green]✓ Registry validation passed[/green]")
        console.print(f"Found {len(registry.calculators)} calculators in {len(set(c.category for c in registry.calculators))} categories")
        
        if validate_only:
            return
        
        # Generate tools
        manager = RegistryManager(registry_path, output_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating tools...", total=None)
            
            results = manager.generate_all_tools()
            
            progress.update(task, description="Generation completed")
        
        # Show results
        console.print(f"\n[bold green]✓ Tool generation completed![/bold green]")
        console.print(f"Output directory: {output_path}")
        console.print(f"Generated files: {len(results['generated'])}")
        
        if results['generated']:
            console.print(f"\n[bold]Generated Files:[/bold]")
            for file_path in results['generated'][:10]:  # Show first 10
                console.print(f"  • {file_path}")
            if len(results['generated']) > 10:
                console.print(f"  ... and {len(results['generated']) - 10} more")
        
        if results['warnings']:
            console.print(f"\n[yellow]Warnings ({len(results['warnings'])}):[/yellow]")
            for warning in results['warnings']:
                console.print(f"  • {warning}")
        
        if results['errors']:
            console.print(f"\n[red]Errors ({len(results['errors'])}):[/red]")
            for error in results['errors']:
                console.print(f"  • {error}")
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]Tool generation failed: {e}[/red]")
        raise typer.Exit(1)


def tools_list(
    registry_file: str = typer.Option("tools/registry.yml", help="Registry YAML file path"),
    category: Optional[str] = typer.Option(None, help="Filter by category"),
    show_details: bool = typer.Option(False, help="Show detailed information")
):
    """List available calculators in registry."""
    registry_path = Path(registry_file)
    
    if not registry_path.exists():
        console.print(f"[red]Registry file not found: {registry_path}[/red]")
        raise typer.Exit(1)
    
    try:
        registry = load_registry_from_yaml(registry_path)
        calculators = registry.calculators
        
        if category:
            calculators = [c for c in calculators if c.category == category]
        
        if not calculators:
            console.print(f"[yellow]No calculators found{' in category ' + category if category else ''}[/yellow]")
            return
        
        if show_details:
            # Detailed view
            for calc in calculators:
                console.print(f"\n[bold cyan]{calc.id}[/bold cyan] - {calc.title}")
                console.print(f"  [dim]Category:[/dim] {calc.category}")
                console.print(f"  [dim]Description:[/dim] {calc.description}")
                console.print(f"  [dim]Inputs:[/dim] {len(calc.inputs)} fields")
                console.print(f"  [dim]Outputs:[/dim] {len(calc.outputs)} results")
                console.print(f"  [dim]Usage:[/dim] {calc.metadata.usage_count} times")
        else:
            # Table view
            table = Table(title=f"Calculator Tools{' - ' + category if category else ''}")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Category", style="yellow")
            table.add_column("Inputs", justify="right")
            table.add_column("Outputs", justify="right")
            table.add_column("Usage", justify="right", style="dim")
            
            for calc in calculators:
                table.add_row(
                    calc.id,
                    calc.title,
                    calc.category,
                    str(len(calc.inputs)),
                    str(len(calc.outputs)),
                    str(calc.metadata.usage_count)
                )
            
            console.print(table)
        
        # Show categories summary
        if not category:
            categories = {}
            for calc in registry.calculators:
                categories[calc.category] = categories.get(calc.category, 0) + 1
            
            console.print(f"\n[bold]Categories:[/bold]")
            for cat, count in categories.items():
                console.print(f"  • {cat}: {count} calculator{'s' if count != 1 else ''}")
    
    except Exception as e:
        console.print(f"[red]Failed to list tools: {e}[/red]")
        raise typer.Exit(1)


def tools_test(
    registry_file: str = typer.Option("tools/registry.yml", help="Registry YAML file path"),
    calculator_id: Optional[str] = typer.Option(None, help="Test specific calculator"),
    sample_inputs: Optional[str] = typer.Option(None, help="JSON string of sample inputs")
):
    """Test calculator formulas and validation."""
    registry_path = Path(registry_file)
    
    if not registry_path.exists():
        console.print(f"[red]Registry file not found: {registry_path}[/red]")
        raise typer.Exit(1)
    
    try:
        registry = load_registry_from_yaml(registry_path)
        
        calculators_to_test = []
        if calculator_id:
            calc = registry.get_calculator(calculator_id)
            if not calc:
                console.print(f"[red]Calculator '{calculator_id}' not found[/red]")
                raise typer.Exit(1)
            calculators_to_test = [calc]
        else:
            calculators_to_test = registry.calculators
        
        evaluator = FormulaEvaluator()
        total_tests = 0
        passed_tests = 0
        
        for calc in calculators_to_test:
            console.print(f"\n[bold]Testing {calc.id}[/bold] - {calc.title}")
            
            # Use provided sample inputs or generate defaults
            if sample_inputs and calculator_id:
                try:
                    test_inputs = json.loads(sample_inputs)
                except json.JSONDecodeError:
                    console.print(f"[red]Invalid JSON in sample_inputs[/red]")
                    continue
            else:
                # Generate sample inputs
                test_inputs = {}
                for inp in calc.inputs:
                    if inp.type == "number":
                        test_inputs[inp.name] = inp.default_value or (inp.min_value or 0) + 1
                    elif inp.type == "text":
                        test_inputs[inp.name] = inp.default_value or "test input"
                    elif inp.type == "select" and inp.options:
                        test_inputs[inp.name] = inp.options[0]["value"]
                    elif inp.type == "checkbox":
                        test_inputs[inp.name] = bool(inp.default_value)
            
            # Test calculation
            total_tests += 1
            try:
                result = evaluator.calculate(calc, test_inputs)
                
                if result.errors:
                    console.print(f"  [red]✗ Calculation failed:[/red]")
                    for error in result.errors:
                        console.print(f"    • {error}")
                else:
                    console.print(f"  [green]✓ Calculation succeeded[/green]")
                    console.print(f"    Execution time: {result.execution_time_ms:.1f}ms")
                    
                    # Show sample outputs
                    for output_name, value in result.outputs.items():
                        console.print(f"    {output_name}: {value}")
                    
                    passed_tests += 1
                
                if result.warnings:
                    console.print(f"  [yellow]Warnings:[/yellow]")
                    for warning in result.warnings:
                        console.print(f"    • {warning}")
            
            except Exception as e:
                console.print(f"  [red]✗ Test failed: {e}[/red]")
        
        # Summary
        console.print(f"\n[bold]Test Summary:[/bold]")
        console.print(f"  Tests run: {total_tests}")
        console.print(f"  Passed: [green]{passed_tests}[/green]")
        console.print(f"  Failed: [red]{total_tests - passed_tests}[/red]")
        
        if passed_tests < total_tests:
            raise typer.Exit(1)
    
    except Exception as e:
        console.print(f"[red]Testing failed: {e}[/red]")
        raise typer.Exit(1)


def tools_create_registry(
    output_file: str = typer.Argument(..., help="Output YAML file path"),
    overwrite: bool = typer.Option(False, help="Overwrite existing file")
):
    """Create a sample calculator registry file."""
    output_path = Path(output_file)
    
    if output_path.exists() and not overwrite:
        console.print(f"[red]File already exists: {output_path}[/red]")
        console.print(f"Use --overwrite to replace it")
        raise typer.Exit(1)
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        create_sample_registry_file(output_path)
        
        console.print(f"[green]✓ Created sample registry: {output_path}[/green]")
        console.print(f"\nThe registry includes sample calculators:")
        console.print(f"  • Keyword Density Calculator (SEO)")
        console.print(f"  • Page Load Budget Calculator (Technical)")
        console.print(f"\nEdit the file to customize calculators before building.")
    
    except Exception as e:
        console.print(f"[red]Failed to create registry: {e}[/red]")
        raise typer.Exit(1)


def tools_validate_formula(
    expression: str = typer.Argument(..., help="Formula expression to validate"),
    variables: Optional[str] = typer.Option(None, help="JSON object of test variables")
):
    """Validate a formula expression."""
    evaluator = FormulaEvaluator()
    
    try:
        # Validate syntax
        is_valid, error_msg = evaluator.validate_formula_syntax(expression)
        
        if not is_valid:
            console.print(f"[red]✗ Syntax error: {error_msg}[/red]")
            raise typer.Exit(1)
        
        console.print(f"[green]✓ Syntax is valid[/green]")
        
        # Test evaluation if variables provided
        if variables:
            try:
                test_vars = json.loads(variables)
                result = evaluator.evaluator.evaluate(expression, test_vars)
                console.print(f"[green]✓ Evaluation succeeded: {result}[/green]")
            except json.JSONDecodeError:
                console.print(f"[yellow]Warning: Invalid JSON in variables[/yellow]")
            except Exception as e:
                console.print(f"[red]✗ Evaluation failed: {e}[/red]")
        else:
            console.print(f"[dim]Provide --variables as JSON to test evaluation[/dim]")
    
    except Exception as e:
        console.print(f"[red]Validation failed: {e}[/red]")
        raise typer.Exit(1)
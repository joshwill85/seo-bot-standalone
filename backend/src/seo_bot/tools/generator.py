"""Tool generation and code generation for calculators."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, Template

from .models import CalculatorSpec, ToolRegistry
from .evaluator import FormulaEvaluator


logger = logging.getLogger(__name__)


class ComponentRenderer:
    """Renders calculator components from specifications."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        
        self.template_dir = template_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )
        
        # Register custom filters
        self.jinja_env.filters['to_json'] = json.dumps
        self.jinja_env.filters['to_camel_case'] = self._to_camel_case
        self.jinja_env.filters['to_pascal_case'] = self._to_pascal_case
    
    def render_react_component(self, spec: CalculatorSpec) -> str:
        """Generate React/TypeScript component for calculator."""
        template = self.jinja_env.get_template('calculator.tsx.j2')
        
        return template.render(
            spec=spec,
            component_name=self._to_pascal_case(spec.id),
            has_charts=any(out.show_chart for out in spec.outputs),
            required_inputs=[inp for inp in spec.inputs if inp.required],
            optional_inputs=[inp for inp in spec.inputs if not inp.required]
        )
    
    def render_mdx_shortcode(self, spec: CalculatorSpec) -> str:
        """Generate MDX shortcode for embedding calculator."""
        template = self.jinja_env.get_template('calculator-shortcode.mdx.j2')
        
        return template.render(
            spec=spec,
            component_name=self._to_pascal_case(spec.id)
        )
    
    def render_html_embed(self, spec: CalculatorSpec) -> str:
        """Generate standalone HTML embed for calculator."""
        template = self.jinja_env.get_template('calculator-embed.html.j2')
        
        return template.render(
            spec=spec,
            calculator_json=json.dumps(spec.dict()),
            primary_outputs=spec.get_primary_outputs()
        )
    
    def render_json_schema(self, spec: CalculatorSpec) -> str:
        """Generate JSON-LD schema for calculator."""
        schema = {
            "@context": "https://schema.org/",
            "@type": "SoftwareApplication",
            "name": spec.title,
            "description": spec.description,
            "applicationCategory": spec.metadata.application_category,
            "operatingSystem": spec.metadata.operating_system,
            "softwareVersion": spec.metadata.software_version,
            "author": {
                "@type": "Organization",
                "name": spec.metadata.author or "SEO Bot"
            },
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD"
            },
            "featureList": [
                f"Calculate {output.label}" for output in spec.outputs
            ],
            "keywords": spec.metadata.keywords,
            "dateCreated": spec.created_at.isoformat(),
            "dateModified": spec.updated_at.isoformat()
        }
        
        return json.dumps(schema, indent=2)
    
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))


class ToolGenerator:
    """Main tool generation coordinator."""
    
    def __init__(self, output_dir: Path, template_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.renderer = ComponentRenderer(template_dir)
        self.evaluator = FormulaEvaluator()
    
    def generate_from_registry(self, registry_path: Path) -> Dict[str, List[str]]:
        """Generate all tools from registry file."""
        if registry_path.suffix.lower() == '.yaml' or registry_path.suffix.lower() == '.yml':
            with open(registry_path) as f:
                registry_data = yaml.safe_load(f)
        else:
            with open(registry_path) as f:
                registry_data = json.load(f)
        
        registry = ToolRegistry(**registry_data)
        
        results = {
            'generated': [],
            'errors': [],
            'warnings': []
        }
        
        # Validate all calculators first
        validation_errors = registry.validate_all_calculators()
        
        for calc in registry.calculators:
            if calc.id in validation_errors:
                results['errors'].extend([
                    f"{calc.id}: {error}" for error in validation_errors[calc.id]
                ])
                continue
            
            try:
                self._generate_calculator(calc, results)
            except Exception as e:
                results['errors'].append(f"{calc.id}: {e}")
        
        # Generate registry index
        self._generate_registry_index(registry)
        
        return results
    
    def generate_calculator(self, spec: CalculatorSpec) -> Dict[str, str]:
        """Generate all files for a single calculator."""
        results = {'generated': [], 'errors': []}
        return self._generate_calculator(spec, results)
    
    def _generate_calculator(self, spec: CalculatorSpec, results: Dict) -> Dict[str, str]:
        """Generate all files for a calculator."""
        calc_dir = self.output_dir / "components" / spec.id
        calc_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        try:
            # Generate React component
            react_code = self.renderer.render_react_component(spec)
            react_file = calc_dir / f"{self._to_pascal_case(spec.id)}.tsx"
            react_file.write_text(react_code)
            generated_files['react'] = str(react_file)
            results['generated'].append(f"React component: {react_file}")
            
            # Generate MDX shortcode
            mdx_code = self.renderer.render_mdx_shortcode(spec)
            mdx_file = calc_dir / f"{spec.id}.mdx"
            mdx_file.write_text(mdx_code)
            generated_files['mdx'] = str(mdx_file)
            results['generated'].append(f"MDX shortcode: {mdx_file}")
            
            # Generate HTML embed
            html_code = self.renderer.render_html_embed(spec)
            html_file = calc_dir / f"{spec.id}.html"
            html_file.write_text(html_code)
            generated_files['html'] = str(html_file)
            results['generated'].append(f"HTML embed: {html_file}")
            
            # Generate JSON-LD schema
            schema_code = self.renderer.render_json_schema(spec)
            schema_file = calc_dir / f"{spec.id}.jsonld"
            schema_file.write_text(schema_code)
            generated_files['schema'] = str(schema_file)
            results['generated'].append(f"JSON-LD schema: {schema_file}")
            
            # Generate calculator specification
            spec_file = calc_dir / f"{spec.id}.spec.json"
            spec_file.write_text(json.dumps(spec.dict(), indent=2, default=str))
            generated_files['spec'] = str(spec_file)
            results['generated'].append(f"Specification: {spec_file}")
            
            # Test formula evaluation
            self._test_calculator_formulas(spec, results)
            
        except Exception as e:
            error_msg = f"Failed to generate {spec.id}: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return generated_files
    
    def _generate_registry_index(self, registry: ToolRegistry):
        """Generate index files for the registry."""
        index_dir = self.output_dir / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate calculator index JSON
        index_data = {
            'version': registry.version,
            'generated_at': datetime.now().isoformat(),
            'calculators': [
                {
                    'id': calc.id,
                    'title': calc.title,
                    'description': calc.description,
                    'category': calc.category,
                    'url': f"/calculators/{calc.id}/",
                    'embed_url': f"/calculators/{calc.id}/{calc.id}.html",
                    'schema_url': f"/calculators/{calc.id}/{calc.id}.jsonld",
                    'usage_count': calc.metadata.usage_count,
                    'last_used': calc.metadata.last_used.isoformat() if calc.metadata.last_used else None
                }
                for calc in registry.calculators
            ],
            'categories': registry.categories,
            'featured': [
                calc.id for calc in registry.get_featured_calculators()
            ]
        }
        
        index_file = index_dir / "calculators.json"
        index_file.write_text(json.dumps(index_data, indent=2))
        
        # Generate sitemap
        self._generate_sitemap(registry, index_dir)
    
    def _generate_sitemap(self, registry: ToolRegistry, output_dir: Path):
        """Generate sitemap for calculators."""
        from datetime import datetime
        
        sitemap_entries = []
        
        for calc in registry.calculators:
            sitemap_entries.append({
                'url': f"/calculators/{calc.id}/",
                'lastmod': calc.updated_at.strftime('%Y-%m-%d'),
                'changefreq': 'monthly',
                'priority': '0.8'
            })
        
        # Generate XML sitemap
        sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
        
        for entry in sitemap_entries:
            sitemap_xml += f'''  <url>
    <loc>{entry['url']}</loc>
    <lastmod>{entry['lastmod']}</lastmod>
    <changefreq>{entry['changefreq']}</changefreq>
    <priority>{entry['priority']}</priority>
  </url>
'''
        
        sitemap_xml += '</urlset>'
        
        sitemap_file = output_dir / "calculators-sitemap.xml"
        sitemap_file.write_text(sitemap_xml)
    
    def _test_calculator_formulas(self, spec: CalculatorSpec, results: Dict):
        """Test calculator formulas with sample inputs."""
        try:
            # Generate sample inputs
            sample_inputs = {}
            for input_spec in spec.inputs:
                if input_spec.type == "number":
                    if input_spec.default_value is not None:
                        sample_inputs[input_spec.name] = input_spec.default_value
                    elif input_spec.min_value is not None:
                        sample_inputs[input_spec.name] = input_spec.min_value + 1
                    else:
                        sample_inputs[input_spec.name] = 100
                
                elif input_spec.type == "text":
                    sample_inputs[input_spec.name] = input_spec.default_value or "test"
                
                elif input_spec.type == "select" and input_spec.options:
                    sample_inputs[input_spec.name] = input_spec.options[0]["value"]
                
                elif input_spec.type == "checkbox":
                    sample_inputs[input_spec.name] = bool(input_spec.default_value)
            
            # Test calculation
            calc_result = self.evaluator.calculate(spec, sample_inputs)
            
            if calc_result.errors:
                results['errors'].extend([
                    f"{spec.id} formula test: {error}" for error in calc_result.errors
                ])
            
            if calc_result.warnings:
                results['warnings'].extend([
                    f"{spec.id} formula test: {warning}" for warning in calc_result.warnings
                ])
            
            # Check if execution time is reasonable
            if calc_result.execution_time_ms > spec.max_execution_time_ms:
                results['warnings'].append(
                    f"{spec.id}: Execution time ({calc_result.execution_time_ms:.1f}ms) "
                    f"exceeds limit ({spec.max_execution_time_ms:.1f}ms)"
                )
        
        except Exception as e:
            results['errors'].append(f"{spec.id} formula test failed: {e}")
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))


class RegistryBuilder:
    """Builds calculator registry from YAML specifications."""
    
    def __init__(self):
        self.evaluator = FormulaEvaluator()
    
    def build_from_yaml(self, yaml_path: Path) -> ToolRegistry:
        """Build registry from YAML file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        # Parse calculator specifications
        calculators = []
        for calc_data in data.get('calculators', []):
            try:
                spec = CalculatorSpec(**calc_data)
                calculators.append(spec)
            except Exception as e:
                logger.error(f"Failed to parse calculator {calc_data.get('id', 'unknown')}: {e}")
        
        registry = ToolRegistry(
            version=data.get('version', '1.0'),
            calculators=calculators,
            categories=data.get('categories', {}),
            default_theme=data.get('default_theme', 'modern'),
            analytics_enabled=data.get('analytics_enabled', True)
        )
        
        return registry
    
    def validate_registry(self, registry: ToolRegistry) -> Dict[str, List[str]]:
        """Validate entire registry."""
        return registry.validate_all_calculators()
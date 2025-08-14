"""Calculator registry management and YAML-based configuration."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .models import CalculatorSpec, ToolRegistry
from .generator import ToolGenerator


logger = logging.getLogger(__name__)


def create_sample_registry() -> Dict:
    """Create a sample calculator registry in YAML format."""
    return {
        'version': '1.0',
        'categories': {
            'seo': 'SEO & Marketing Tools',
            'business': 'Business Calculators',
            'finance': 'Financial Tools',
            'technical': 'Technical Utilities'
        },
        'calculators': [
            {
                'id': 'keyword_density',
                'title': 'Keyword Density Calculator',
                'description': 'Calculate keyword density and frequency for SEO optimization',
                'category': 'seo',
                'inputs': [
                    {
                        'name': 'content',
                        'type': 'text',
                        'label': 'Content Text',
                        'description': 'Paste your content to analyze',
                        'required': True,
                        'placeholder': 'Enter your content here...'
                    },
                    {
                        'name': 'target_keyword',
                        'type': 'text',
                        'label': 'Target Keyword',
                        'description': 'Primary keyword to analyze',
                        'required': True,
                        'placeholder': 'e.g., SEO optimization'
                    },
                    {
                        'name': 'max_density',
                        'type': 'number',
                        'label': 'Maximum Density (%)',
                        'description': 'Recommended maximum keyword density',
                        'required': False,
                        'default_value': 3.0,
                        'min_value': 0.5,
                        'max_value': 10.0,
                        'step': 0.1,
                        'unit': '%'
                    }
                ],
                'outputs': [
                    {
                        'name': 'keyword_density',
                        'label': 'Keyword Density',
                        'type': 'percentage',
                        'highlight': True,
                        'decimal_places': 1
                    },
                    {
                        'name': 'keyword_count',
                        'label': 'Keyword Count',
                        'type': 'number',
                        'decimal_places': 0
                    },
                    {
                        'name': 'total_words',
                        'label': 'Total Words',
                        'type': 'number',
                        'decimal_places': 0
                    },
                    {
                        'name': 'density_status',
                        'label': 'SEO Status',
                        'type': 'text'
                    }
                ],
                'formulas': [
                    {
                        'name': 'word_count',
                        'expression': 'len(content.split())',
                        'description': 'Count total words in content'
                    },
                    {
                        'name': 'keyword_occurrences',
                        'expression': 'content.lower().count(target_keyword.lower())',
                        'description': 'Count keyword occurrences'
                    },
                    {
                        'name': 'keyword_density',
                        'expression': '(keyword_occurrences / word_count) * 100 if word_count > 0 else 0',
                        'description': 'Calculate keyword density percentage',
                        'depends_on': ['word_count', 'keyword_occurrences'],
                        'round_to': 2
                    },
                    {
                        'name': 'keyword_count',
                        'expression': 'keyword_occurrences',
                        'depends_on': ['keyword_occurrences']
                    },
                    {
                        'name': 'total_words',
                        'expression': 'word_count',
                        'depends_on': ['word_count']
                    },
                    {
                        'name': 'density_status',
                        'expression': '"Optimal" if keyword_density <= max_density else "Too High"',
                        'depends_on': ['keyword_density']
                    }
                ],
                'validations': [
                    {
                        'field_name': 'content',
                        'rules': ['len(content) >= 50'],
                        'error_messages': {
                            'len(content) >= 50': 'Content must be at least 50 characters'
                        }
                    }
                ],
                'metadata': {
                    'title': 'Keyword Density Calculator for SEO',
                    'description': 'Analyze keyword density to optimize your content for search engines while avoiding keyword stuffing.',
                    'keywords': ['keyword density', 'SEO', 'content optimization', 'keyword frequency'],
                    'author': 'SEO Bot',
                    'application_category': 'BusinessApplication',
                    'operating_system': ['Web'],
                    'software_version': '1.0'
                }
            },
            {
                'id': 'page_load_budget',
                'title': 'Page Load Time Budget Calculator',
                'description': 'Calculate performance budgets for different page types and connection speeds',
                'category': 'technical',
                'inputs': [
                    {
                        'name': 'page_type',
                        'type': 'select',
                        'label': 'Page Type',
                        'required': True,
                        'options': [
                            {'value': 'landing', 'label': 'Landing Page'},
                            {'value': 'article', 'label': 'Article/Blog Post'},
                            {'value': 'product', 'label': 'Product Page'},
                            {'value': 'category', 'label': 'Category Page'}
                        ]
                    },
                    {
                        'name': 'connection_speed',
                        'type': 'select',
                        'label': 'Target Connection Speed',
                        'required': True,
                        'options': [
                            {'value': 'fast_3g', 'label': 'Fast 3G (1.6 Mbps)'},
                            {'value': 'slow_3g', 'label': 'Slow 3G (400 Kbps)'},
                            {'value': 'fast_4g', 'label': 'Fast 4G (9 Mbps)'},
                            {'value': 'broadband', 'label': 'Broadband (10+ Mbps)'}
                        ]
                    },
                    {
                        'name': 'target_lcp',
                        'type': 'number',
                        'label': 'Target LCP (seconds)',
                        'description': 'Largest Contentful Paint target',
                        'default_value': 2.5,
                        'min_value': 1.0,
                        'max_value': 5.0,
                        'step': 0.1
                    }
                ],
                'outputs': [
                    {
                        'name': 'js_budget_kb',
                        'label': 'JavaScript Budget',
                        'type': 'number',
                        'unit': 'KB',
                        'highlight': True
                    },
                    {
                        'name': 'css_budget_kb',
                        'label': 'CSS Budget',
                        'type': 'number',
                        'unit': 'KB'
                    },
                    {
                        'name': 'image_budget_kb',
                        'label': 'Image Budget',
                        'type': 'number',
                        'unit': 'KB'
                    },
                    {
                        'name': 'total_budget_kb',
                        'label': 'Total Page Budget',
                        'type': 'number',
                        'unit': 'KB'
                    }
                ],
                'formulas': [
                    {
                        'name': 'connection_factor',
                        'expression': '{"slow_3g": 0.5, "fast_3g": 0.8, "fast_4g": 1.2, "broadband": 1.5}[connection_speed]'
                    },
                    {
                        'name': 'page_factor',
                        'expression': '{"landing": 1.0, "article": 0.8, "product": 1.2, "category": 0.9}[page_type]'
                    },
                    {
                        'name': 'base_js_budget',
                        'expression': '200 * connection_factor * page_factor',
                        'depends_on': ['connection_factor', 'page_factor']
                    },
                    {
                        'name': 'js_budget_kb',
                        'expression': 'round(base_js_budget)',
                        'depends_on': ['base_js_budget']
                    },
                    {
                        'name': 'css_budget_kb',
                        'expression': 'round(js_budget_kb * 0.4)',
                        'depends_on': ['js_budget_kb']
                    },
                    {
                        'name': 'image_budget_kb',
                        'expression': 'round(js_budget_kb * 2.5)',
                        'depends_on': ['js_budget_kb']
                    },
                    {
                        'name': 'total_budget_kb',
                        'expression': 'js_budget_kb + css_budget_kb + image_budget_kb',
                        'depends_on': ['js_budget_kb', 'css_budget_kb', 'image_budget_kb']
                    }
                ],
                'metadata': {
                    'title': 'Page Load Time Budget Calculator',
                    'description': 'Calculate performance budgets to ensure fast page load times across different devices and connection speeds.',
                    'keywords': ['performance budget', 'page speed', 'web performance', 'LCP', 'Core Web Vitals'],
                    'author': 'SEO Bot',
                    'application_category': 'DeveloperApplication'
                }
            }
        ]
    }


def load_registry_from_yaml(yaml_path: Path) -> ToolRegistry:
    """Load tool registry from YAML file."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    
    return create_registry_from_dict(data)


def create_registry_from_dict(data: Dict) -> ToolRegistry:
    """Create ToolRegistry from dictionary data."""
    calculators = []
    
    for calc_data in data.get('calculators', []):
        try:
            spec = CalculatorSpec(**calc_data)
            calculators.append(spec)
        except Exception as e:
            logger.error(f"Failed to create calculator {calc_data.get('id', 'unknown')}: {e}")
    
    return ToolRegistry(
        version=data.get('version', '1.0'),
        calculators=calculators,
        categories=data.get('categories', {}),
        default_theme=data.get('default_theme', 'modern'),
        analytics_enabled=data.get('analytics_enabled', True)
    )


def save_registry_to_yaml(registry: ToolRegistry, output_path: Path):
    """Save tool registry to YAML file."""
    data = {
        'version': registry.version,
        'categories': registry.categories,
        'calculators': [calc.dict() for calc in registry.calculators]
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def create_sample_registry_file(output_path: Path):
    """Create a sample registry YAML file."""
    sample_data = create_sample_registry()
    
    with open(output_path, 'w') as f:
        yaml.dump(sample_data, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Created sample registry: {output_path}")


class RegistryManager:
    """Manages calculator registry operations."""
    
    def __init__(self, registry_path: Path, output_dir: Path):
        self.registry_path = registry_path
        self.output_dir = output_dir
        self.generator = ToolGenerator(output_dir)
    
    def load_registry(self) -> ToolRegistry:
        """Load registry from configured path."""
        return load_registry_from_yaml(self.registry_path)
    
    def validate_registry(self) -> Dict[str, List[str]]:
        """Validate the registry."""
        registry = self.load_registry()
        return registry.validate_all_calculators()
    
    def generate_all_tools(self) -> Dict[str, List[str]]:
        """Generate all tools from registry."""
        return self.generator.generate_from_registry(self.registry_path)
    
    def add_calculator(self, spec: CalculatorSpec) -> bool:
        """Add a new calculator to the registry."""
        try:
            registry = self.load_registry()
            
            # Check for duplicate IDs
            if registry.get_calculator(spec.id):
                logger.error(f"Calculator with ID '{spec.id}' already exists")
                return False
            
            registry.calculators.append(spec)
            save_registry_to_yaml(registry, self.registry_path)
            
            logger.info(f"Added calculator: {spec.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add calculator: {e}")
            return False
    
    def update_calculator(self, spec: CalculatorSpec) -> bool:
        """Update an existing calculator in the registry."""
        try:
            registry = self.load_registry()
            
            # Find and replace calculator
            for i, calc in enumerate(registry.calculators):
                if calc.id == spec.id:
                    registry.calculators[i] = spec
                    save_registry_to_yaml(registry, self.registry_path)
                    logger.info(f"Updated calculator: {spec.id}")
                    return True
            
            logger.error(f"Calculator with ID '{spec.id}' not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update calculator: {e}")
            return False
    
    def remove_calculator(self, calculator_id: str) -> bool:
        """Remove a calculator from the registry."""
        try:
            registry = self.load_registry()
            
            # Find and remove calculator
            original_count = len(registry.calculators)
            registry.calculators = [calc for calc in registry.calculators if calc.id != calculator_id]
            
            if len(registry.calculators) < original_count:
                save_registry_to_yaml(registry, self.registry_path)
                logger.info(f"Removed calculator: {calculator_id}")
                return True
            else:
                logger.error(f"Calculator with ID '{calculator_id}' not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove calculator: {e}")
            return False
    
    def get_calculator_usage_stats(self) -> Dict[str, Dict]:
        """Get usage statistics for all calculators."""
        registry = self.load_registry()
        
        stats = {}
        for calc in registry.calculators:
            stats[calc.id] = {
                'title': calc.title,
                'usage_count': calc.metadata.usage_count,
                'last_used': calc.metadata.last_used,
                'average_session_time': calc.metadata.average_session_time,
                'category': calc.category
            }
        
        return stats
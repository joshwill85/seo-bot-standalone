"""Data models for micro-tools and calculators."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, validator


class CalculatorInput(BaseModel):
    """Input field specification for calculator."""
    name: str
    type: Literal["number", "text", "select", "checkbox", "range"]
    label: str
    description: Optional[str] = None
    required: bool = True
    
    # Validation constraints
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # Regex pattern for text inputs
    
    # Select options
    options: Optional[List[Dict[str, str]]] = None  # [{"value": "a", "label": "Option A"}]
    
    # Default values
    default_value: Optional[Union[str, int, float, bool]] = None
    
    # Units and formatting
    unit: Optional[str] = None
    prefix: Optional[str] = None  # e.g., "$" for currency
    suffix: Optional[str] = None
    
    # UI attributes
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    css_class: Optional[str] = None


class CalculatorOutput(BaseModel):
    """Output field specification for calculator."""
    name: str
    label: str
    description: Optional[str] = None
    
    # Formatting
    type: Literal["number", "text", "currency", "percentage", "duration"]
    unit: Optional[str] = None
    decimal_places: int = 2
    format_style: Optional[str] = None  # Custom format string
    
    # Display options
    highlight: bool = False  # Primary result
    show_chart: bool = False
    chart_type: Optional[Literal["bar", "pie", "line"]] = None
    
    # Conditional display
    show_when: Optional[str] = None  # Expression for when to show


class CalculatorFormula(BaseModel):
    """Formula definition for calculator."""
    name: str
    expression: str  # Mathematical expression using input variables
    description: Optional[str] = None
    
    # Dependencies
    depends_on: List[str] = []  # List of input/formula names this depends on
    
    # Validation
    min_result: Optional[Union[int, float]] = None
    max_result: Optional[Union[int, float]] = None
    round_to: Optional[int] = None


class CalculatorResult(BaseModel):
    """Result from calculator execution."""
    calculator_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    intermediate_values: Dict[str, Any] = {}
    errors: List[str] = []
    warnings: List[str] = []
    execution_time_ms: float = 0.0
    calculated_at: datetime = Field(default_factory=datetime.now)


class CalculatorValidation(BaseModel):
    """Validation rules for calculator inputs."""
    field_name: str
    rules: List[str]  # Validation expressions
    error_messages: Dict[str, str]  # rule -> error message
    
    # Cross-field validation
    depends_on: List[str] = []


class CalculatorMetadata(BaseModel):
    """Metadata for calculator SEO and schema."""
    title: str
    description: str
    keywords: List[str] = []
    author: Optional[str] = None
    
    # Schema.org SoftwareApplication
    application_category: str = "BusinessApplication" 
    operating_system: List[str] = ["Web"]
    software_version: str = "1.0"
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    average_session_time: float = 0.0


class CalculatorSpec(BaseModel):
    """Complete calculator specification."""
    id: str
    title: str
    description: str
    category: str
    
    # Definition
    inputs: List[CalculatorInput]
    outputs: List[CalculatorOutput]
    formulas: List[CalculatorFormula]
    validations: List[CalculatorValidation] = []
    
    # Metadata
    metadata: CalculatorMetadata
    
    # Localization
    i18n: Dict[str, Dict[str, str]] = {}  # locale -> translations
    
    # Styling and layout
    layout: Dict[str, Any] = {}
    css_theme: Optional[str] = None
    
    # Advanced features
    show_step_by_step: bool = False
    allow_save_results: bool = False
    enable_comparisons: bool = False
    
    # Quality gates
    min_inputs_required: int = 1
    max_execution_time_ms: float = 1000.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @validator('id')
    def validate_id(cls, v):
        """Ensure ID is valid for file names and URLs."""
        import re
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError('ID must contain only lowercase letters, numbers, and underscores')
        return v
    
    def get_required_inputs(self) -> List[CalculatorInput]:
        """Get list of required inputs."""
        return [inp for inp in self.inputs if inp.required]
    
    def get_primary_outputs(self) -> List[CalculatorOutput]:
        """Get highlighted/primary outputs."""
        primary = [out for out in self.outputs if out.highlight]
        return primary if primary else self.outputs[:1]  # First output if none highlighted


class ToolRegistry(BaseModel):
    """Registry of all calculator tools."""
    version: str = "1.0"
    calculators: List[CalculatorSpec] = []
    categories: Dict[str, str] = {}  # category_id -> description
    
    # Global settings
    default_theme: str = "modern"
    analytics_enabled: bool = True
    cache_results: bool = True
    
    # Quality thresholds
    min_usage_for_featured: int = 100
    max_execution_time_warning: float = 500.0
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def get_calculator(self, calculator_id: str) -> Optional[CalculatorSpec]:
        """Get calculator by ID."""
        for calc in self.calculators:
            if calc.id == calculator_id:
                return calc
        return None
    
    def get_calculators_by_category(self, category: str) -> List[CalculatorSpec]:
        """Get all calculators in a category."""
        return [calc for calc in self.calculators if calc.category == category]
    
    def get_featured_calculators(self) -> List[CalculatorSpec]:
        """Get calculators with high usage."""
        return [
            calc for calc in self.calculators 
            if calc.metadata.usage_count >= self.min_usage_for_featured
        ]
    
    def validate_all_calculators(self) -> Dict[str, List[str]]:
        """Validate all calculators and return errors."""
        errors = {}
        for calc in self.calculators:
            calc_errors = []
            
            # Check for circular dependencies
            for formula in calc.formulas:
                if self._has_circular_dependency(calc, formula):
                    calc_errors.append(f"Circular dependency in formula: {formula.name}")
            
            # Validate formula expressions
            for formula in calc.formulas:
                if not self._validate_formula_syntax(formula.expression):
                    calc_errors.append(f"Invalid formula syntax: {formula.name}")
            
            if calc_errors:
                errors[calc.id] = calc_errors
        
        return errors
    
    def _has_circular_dependency(self, calc: CalculatorSpec, formula: CalculatorFormula) -> bool:
        """Check for circular dependencies in formulas."""
        visited = set()
        
        def check_deps(formula_name: str) -> bool:
            if formula_name in visited:
                return True
            
            visited.add(formula_name)
            
            # Find formula by name
            for f in calc.formulas:
                if f.name == formula_name:
                    for dep in f.depends_on:
                        if check_deps(dep):
                            return True
            
            visited.remove(formula_name)
            return False
        
        return check_deps(formula.name)
    
    def _validate_formula_syntax(self, expression: str) -> bool:
        """Basic validation of formula syntax."""
        # Check for balanced parentheses
        count = 0
        for char in expression:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
                if count < 0:
                    return False
        
        return count == 0
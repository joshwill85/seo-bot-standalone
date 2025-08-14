"""Formula evaluation and validation engine for calculators."""

import ast
import logging
import math
import operator
import re
import time
from typing import Any, Dict, List, Optional, Set

from .models import CalculatorSpec, CalculatorInput, CalculatorResult, CalculatorValidation


logger = logging.getLogger(__name__)


class SafeMathEvaluator:
    """Safe mathematical expression evaluator."""
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Allowed functions
    FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'sqrt': math.sqrt,
        'pow': pow,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'ceil': math.ceil,
        'floor': math.floor,
        'pi': math.pi,
        'e': math.e,
    }
    
    def __init__(self, max_execution_time: float = 1.0):
        self.max_execution_time = max_execution_time
        self.start_time = 0.0
    
    def evaluate(self, expression: str, variables: Dict[str, Any]) -> Any:
        """Safely evaluate mathematical expression."""
        self.start_time = time.time()
        
        try:
            # Parse expression to AST
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate AST
            result = self._eval_node(tree.body, variables)
            
            execution_time = time.time() - self.start_time
            if execution_time > self.max_execution_time:
                raise ValueError(f"Execution time exceeded {self.max_execution_time}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            raise ValueError(f"Expression evaluation failed: {e}")
    
    def _eval_node(self, node: ast.AST, variables: Dict[str, Any]) -> Any:
        """Recursively evaluate AST node."""
        # Check execution time
        if time.time() - self.start_time > self.max_execution_time:
            raise ValueError("Execution time limit exceeded")
        
        if isinstance(node, ast.Constant):
            return node.value
        
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            elif node.id in self.FUNCTIONS:
                return self.FUNCTIONS[node.id]
            else:
                raise NameError(f"Undefined variable: {node.id}")
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op = self.OPERATORS.get(type(node.op))
            if op:
                return op(left, right)
            else:
                raise ValueError(f"Unsupported operator: {type(node.op)}")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, variables)
            op = self.OPERATORS.get(type(node.op))
            if op:
                return op(operand)
            else:
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
        
        elif isinstance(node, ast.Call):
            func = self._eval_node(node.func, variables)
            if not callable(func):
                raise ValueError(f"Not callable: {func}")
            
            args = [self._eval_node(arg, variables) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value, variables) for kw in node.keywords}
            
            return func(*args, **kwargs)
        
        elif isinstance(node, ast.List):
            return [self._eval_node(elem, variables) for elem in node.elts]
        
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, variables)
            
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, variables)
                
                if isinstance(op, ast.Lt):
                    result = left < right
                elif isinstance(op, ast.LtE):
                    result = left <= right
                elif isinstance(op, ast.Gt):
                    result = left > right
                elif isinstance(op, ast.GtE):
                    result = left >= right
                elif isinstance(op, ast.Eq):
                    result = left == right
                elif isinstance(op, ast.NotEq):
                    result = left != right
                else:
                    raise ValueError(f"Unsupported comparison: {type(op)}")
                
                if not result:
                    return False
                
                left = right  # Chain comparisons
            
            return True
        
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(value, variables) for value in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(value, variables) for value in node.values)
        
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")


class ValidationEngine:
    """Input validation engine for calculators."""
    
    def __init__(self):
        self.evaluator = SafeMathEvaluator()
    
    def validate_inputs(self, spec: CalculatorSpec, inputs: Dict[str, Any]) -> List[str]:
        """Validate all inputs according to specification."""
        errors = []
        
        # Check required inputs
        for input_spec in spec.inputs:
            if input_spec.required and input_spec.name not in inputs:
                errors.append(f"Required field '{input_spec.label}' is missing")
                continue
            
            if input_spec.name in inputs:
                field_errors = self._validate_single_input(input_spec, inputs[input_spec.name])
                errors.extend(field_errors)
        
        # Run custom validations
        for validation in spec.validations:
            validation_errors = self._run_custom_validation(validation, inputs)
            errors.extend(validation_errors)
        
        return errors
    
    def _validate_single_input(self, input_spec: CalculatorInput, value: Any) -> List[str]:
        """Validate a single input field."""
        errors = []
        
        # Type validation
        if input_spec.type == "number":
            try:
                numeric_value = float(value)
                
                if input_spec.min_value is not None and numeric_value < input_spec.min_value:
                    errors.append(f"{input_spec.label} must be at least {input_spec.min_value}")
                
                if input_spec.max_value is not None and numeric_value > input_spec.max_value:
                    errors.append(f"{input_spec.label} must be at most {input_spec.max_value}")
                
            except (ValueError, TypeError):
                errors.append(f"{input_spec.label} must be a valid number")
        
        elif input_spec.type == "text":
            if not isinstance(value, str):
                errors.append(f"{input_spec.label} must be text")
            elif input_spec.pattern:
                if not re.match(input_spec.pattern, value):
                    errors.append(f"{input_spec.label} format is invalid")
        
        elif input_spec.type == "select":
            if input_spec.options:
                valid_values = [opt["value"] for opt in input_spec.options]
                if value not in valid_values:
                    errors.append(f"{input_spec.label} must be one of: {', '.join(valid_values)}")
        
        elif input_spec.type == "checkbox":
            if not isinstance(value, bool):
                errors.append(f"{input_spec.label} must be true or false")
        
        return errors
    
    def _run_custom_validation(self, validation: CalculatorValidation, inputs: Dict[str, Any]) -> List[str]:
        """Run custom validation rules."""
        errors = []
        
        # Check if all dependencies are present
        for dep in validation.depends_on:
            if dep not in inputs:
                return []  # Skip validation if dependencies missing
        
        for rule in validation.rules:
            try:
                # Evaluate validation rule
                result = self.evaluator.evaluate(rule, inputs)
                
                if not result:
                    error_msg = validation.error_messages.get(rule, f"Validation failed: {rule}")
                    errors.append(error_msg)
                    
            except Exception as e:
                logger.warning(f"Validation rule failed to execute: {rule} - {e}")
        
        return errors


class FormulaEvaluator:
    """Main formula evaluation engine."""
    
    def __init__(self, max_execution_time: float = 1.0):
        self.evaluator = SafeMathEvaluator(max_execution_time)
        self.validator = ValidationEngine()
    
    def calculate(self, spec: CalculatorSpec, inputs: Dict[str, Any]) -> CalculatorResult:
        """Execute calculator with given inputs."""
        start_time = time.time()
        
        result = CalculatorResult(
            calculator_id=spec.id,
            inputs=inputs.copy(),
            outputs={},
            intermediate_values={},
            errors=[],
            warnings=[]
        )
        
        try:
            # Validate inputs
            validation_errors = self.validator.validate_inputs(spec, inputs)
            if validation_errors:
                result.errors.extend(validation_errors)
                return result
            
            # Prepare variable context
            variables = inputs.copy()
            
            # Sort formulas by dependencies
            sorted_formulas = self._sort_formulas_by_dependencies(spec.formulas)
            
            # Evaluate formulas in order
            for formula in sorted_formulas:
                try:
                    formula_result = self.evaluator.evaluate(formula.expression, variables)
                    
                    # Apply rounding if specified
                    if formula.round_to is not None:
                        formula_result = round(formula_result, formula.round_to)
                    
                    # Validate result range
                    if formula.min_result is not None and formula_result < formula.min_result:
                        result.warnings.append(f"{formula.name} result below minimum: {formula_result}")
                    
                    if formula.max_result is not None and formula_result > formula.max_result:
                        result.warnings.append(f"{formula.name} result above maximum: {formula_result}")
                    
                    # Store result
                    variables[formula.name] = formula_result
                    result.intermediate_values[formula.name] = formula_result
                    
                except Exception as e:
                    result.errors.append(f"Formula '{formula.name}' failed: {e}")
            
            # Extract outputs
            for output_spec in spec.outputs:
                if output_spec.name in variables:
                    value = variables[output_spec.name]
                    
                    # Format output value
                    formatted_value = self._format_output(output_spec, value)
                    result.outputs[output_spec.name] = formatted_value
        
        except Exception as e:
            result.errors.append(f"Calculation failed: {e}")
        
        # Record execution time
        result.execution_time_ms = (time.time() - start_time) * 1000
        
        # Check execution time warning
        if result.execution_time_ms > spec.max_execution_time_ms:
            result.warnings.append(f"Execution time ({result.execution_time_ms:.1f}ms) exceeded recommended limit")
        
        return result
    
    def _sort_formulas_by_dependencies(self, formulas: List) -> List:
        """Sort formulas by dependency order using topological sort."""
        from collections import defaultdict, deque
        
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        formula_dict = {f.name: f for f in formulas}
        
        for formula in formulas:
            in_degree[formula.name] = 0
        
        for formula in formulas:
            for dep in formula.depends_on:
                if dep in formula_dict:  # Only formula dependencies
                    graph[dep].append(formula.name)
                    in_degree[formula.name] += 1
        
        # Topological sort
        queue = deque([name for name in in_degree if in_degree[name] == 0])
        sorted_names = []
        
        while queue:
            current = queue.popleft()
            sorted_names.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Return formulas in sorted order
        name_to_formula = {f.name: f for f in formulas}
        return [name_to_formula[name] for name in sorted_names if name in name_to_formula]
    
    def _format_output(self, output_spec, value: Any) -> Any:
        """Format output value according to specification."""
        if output_spec.type == "number":
            if isinstance(value, (int, float)):
                return round(value, output_spec.decimal_places)
        
        elif output_spec.type == "currency":
            if isinstance(value, (int, float)):
                return f"${value:,.{output_spec.decimal_places}f}"
        
        elif output_spec.type == "percentage":
            if isinstance(value, (int, float)):
                return f"{value * 100:.{output_spec.decimal_places}f}%"
        
        elif output_spec.type == "duration":
            if isinstance(value, (int, float)):
                # Convert to hours:minutes format
                hours = int(value)
                minutes = int((value - hours) * 60)
                return f"{hours}h {minutes}m"
        
        return value
    
    def validate_formula_syntax(self, expression: str) -> tuple:
        """Validate formula syntax without execution."""
        try:
            ast.parse(expression, mode='eval')
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {e.msg}"
        except Exception as e:
            return False, f"Parse error: {e}"
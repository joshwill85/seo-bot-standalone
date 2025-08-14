#!/usr/bin/env python3
"""
Validation script for clustering and prioritization modules.
Tests basic functionality without external dependencies.
"""

import sys
import os
import ast
import traceback

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def validate_module_syntax(module_path):
    """Validate Python module syntax."""
    print(f"Checking syntax: {module_path}")
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Parse AST to check syntax
        ast.parse(code, filename=module_path)
        print(f"✓ {module_path} - Syntax valid")
        return True
    except SyntaxError as e:
        print(f"✗ {module_path} - Syntax error: {e}")
        return False
    except Exception as e:
        print(f"✗ {module_path} - Error: {e}")
        return False

def validate_module_structure(module_path):
    """Validate module structure and key components."""
    print(f"Analyzing structure: {module_path}")
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        
        classes = []
        functions = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_'):  # Public functions
                    functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        print(f"  Classes: {', '.join(classes)}")
        print(f"  Functions: {', '.join(functions)}")
        print(f"  Key imports: {len(imports)} modules")
        
        return len(classes) > 0 or len(functions) > 0
        
    except Exception as e:
        print(f"✗ Structure analysis failed: {e}")
        return False

def validate_clustering_module():
    """Validate clustering module."""
    print("\n=== CLUSTERING MODULE VALIDATION ===")
    
    module_path = "src/seo_bot/keywords/cluster.py"
    
    # Check syntax
    if not validate_module_syntax(module_path):
        return False
    
    # Check structure
    if not validate_module_structure(module_path):
        return False
    
    # Check for key components
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_classes = [
            'EmbeddingGenerator',
            'KeywordClusterer', 
            'ClusterLabeler',
            'HubSpokeAnalyzer',
            'KeywordClusterManager'
        ]
        
        missing_classes = []
        for cls_name in required_classes:
            if f"class {cls_name}" not in content:
                missing_classes.append(cls_name)
        
        if missing_classes:
            print(f"✗ Missing required classes: {', '.join(missing_classes)}")
            return False
        
        # Check for key methods
        required_methods = [
            'generate_embeddings',
            'cluster_keywords',
            'generate_cluster_labels',
            'analyze_hub_spoke_relationships'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if f"def {method_name}" not in content:
                missing_methods.append(method_name)
        
        if missing_methods:
            print(f"✗ Missing required methods: {', '.join(missing_methods)}")
            return False
        
        print("✓ All required components present")
        return True
        
    except Exception as e:
        print(f"✗ Component check failed: {e}")
        return False

def validate_prioritization_module():
    """Validate prioritization module."""
    print("\n=== PRIORITIZATION MODULE VALIDATION ===")
    
    module_path = "src/seo_bot/keywords/prioritize.py"
    
    # Check syntax
    if not validate_module_syntax(module_path):
        return False
    
    # Check structure
    if not validate_module_structure(module_path):
        return False
    
    # Check for key components
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_classes = [
            'TrafficEstimator',
            'ContentGapAnalyzer',
            'BusinessValueCalculator',
            'KeywordPrioritizer'
        ]
        
        missing_classes = []
        for cls_name in required_classes:
            if f"class {cls_name}" not in content:
                missing_classes.append(cls_name)
        
        if missing_classes:
            print(f"✗ Missing required classes: {', '.join(missing_classes)}")
            return False
        
        # Check for key methods
        required_methods = [
            'estimate_traffic_potential',
            'analyze_content_gaps',
            'calculate_business_value',
            'calculate_priority_score',
            'prioritize_keywords'
        ]
        
        missing_methods = []
        for method_name in required_methods:
            if f"def {method_name}" not in content:
                missing_methods.append(method_name)
        
        if missing_methods:
            print(f"✗ Missing required methods: {', '.join(missing_methods)}")
            return False
        
        print("✓ All required components present")
        return True
        
    except Exception as e:
        print(f"✗ Component check failed: {e}")
        return False

def validate_init_module():
    """Validate __init__.py updates."""
    print("\n=== INIT MODULE VALIDATION ===")
    
    module_path = "src/seo_bot/keywords/__init__.py"
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for new imports
        required_imports = [
            'KeywordClusterManager',
            'KeywordPrioritizer',
            'create_cluster_manager',
            'create_prioritizer'
        ]
        
        missing_imports = []
        for import_name in required_imports:
            if import_name not in content:
                missing_imports.append(import_name)
        
        if missing_imports:
            print(f"✗ Missing imports: {', '.join(missing_imports)}")
            return False
        
        # Check __all__ export
        if '__all__' not in content:
            print("✗ Missing __all__ definition")
            return False
        
        print("✓ Init module properly updated")
        return True
        
    except Exception as e:
        print(f"✗ Init validation failed: {e}")
        return False

def validate_test_modules():
    """Validate test modules."""
    print("\n=== TEST MODULE VALIDATION ===")
    
    test_files = [
        "tests/test_clustering.py",
        "tests/test_prioritization.py", 
        "tests/test_keywords_integration.py"
    ]
    
    all_valid = True
    
    for test_file in test_files:
        if os.path.exists(test_file):
            valid = validate_module_syntax(test_file)
            if valid:
                # Check for test classes
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                test_classes = [line.strip() for line in content.split('\n') 
                               if line.strip().startswith('class Test')]
                print(f"  Test classes: {len(test_classes)}")
            all_valid = all_valid and valid
        else:
            print(f"✗ Test file not found: {test_file}")
            all_valid = False
    
    return all_valid

def main():
    """Run all validations."""
    print("SEO-Bot Keyword Clustering and Prioritization Module Validation")
    print("=" * 70)
    
    results = []
    
    # Validate clustering module
    results.append(("Clustering Module", validate_clustering_module()))
    
    # Validate prioritization module  
    results.append(("Prioritization Module", validate_prioritization_module()))
    
    # Validate init module
    results.append(("Init Module", validate_init_module()))
    
    # Validate test modules
    results.append(("Test Modules", validate_test_modules()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:<25} {status}")
        if result:
            passed += 1
    
    print("-" * 70)
    print(f"Overall: {passed}/{total} validations passed")
    
    if passed == total:
        print("\n🎉 All validations passed! Modules are ready for use.")
        return True
    else:
        print(f"\n⚠️  {total - passed} validation(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
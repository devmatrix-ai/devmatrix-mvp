"""
Code Analyzer - Extract entities, endpoints, and business logic from generated code

Uses AST parsing to extract implementation details from Python code for compliance validation.
Part of Task Group 4.1: Semantic Validation System.
"""
import ast
import re
import logging
from typing import List, Set, Dict, Optional, Any

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Analyzes generated Python code to extract:
    - Pydantic model definitions (entities)
    - FastAPI route decorators (endpoints)
    - Business logic signatures (validations, calculations)

    Uses Python's AST module for accurate parsing.
    """

    def __init__(self):
        """Initialize code analyzer"""
        logger.info("CodeAnalyzer initialized")

    def extract_models(self, code: str) -> List[str]:
        """
        Extract Pydantic model names from code

        Looks for classes that inherit from BaseModel:
        class Product(BaseModel):
            ...

        Args:
            code: Python source code string

        Returns:
            List of model class names (e.g., ["Product", "Customer"])
        """
        models = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class inherits from BaseModel
                    for base in node.bases:
                        # Handle direct inheritance: BaseModel
                        if isinstance(base, ast.Name) and base.id == "BaseModel":
                            models.append(node.name)
                            break
                        # Handle module path: pydantic.BaseModel
                        elif isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                            models.append(node.name)
                            break

            logger.info(f"Extracted {len(models)} models: {models}")
            return models

        except SyntaxError as e:
            logger.error(f"Syntax error parsing code: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting models: {e}")
            return []

    def extract_endpoints(self, code: str) -> List[str]:
        """
        Extract FastAPI endpoint definitions from code

        Looks for FastAPI route decorators:
        @app.get("/products")
        @app.post("/products")
        etc.

        Handles both sync and async functions.

        Args:
            code: Python source code string

        Returns:
            List of endpoints in format "METHOD /path"
            (e.g., ["GET /products", "POST /products/{id}"])
        """
        endpoints = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Handle both sync (FunctionDef) and async (AsyncFunctionDef) functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check decorators for FastAPI routes
                    for decorator in node.decorator_list:
                        endpoint = self._parse_route_decorator(decorator)
                        if endpoint:
                            endpoints.append(endpoint)

            logger.info(f"Extracted {len(endpoints)} endpoints")
            return endpoints

        except SyntaxError as e:
            logger.error(f"Syntax error parsing code: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting endpoints: {e}")
            return []

    def _parse_route_decorator(self, decorator: ast.expr) -> Optional[str]:
        """
        Parse FastAPI route decorator to extract method and path

        Handles patterns like:
        - @app.get("/products")
        - @app.post("/products/{id}")
        - @router.put("/items")
        - Direct decorators without app prefix

        Args:
            decorator: AST decorator node

        Returns:
            Endpoint string "METHOD /path" or None
        """
        # Decorators can be either ast.Call (with args) or ast.Attribute (without args)
        # We need ast.Call with arguments for route decorators
        if not isinstance(decorator, ast.Call):
            # Try to handle decorator as attribute (e.g., @app.get)
            # But route decorators MUST have arguments (the path)
            return None

        # Get the decorator function (e.g., app.get, app.post)
        func = decorator.func

        # Extract HTTP method
        method = None
        if isinstance(func, ast.Attribute):
            # Pattern: app.get, router.post, app.post
            attr_name = func.attr
            method = attr_name.upper()
        elif isinstance(func, ast.Name):
            # Pattern: get, post (less common, direct import)
            method = func.id.upper()
        else:
            return None

        # Validate HTTP method
        if method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
            return None

        # Extract path from first argument
        if not decorator.args:
            return None

        first_arg = decorator.args[0]
        path = None

        # Handle different AST node types for string literals
        if isinstance(first_arg, ast.Constant):
            # Python 3.8+: ast.Constant (preferred)
            path = first_arg.value
        elif isinstance(first_arg, ast.Str):
            # Python 3.7 and earlier: ast.Str (deprecated but still supported)
            path = first_arg.s
        elif isinstance(first_arg, ast.JoinedStr):
            # f-string (rare for route paths, but possible)
            return None

        # Validate path is a string
        if not path or not isinstance(path, str):
            return None

        return f"{method} {path}"

    def extract_validations(self, code: str) -> List[str]:
        """
        Detect business logic signatures in code

        Looks for:
        - Validation logic: if price <= 0, email format checks
        - Calculations: total = sum(items * quantity)
        - Stock checks: if stock < quantity
        - Field validators: Field(gt=0), Field(ge=0)
        - Custom validators: @field_validator decorators

        Args:
            code: Python source code string

        Returns:
            List of business logic descriptions (ALL instances, not deduplicated)
        """
        validations = []

        try:
            tree = ast.parse(code)

            # 1. Extract ALL Pydantic Field constraint instances (not just unique types)
            field_constraint_count = 0
            for node in ast.walk(tree):
                # Check for Field(gt=0), Field(ge=0), etc.
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "Field":
                        for keyword in node.keywords:
                            if keyword.arg in ["gt", "ge", "lt", "le", "min_length", "max_length", "decimal_places"]:
                                # Count each instance separately, not just type
                                field_constraint_count += 1
                                validations.append(f"field_constraint_{keyword.arg}_{field_constraint_count}")

            # 2. Extract @field_validator decorators
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        # Handle @field_validator('field_name')
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, 'id') and decorator.func.id == 'field_validator':
                                validations.append(f"field_validator_{node.name}")
                        # Handle @field_validator without parentheses (rare)
                        elif isinstance(decorator, ast.Name) and decorator.id == 'field_validator':
                            validations.append(f"field_validator_{node.name}")

            # 3. Extract type validators (EmailStr, etc.)
            if 'EmailStr' in code or 'emailstr' in code.lower():
                # Count each EmailStr field
                email_count = code.count('EmailStr') + code.lower().count('emailstr')
                for i in range(email_count):
                    validations.append(f"email_validation_{i+1}")

            # 4. Extract comparison validations from code (each occurrence)
            code_lower = code.lower()

            # Price validations (count occurrences)
            price_matches = len(re.findall(r'price\s*[<>]=?\s*0', code_lower))
            for i in range(price_matches):
                validations.append(f"price_validation_{i+1}")

            # Stock validations (count occurrences)
            stock_matches = len(re.findall(r'stock\s*[<>]=?\s*0', code_lower)) + \
                           len(re.findall(r'stock\s*[<>]=?\s*quantity', code_lower))
            for i in range(stock_matches):
                validations.append(f"stock_validation_{i+1}")

            # Quantity validations (count occurrences)
            quantity_matches = len(re.findall(r'quantity\s*[<>]=?\s*0', code_lower))
            for i in range(quantity_matches):
                validations.append(f"quantity_validation_{i+1}")

            # HTTPException for validation errors (count 400 errors)
            if 'httpexception' in code_lower:
                error_400_count = code.count('400')
                for i in range(error_400_count):
                    validations.append(f"validation_error_handling_{i+1}")

            # is_active checks
            is_active_checks = code_lower.count('is_active')
            if is_active_checks > 0:
                for i in range(is_active_checks):
                    validations.append(f"is_active_validation_{i+1}")

            # Calculate/sum patterns
            if 'total' in code_lower and ('sum' in code_lower or 'calculate' in code_lower):
                validations.append("calculate_total")

            # DON'T deduplicate - return ALL instances
            logger.info(f"Extracted {len(validations)} validation instances (all occurrences counted)")
            return validations

        except Exception as e:
            logger.error(f"Error extracting validations: {e}")
            return []

    def extract_field_constraints(self, code: str, entity_name: str) -> List[str]:
        """
        Extract field constraints for a specific entity

        Args:
            code: Python source code
            entity_name: Entity class name (e.g., "Product")

        Returns:
            List of constraints found in entity definition
        """
        constraints = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == entity_name:
                    # Found the entity class
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            # Field definition: field_name: Type = Field(...)
                            if isinstance(item.value, ast.Call):
                                if isinstance(item.value.func, ast.Name) and \
                                   item.value.func.id == "Field":
                                    # Extract Field constraints
                                    for kw in item.value.keywords:
                                        if kw.arg in ["gt", "ge", "lt", "le"]:
                                            constraints.append(f"{kw.arg}")

            return constraints

        except Exception as e:
            logger.error(f"Error extracting field constraints: {e}")
            return []

    def extract_business_logic_from_function(self, code: str, function_name: str) -> Dict[str, Any]:
        """
        Extract business logic from a specific function

        Args:
            code: Python source code
            function_name: Function name to analyze

        Returns:
            Dict with business logic details
        """
        logic = {
            "has_validation": False,
            "has_calculation": False,
            "has_error_handling": False,
            "checks": []
        }

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Analyze function body
                    for stmt in ast.walk(node):
                        # Check for comparisons (validations)
                        if isinstance(stmt, ast.Compare):
                            logic["has_validation"] = True

                        # Check for calculations
                        if isinstance(stmt, ast.BinOp):
                            if isinstance(stmt.op, (ast.Add, ast.Sub, ast.Mult)):
                                logic["has_calculation"] = True

                        # Check for HTTPException (error handling)
                        if isinstance(stmt, ast.Raise):
                            logic["has_error_handling"] = True

            return logic

        except Exception as e:
            logger.error(f"Error extracting business logic: {e}")
            return logic

    def get_code_statistics(self, code: str) -> Dict[str, int]:
        """
        Get code statistics for analysis

        Args:
            code: Python source code

        Returns:
            Dict with statistics (LOC, functions, classes, etc.)
        """
        stats = {
            "total_lines": 0,
            "code_lines": 0,
            "functions": 0,
            "classes": 0,
            "imports": 0
        }

        try:
            # Count lines
            lines = code.split('\n')
            stats["total_lines"] = len(lines)
            stats["code_lines"] = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

            # Parse AST for structure
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    stats["functions"] += 1
                elif isinstance(node, ast.ClassDef):
                    stats["classes"] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    stats["imports"] += 1

            return stats

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return stats

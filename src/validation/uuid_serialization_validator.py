"""
UUID Serialization Validator

Detects and auto-repairs UUID serialization issues in generated FastAPI apps.
Runs post-generation to catch issues regardless of which generation path was used.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class UUIDSerializationValidator:
    """Validate and auto-repair UUID serialization in generated FastAPI apps."""
    
    def __init__(self, app_path: Path):
        """
        Initialize validator.
        
        Args:
            app_path: Path to generated app directory
        """
        self.app_path = Path(app_path)
        self.schemas_file = self.app_path / "src" / "models" / "schemas.py"
        self.exception_handlers_file = self.app_path / "src" / "core" / "exception_handlers.py"
        
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate UUID handling in generated app.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check 1: BaseSchema with json_encoders exists
        if not self._has_base_schema_with_encoders():
            issues.append("Missing BaseSchema with json_encoders = {UUID: str}")
        
        # Check 2: Response schemas inherit from BaseSchema
        if not self._response_schemas_use_base_schema():
            issues.append("Response schemas don't inherit from BaseSchema")
        
        # Check 3: Create schemas don't have id field
        create_schemas_with_id = self._find_create_schemas_with_id()
        if create_schemas_with_id:
            issues.append(f"Create schemas have 'id' field: {', '.join(create_schemas_with_id)}")
        
        # Check 4: Exception handlers use jsonable_encoder
        if not self._exception_handlers_use_jsonable_encoder():
            issues.append("Exception handlers don't use jsonable_encoder")
        
        return (len(issues) == 0, issues)
    
    def auto_repair(self) -> bool:
        """
        Auto-repair UUID serialization issues.
        
        Returns:
            True if repairs were successful
        """
        try:
            repairs_made = []
            
            # Repair 1: Add BaseSchema if missing
            if not self._has_base_schema_with_encoders():
                if self._add_base_schema():
                    repairs_made.append("Added BaseSchema with json_encoders")
            
            # Repair 2: Make response schemas inherit from BaseSchema
            if not self._response_schemas_use_base_schema():
                if self._update_response_schemas_inheritance():
                    repairs_made.append("Updated response schemas to inherit from BaseSchema")
            
            # Repair 3: Remove id from Create schemas
            create_schemas_with_id = self._find_create_schemas_with_id()
            if create_schemas_with_id:
                if self._remove_id_from_create_schemas(create_schemas_with_id):
                    repairs_made.append(f"Removed 'id' from Create schemas: {', '.join(create_schemas_with_id)}")
            
            # Repair 4: Add jsonable_encoder to exception handlers
            if not self._exception_handlers_use_jsonable_encoder():
                if self._add_jsonable_encoder_to_handlers():
                    repairs_made.append("Added jsonable_encoder to exception handlers")
            
            if repairs_made:
                logger.info(f"✅ UUID serialization auto-repairs completed: {', '.join(repairs_made)}")
                return True
            else:
                logger.info("✅ No UUID serialization repairs needed")
                return True
                
        except Exception as e:
            logger.error(f"❌ UUID serialization auto-repair failed: {e}")
            return False
    
    def _has_base_schema_with_encoders(self) -> bool:
        """Check if BaseSchema with json_encoders exists."""
        if not self.schemas_file.exists():
            return False
        
        content = self.schemas_file.read_text()
        return "class BaseSchema" in content and "json_encoders" in content and "UUID: str" in content
    
    def _response_schemas_use_base_schema(self) -> bool:
        """Check if response schemas inherit from BaseSchema."""
        if not self.schemas_file.exists():
            return False
        
        content = self.schemas_file.read_text()
        
        # Find all Response classes
        response_classes = re.findall(r'class (\w+Response)\((\w+)\):', content)
        
        if not response_classes:
            return True  # No response classes found, nothing to check
        
        # Check if they inherit from BaseSchema or a class that inherits from BaseSchema
        for class_name, parent in response_classes:
            if parent not in ["BaseSchema", "BaseModel"]:
                # Check if parent inherits from BaseSchema
                parent_def = re.search(rf'class {parent}\((\w+)\):', content)
                if parent_def and parent_def.group(1) != "BaseSchema":
                    return False
        
        return True
    
    def _find_create_schemas_with_id(self) -> List[str]:
        """Find Create schemas that have 'id' field (either directly or inherited)."""
        if not self.schemas_file.exists():
            return []
        
        content = self.schemas_file.read_text()
        create_schemas_with_id = []
        
        # Find all Create classes and their parent classes
        create_classes = re.findall(r'class (\w+Create)\((\w+)\):', content)
        
        for class_name, parent_class in create_classes:
            # Check if parent class has 'id' field
            parent_pattern = rf'class {parent_class}\([^)]*\):.*?(?=class |\Z)'
            parent_match = re.search(parent_pattern, content, re.DOTALL)
            
            if parent_match:
                parent_body = parent_match.group(0)
                # Check if parent has 'id:' field
                if re.search(r'\n\s+id\s*:', parent_body):
                    create_schemas_with_id.append(class_name)
        
        return create_schemas_with_id
    
    def _exception_handlers_use_jsonable_encoder(self) -> bool:
        """Check if exception handlers use jsonable_encoder."""
        if not self.exception_handlers_file.exists():
            return True  # No exception handlers file, nothing to check
        
        content = self.exception_handlers_file.read_text()
        
        # Check if jsonable_encoder is imported and used
        has_import = "from fastapi.encoders import jsonable_encoder" in content
        has_usage = "jsonable_encoder(" in content
        
        return has_import and has_usage
    
    def _add_base_schema(self) -> bool:
        """Add BaseSchema with json_encoders to schemas.py."""
        try:
            content = self.schemas_file.read_text()
            
            # Find the imports section
            import_section_end = content.rfind("from")
            if import_section_end == -1:
                import_section_end = 0
            else:
                # Find the end of the line
                import_section_end = content.find("\n", import_section_end) + 1
            
            # Insert BaseSchema after imports
            base_schema = '''
class BaseSchema(BaseModel):
    """Base schema with UUID serialization support."""
    class Config:
        json_encoders = {UUID: str}
        from_attributes = True

'''
            
            new_content = content[:import_section_end] + base_schema + content[import_section_end:]
            self.schemas_file.write_text(new_content)
            
            logger.info("✅ Added BaseSchema to schemas.py")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add BaseSchema: {e}")
            return False
    
    def _update_response_schemas_inheritance(self) -> bool:
        """Update response schemas to inherit from BaseSchema."""
        try:
            content = self.schemas_file.read_text()
            
            # Replace BaseModel with BaseSchema in Response classes
            # Pattern: class XxxResponse(BaseModel):
            pattern = r'(class \w+Response)\(BaseModel\):'
            replacement = r'\1(BaseSchema):'
            
            new_content = re.sub(pattern, replacement, content)
            
            if new_content != content:
                self.schemas_file.write_text(new_content)
                logger.info("✅ Updated response schemas to inherit from BaseSchema")
                return True
            
            return True  # No changes needed
            
        except Exception as e:
            logger.error(f"❌ Failed to update response schemas: {e}")
            return False
    
    def _remove_id_from_create_schemas(self, schema_names: List[str]) -> bool:
        """Remove 'id' field from Create schemas by restructuring inheritance using AST."""
        try:
            import ast
            
            content = self.schemas_file.read_text()
            
            # Parse to AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                logger.error(f"Failed to parse schemas.py: {e}")
                return False
            
            # Find all entity names (e.g., "Product", "Customer")
            # by looking for {Entity}Base classes
            entity_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if node.name.endswith('Base') and not node.name.endswith('BaseFields'):
                        # Extract entity name (e.g., "ProductBase" -> "Product")
                        entity_name = node.name[:-4]  # Remove "Base"
                        entity_names.add(entity_name)
            
            if not entity_names:
                logger.info("No entity Base classes found to restructure")
                return True
            
            # For each entity, restructure the schemas
            for entity_name in entity_names:
                base_class_name = f"{entity_name}Base"
                base_fields_class_name = f"{entity_name}BaseFields"
                create_class_name = f"{entity_name}Create"
                
                # Find the Base class
                base_class = None
                base_class_index = None
                for i, node in enumerate(tree.body):
                    if isinstance(node, ast.ClassDef) and node.name == base_class_name:
                        base_class = node
                        base_class_index = i
                        break
                
                if not base_class:
                    continue
                
                # Extract fields from Base class (excluding id, created_at, updated_at)
                server_fields = ['id', 'created_at', 'updated_at']
                client_fields = []
                server_field_nodes = []
                
                for item in base_class.body:
                    if isinstance(item, ast.AnnAssign):
                        field_name = item.target.id if isinstance(item.target, ast.Name) else None
                        if field_name:
                            if field_name in server_fields:
                                server_field_nodes.append(item)
                            else:
                                client_fields.append(item)
                
                # Only restructure if there are server fields to separate
                if not server_field_nodes:
                    continue
                
                # Create {Entity}BaseFields class with only client fields
                base_fields_class = ast.ClassDef(
                    name=base_fields_class_name,
                    bases=[ast.Name(id='BaseModel', ctx=ast.Load())],
                    keywords=[],
                    body=client_fields + [
                        ast.Expr(value=ast.Constant(value=f"Base fields for {entity_name.lower()}."))
                    ] if client_fields else [ast.Pass()],
                    decorator_list=[]
                )
                
                # Update {Entity}Base to inherit from BaseFields and add server fields
                base_class.bases = [ast.Name(id=base_fields_class_name, ctx=ast.Load())]
                base_class.body = server_field_nodes + [
                    item for item in base_class.body 
                    if not isinstance(item, ast.AnnAssign) or 
                    (isinstance(item.target, ast.Name) and item.target.id not in 
                     [f.target.id for f in client_fields if isinstance(f.target, ast.Name)])
                ]
                
                # Find and update {Entity}Create to inherit from BaseFields
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name == create_class_name:
                        node.bases = [ast.Name(id=base_fields_class_name, ctx=ast.Load())]
                        break
                
                # Insert BaseFields class before Base class
                tree.body.insert(base_class_index, base_fields_class)
            
            # Convert back to source code
            try:
                new_content = ast.unparse(tree)
                self.schemas_file.write_text(new_content)
                logger.info(f"✅ Restructured schema inheritance for {len(entity_names)} entities using AST")
                return True
            except Exception as e:
                logger.error(f"Failed to convert AST back to source: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Failed to restructure schema inheritance: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _add_jsonable_encoder_to_handlers(self) -> bool:
        """Add jsonable_encoder to exception handlers using AST parsing."""
        try:
            import ast
            
            content = self.exception_handlers_file.read_text()
            
            # Add import if missing
            if "from fastapi.encoders import jsonable_encoder" not in content:
                # Find the last fastapi import
                last_import = content.rfind("from fastapi")
                if last_import != -1:
                    # Find end of line
                    line_end = content.find("\n", last_import) + 1
                    content = content[:line_end] + "from fastapi.encoders import jsonable_encoder\n" + content[line_end:]
            
            # Parse to AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                logger.error(f"Failed to parse exception_handlers.py: {e}")
                return False
            
            # Track if we made any changes
            changes_made = False
            
            # Walk the AST and find all JSONResponse calls
            class JSONResponseWrapper(ast.NodeTransformer):
                def visit_Call(self, node):
                    # First, visit children
                    self.generic_visit(node)
                    
                    # Check if this is a JSONResponse call
                    is_json_response = False
                    if isinstance(node.func, ast.Name) and node.func.id == 'JSONResponse':
                        is_json_response = True
                    
                    if is_json_response:
                        # Find the 'content' keyword argument
                        for keyword in node.keywords:
                            if keyword.arg == 'content':
                                # Check if already wrapped with jsonable_encoder
                                if isinstance(keyword.value, ast.Call):
                                    if isinstance(keyword.value.func, ast.Name):
                                        if keyword.value.func.id == 'jsonable_encoder':
                                            # Already wrapped, skip
                                            continue
                                
                                # Wrap with jsonable_encoder
                                nonlocal changes_made
                                changes_made = True
                                
                                keyword.value = ast.Call(
                                    func=ast.Name(id='jsonable_encoder', ctx=ast.Load()),
                                    args=[keyword.value],
                                    keywords=[]
                                )
                    
                    return node
            
            # Apply the transformation
            transformer = JSONResponseWrapper()
            new_tree = transformer.visit(tree)
            
            if changes_made:
                # Convert back to source code using ast.unparse (Python 3.9+)
                try:
                    new_content = ast.unparse(new_tree)
                    self.exception_handlers_file.write_text(new_content)
                    logger.info("✅ Added jsonable_encoder to exception handlers using AST")
                    return True
                except Exception as e:
                    logger.error(f"Failed to convert AST back to source: {e}")
                    return False
            else:
                logger.info("✅ Exception handlers already use jsonable_encoder")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add jsonable_encoder to handlers: {e}")
            import traceback
            traceback.print_exc()
            return False

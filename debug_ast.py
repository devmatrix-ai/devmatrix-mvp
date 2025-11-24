import ast
import astor

def test_ast_modification():
    source_code = """
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

class OrderSchema(BaseModel):
    id: str
    payment_status: Literal["pending", "failed"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    other_field: int = Field(gt=0)
    simple_field: str = "default"
"""
    print("--- Original Code ---")
    print(source_code)

    tree = ast.parse(source_code)

    class SchemaModifier(ast.NodeTransformer):
        def visit_ClassDef(self, node):
            if node.name == "OrderSchema":
                for item in node.body:
                    if isinstance(item, ast.AnnAssign):
                        # targeted field: payment_status (Literal update)
                        if isinstance(item.target, ast.Name) and item.target.id == "payment_status":
                            print(f"Found field: {item.target.id}")
                            # Update Literal
                            new_values = ["pending", "simulated_ok", "failed"]
                            # Construct Literal[...]
                            # Python < 3.9: ast.Subscript(value=Name(id='Literal'), slice=Index(value=Tuple(...)))
                            # Python >= 3.9: ast.Subscript(value=Name(id='Literal'), slice=Tuple(...))
                            
                            # Create the tuple of strings
                            elts = [ast.Constant(value=v) for v in new_values]
                            slice_node = ast.Tuple(elts=elts, ctx=ast.Load())
                            
                            item.annotation = ast.Subscript(
                                value=ast.Name(id='Literal', ctx=ast.Load()),
                                slice=slice_node,
                                ctx=ast.Load()
                            )
                        
                        # targeted field: created_at (default_factory fix)
                        if isinstance(item.target, ast.Name) and item.target.id == "created_at":
                             print(f"Found field: {item.target.id}")
                             # Check if value is Call to Field
                             if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name) and item.value.func.id == 'Field':
                                 # Update default_factory to use actual attribute, not string
                                 # Remove existing default_factory kwarg
                                 item.value.keywords = [k for k in item.value.keywords if k.arg != 'default_factory']
                                 # Add new one: default_factory=uuid.uuid4
                                 item.value.keywords.append(
                                     ast.keyword(
                                         arg='default_factory',
                                         value=ast.Attribute(
                                             value=ast.Name(id='uuid', ctx=ast.Load()),
                                             attr='uuid4',
                                             ctx=ast.Load()
                                         )
                                     )
                                 )

                        # targeted field: simple_field (convert to Field)
                        if isinstance(item.target, ast.Name) and item.target.id == "simple_field":
                            print(f"Found field: {item.target.id}")
                            # Convert 'simple_field: str = "default"' to 'simple_field: str = Field(default="default", description="Added")'
                            if not isinstance(item.value, ast.Call):
                                old_default = item.value
                                item.value = ast.Call(
                                    func=ast.Name(id='Field', ctx=ast.Load()),
                                    args=[],
                                    keywords=[
                                        ast.keyword(arg='default', value=old_default),
                                        ast.keyword(arg='description', value=ast.Constant(value="Added via AST"))
                                    ]
                                )

            return node

    modifier = SchemaModifier()
    new_tree = modifier.visit(tree)
    ast.fix_missing_locations(new_tree)
    
    print("\n--- Modified Code ---")
    print(astor.to_source(new_tree))

if __name__ == "__main__":
    test_ast_modification()

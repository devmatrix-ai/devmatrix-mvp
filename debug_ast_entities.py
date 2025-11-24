import ast
import astor

def test_ast_entities_and_imports():
    source_code = """
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.core.database import Base
import uuid

class OrderEntity(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    email = Column(String(255), nullable=False)
"""
    print("--- Original Code ---")
    print(source_code)

    tree = ast.parse(source_code)

    class EntityModifier(ast.NodeTransformer):
        def visit_Module(self, node):
            # Check/Add imports
            has_uuid = any(isinstance(n, ast.Import) and any(alias.name == 'uuid' for alias in n.names) for n in node.body)
            if not has_uuid:
                print("Adding import uuid")
                node.body.insert(0, ast.Import(names=[ast.alias(name='uuid', asname=None)]))
            
            # Continue visiting children
            self.generic_visit(node)
            return node

        def visit_ClassDef(self, node):
            if node.name == "OrderEntity":
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        # Check targets
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                field_name = target.id
                                
                                # Handle customer_id (ForeignKey)
                                if field_name == 'customer_id':
                                    if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name) and item.value.func.id == 'Column':
                                        print(f"Found Column: {field_name}")
                                        # Check if ForeignKey exists in args
                                        has_fk = any(
                                            isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'ForeignKey'
                                            for arg in item.value.args
                                        )
                                        if not has_fk:
                                            print(f"Adding ForeignKey to {field_name}")
                                            # Add ForeignKey('customers.id')
                                            fk_node = ast.Call(
                                                func=ast.Name(id='ForeignKey', ctx=ast.Load()),
                                                args=[ast.Constant(value='customers.id')],
                                                keywords=[]
                                            )
                                            item.value.args.append(fk_node)

                                # Handle email (unique)
                                if field_name == 'email':
                                    if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name) and item.value.func.id == 'Column':
                                        print(f"Found Column: {field_name}")
                                        # Add unique=True keyword
                                        has_unique = any(k.arg == 'unique' for k in item.value.keywords)
                                        if not has_unique:
                                            print(f"Adding unique=True to {field_name}")
                                            item.value.keywords.append(ast.keyword(arg='unique', value=ast.Constant(value=True)))

            return node

    modifier = EntityModifier()
    new_tree = modifier.visit(tree)
    ast.fix_missing_locations(new_tree)
    
    print("\n--- Modified Code ---")
    print(astor.to_source(new_tree))

if __name__ == "__main__":
    test_ast_entities_and_imports()

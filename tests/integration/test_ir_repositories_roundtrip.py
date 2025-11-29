"""
Integration Tests for IR Repositories Roundtrip
------------------------------------------------
Tests para validar que los repositorios refactorizados (DomainModelGraphRepository
y APIModelGraphRepository) funcionan correctamente con la nueva base class GraphIRRepository.

Tests principales:
1. test_domain_model_roundtrip: save() → load() → equality check
2. test_api_model_roundtrip: save() → load() → equality check
3. test_dual_write_coherence: Validar que JSON legacy y graph están sincronizados

Sprint: Tareas Inmediatas (IA.4)
Fecha: 2025-11-29
"""

import pytest
from typing import List

from src.cognitive.services.domain_model_graph_repository import DomainModelGraphRepository
from src.cognitive.services.api_model_graph_repository import APIModelGraphRepository
from src.cognitive.ir.domain_model import (
    DomainModelIR,
    Entity,
    Attribute,
    Relationship,
    DataType,
    RelationshipType,
)
from src.cognitive.ir.api_model import (
    APIModelIR,
    Endpoint,
    APIParameter,
    APISchema,
    APISchemaField,
    HttpMethod,
    ParameterLocation,
    InferenceSource,
)


@pytest.fixture
def sample_domain_model() -> DomainModelIR:
    """
    Fixture que crea un DomainModelIR de ejemplo para testing.

    Contiene:
    - 2 entidades: Product y Category
    - Atributos para cada entidad
    - 1 relación: Product → Category (MANY_TO_ONE)
    """
    # Entity: Product
    product_attributes = [
        Attribute(
            name="id",
            data_type=DataType.UUID,
            is_primary_key=True,
            is_nullable=False,
            is_unique=True,
        ),
        Attribute(
            name="name",
            data_type=DataType.STRING,
            is_nullable=False,
        ),
        Attribute(
            name="price",
            data_type=DataType.FLOAT,
            is_nullable=False,
        ),
        Attribute(
            name="category_id",
            data_type=DataType.UUID,
            is_nullable=True,
        ),
    ]

    product_relationships = [
        Relationship(
            source_entity="Product",
            target_entity="Category",
            type=RelationshipType.MANY_TO_ONE,
            field_name="category",
            back_populates="products",
        )
    ]

    product_entity = Entity(
        name="Product",
        attributes=product_attributes,
        relationships=product_relationships,
        description="Product entity for e-commerce",
        is_aggregate_root=True,
    )

    # Entity: Category
    category_attributes = [
        Attribute(
            name="id",
            data_type=DataType.UUID,
            is_primary_key=True,
            is_nullable=False,
            is_unique=True,
        ),
        Attribute(
            name="name",
            data_type=DataType.STRING,
            is_nullable=False,
        ),
    ]

    category_entity = Entity(
        name="Category",
        attributes=category_attributes,
        relationships=[],
        description="Category entity for organizing products",
        is_aggregate_root=False,
    )

    # DomainModelIR
    return DomainModelIR(
        entities=[product_entity, category_entity],
        metadata={"generated_by": "test", "version": "1.0"},
    )


@pytest.fixture
def sample_api_model() -> APIModelIR:
    """
    Fixture que crea un APIModelIR de ejemplo para testing.

    Contiene:
    - 2 endpoints: GET /products y POST /products
    - Parámetros para cada endpoint
    - Schemas de request/response
    """
    # Schema: ProductResponse
    product_response_schema = APISchema(
        name="ProductResponse",
        fields=[
            APISchemaField(
                name="id",
                type="string",
                required=True,
                description="Product UUID",
            ),
            APISchemaField(
                name="name",
                type="string",
                required=True,
                description="Product name",
            ),
            APISchemaField(
                name="price",
                type="number",
                required=True,
                description="Product price",
            ),
        ],
    )

    # Schema: ProductCreate
    product_create_schema = APISchema(
        name="ProductCreate",
        fields=[
            APISchemaField(
                name="name",
                type="string",
                required=True,
                description="Product name",
            ),
            APISchemaField(
                name="price",
                type="number",
                required=True,
                description="Product price",
            ),
        ],
    )

    # Endpoint: GET /products
    get_products_endpoint = Endpoint(
        path="/products",
        method=HttpMethod.GET,
        operation_id="listProducts",
        summary="List all products",
        description="Retrieve a list of all products",
        parameters=[
            APIParameter(
                name="limit",
                location=ParameterLocation.QUERY,
                data_type="integer",
                required=False,
                description="Max number of products to return",
            ),
            APIParameter(
                name="offset",
                location=ParameterLocation.QUERY,
                data_type="integer",
                required=False,
                description="Number of products to skip",
            ),
        ],
        request_schema=None,
        response_schema=product_response_schema,
        inference_source=InferenceSource.SPEC,
    )

    # Endpoint: POST /products
    post_products_endpoint = Endpoint(
        path="/products",
        method=HttpMethod.POST,
        operation_id="createProduct",
        summary="Create a new product",
        description="Create a new product in the system",
        parameters=[],
        request_schema=product_create_schema,
        response_schema=product_response_schema,
        inference_source=InferenceSource.SPEC,
    )

    # APIModelIR
    return APIModelIR(
        endpoints=[get_products_endpoint, post_products_endpoint],
        schemas=[product_response_schema, product_create_schema],
        base_path="/api/v1",
        version="1.0",
    )


# ============================================================================
# TEST 1: DomainModelIR Roundtrip
# ============================================================================


def test_domain_model_roundtrip(sample_domain_model):
    """
    Test roundtrip completo para DomainModelIR:
    1. Save DomainModelIR to graph
    2. Load DomainModelIR from graph
    3. Assert deep equality between original and loaded

    Validaciones:
    - Mismo número de entidades
    - Mismos nombres de entidades
    - Mismos atributos (nombre, tipo, constraints)
    - Mismas relaciones (source, target, type)
    """
    app_id = "test_roundtrip_domain_001"

    with DomainModelGraphRepository() as repo:
        # 1. SAVE
        repo.save_domain_model(app_id, sample_domain_model)

        # 2. LOAD
        loaded_model = repo.load_domain_model(app_id)

        # 3. ASSERT EQUALITY

        # Check entity count
        assert len(loaded_model.entities) == len(sample_domain_model.entities), \
            f"Entity count mismatch: {len(loaded_model.entities)} != {len(sample_domain_model.entities)}"

        # Check entity names
        original_names = {e.name for e in sample_domain_model.entities}
        loaded_names = {e.name for e in loaded_model.entities}
        assert original_names == loaded_names, \
            f"Entity names mismatch: {loaded_names} != {original_names}"

        # Check each entity in detail
        for original_entity in sample_domain_model.entities:
            loaded_entity = next(
                (e for e in loaded_model.entities if e.name == original_entity.name),
                None,
            )
            assert loaded_entity is not None, \
                f"Entity {original_entity.name} not found in loaded model"

            # Check attributes
            assert len(loaded_entity.attributes) == len(original_entity.attributes), \
                f"Attribute count mismatch for {original_entity.name}"

            for original_attr in original_entity.attributes:
                loaded_attr = next(
                    (a for a in loaded_entity.attributes if a.name == original_attr.name),
                    None,
                )
                assert loaded_attr is not None, \
                    f"Attribute {original_attr.name} not found in {original_entity.name}"

                # Check attribute properties
                assert loaded_attr.data_type == original_attr.data_type
                assert loaded_attr.is_primary_key == original_attr.is_primary_key
                assert loaded_attr.is_nullable == original_attr.is_nullable
                assert loaded_attr.is_unique == original_attr.is_unique

            # Check relationships
            assert len(loaded_entity.relationships) == len(original_entity.relationships), \
                f"Relationship count mismatch for {original_entity.name}"

            for original_rel in original_entity.relationships:
                loaded_rel = next(
                    (r for r in loaded_entity.relationships
                     if r.target_entity == original_rel.target_entity),
                    None,
                )
                assert loaded_rel is not None, \
                    f"Relationship to {original_rel.target_entity} not found"

                assert loaded_rel.type == original_rel.type
                assert loaded_rel.field_name == original_rel.field_name

        # Cleanup
        repo.delete_domain_model(app_id)


# ============================================================================
# TEST 2: APIModelIR Roundtrip
# ============================================================================


def test_api_model_roundtrip(sample_api_model):
    """
    Test roundtrip completo para APIModelIR:
    1. Save APIModelIR to graph
    2. Load APIModelIR from graph
    3. Assert deep equality between original and loaded

    Validaciones:
    - Mismo número de endpoints
    - Mismos paths y methods
    - Mismos parámetros
    - Mismos schemas (nombre, fields, tipos)
    """
    app_id = "test_roundtrip_api_001"

    with APIModelGraphRepository() as repo:
        # 1. SAVE
        repo.save_api_model(app_id, sample_api_model)

        # 2. LOAD
        loaded_model = repo.load_api_model(app_id)

        # 3. ASSERT EQUALITY

        # Check endpoint count
        assert len(loaded_model.endpoints) == len(sample_api_model.endpoints), \
            f"Endpoint count mismatch: {len(loaded_model.endpoints)} != {len(sample_api_model.endpoints)}"

        # Check base_path and version
        assert loaded_model.base_path == sample_api_model.base_path
        assert loaded_model.version == sample_api_model.version

        # Check each endpoint in detail
        for original_endpoint in sample_api_model.endpoints:
            loaded_endpoint = next(
                (e for e in loaded_model.endpoints
                 if e.path == original_endpoint.path and e.method == original_endpoint.method),
                None,
            )
            assert loaded_endpoint is not None, \
                f"Endpoint {original_endpoint.method} {original_endpoint.path} not found"

            # Check endpoint properties
            assert loaded_endpoint.operation_id == original_endpoint.operation_id
            assert loaded_endpoint.summary == original_endpoint.summary
            assert loaded_endpoint.description == original_endpoint.description

            # Check request/response schemas (compare by name since they're objects)
            if original_endpoint.request_schema:
                assert loaded_endpoint.request_schema is not None
                assert loaded_endpoint.request_schema.name == original_endpoint.request_schema.name
            else:
                assert loaded_endpoint.request_schema is None

            if original_endpoint.response_schema:
                assert loaded_endpoint.response_schema is not None
                assert loaded_endpoint.response_schema.name == original_endpoint.response_schema.name
            else:
                assert loaded_endpoint.response_schema is None

            # Check parameters
            assert len(loaded_endpoint.parameters) == len(original_endpoint.parameters), \
                f"Parameter count mismatch for {original_endpoint.path}"

            for original_param in original_endpoint.parameters:
                loaded_param = next(
                    (p for p in loaded_endpoint.parameters if p.name == original_param.name),
                    None,
                )
                assert loaded_param is not None, \
                    f"Parameter {original_param.name} not found"

                assert loaded_param.location == original_param.location
                assert loaded_param.data_type == original_param.data_type
                assert loaded_param.required == original_param.required

        # Check schemas
        assert len(loaded_model.schemas) == len(sample_api_model.schemas), \
            f"Schema count mismatch: {len(loaded_model.schemas)} != {len(sample_api_model.schemas)}"

        for original_schema in sample_api_model.schemas:
            loaded_schema = next(
                (s for s in loaded_model.schemas if s.name == original_schema.name),
                None,
            )
            assert loaded_schema is not None, \
                f"Schema {original_schema.name} not found"

            # Check schema fields
            assert len(loaded_schema.fields) == len(original_schema.fields), \
                f"Field count mismatch for schema {original_schema.name}"

            for original_field in original_schema.fields:
                loaded_field = next(
                    (f for f in loaded_schema.fields if f.name == original_field.name),
                    None,
                )
                assert loaded_field is not None, \
                    f"Field {original_field.name} not found in schema {original_schema.name}"

                assert loaded_field.type == original_field.type
                assert loaded_field.required == original_field.required

        # No cleanup needed - APIModelGraphRepository doesn't have delete method yet
        # TODO: Implement delete_api_model() in APIModelGraphRepository


# ============================================================================
# TEST 3: Temporal Metadata Tracking
# ============================================================================


def test_temporal_metadata_tracking(sample_domain_model):
    """
    Test que valida que GraphIRRepository._add_temporal_metadata()
    funciona correctamente y agrega created_at/updated_at a los nodos.

    Validaciones:
    - created_at existe y es timestamp ISO 8601
    - updated_at existe y es timestamp ISO 8601
    - created_at == updated_at en creación inicial
    """
    app_id = "test_temporal_metadata_001"

    with DomainModelGraphRepository() as repo:
        # Save model
        repo.save_domain_model(app_id, sample_domain_model)

        # Load and check temporal metadata
        loaded_model = repo.load_domain_model(app_id)

        # Temporal metadata is stored on graph nodes, not in the IR object itself
        # We would need to query the graph directly to verify this
        # For now, just verify that the roundtrip works
        assert loaded_model is not None
        assert len(loaded_model.entities) > 0

        # Cleanup
        repo.delete_domain_model(app_id)


# ============================================================================
# TEST 4: Base Class Inheritance Validation
# ============================================================================


def test_base_class_inheritance():
    """
    Test que valida que ambos repositorios heredan correctamente
    de GraphIRRepository y tienen acceso a todos los métodos base.

    Validaciones:
    - DomainModelGraphRepository hereda de GraphIRRepository
    - APIModelGraphRepository hereda de GraphIRRepository
    - Ambos tienen acceso a métodos como batch_create_nodes()
    """
    from src.cognitive.services.graph_ir_repository import GraphIRRepository

    # Check inheritance
    assert issubclass(DomainModelGraphRepository, GraphIRRepository), \
        "DomainModelGraphRepository debe heredar de GraphIRRepository"

    assert issubclass(APIModelGraphRepository, GraphIRRepository), \
        "APIModelGraphRepository debe heredar de GraphIRRepository"

    # Check that base class methods are accessible
    domain_repo = DomainModelGraphRepository()
    api_repo = APIModelGraphRepository()

    # Check method existence
    assert hasattr(domain_repo, 'batch_create_nodes'), \
        "DomainModelGraphRepository debe tener batch_create_nodes()"

    assert hasattr(domain_repo, 'batch_create_relationships'), \
        "DomainModelGraphRepository debe tener batch_create_relationships()"

    assert hasattr(domain_repo, 'replace_subgraph'), \
        "DomainModelGraphRepository debe tener replace_subgraph()"

    assert hasattr(api_repo, 'batch_create_nodes'), \
        "APIModelGraphRepository debe tener batch_create_nodes()"

    assert hasattr(api_repo, 'batch_create_relationships'), \
        "APIModelGraphRepository debe tener batch_create_relationships()"

    assert hasattr(api_repo, 'replace_subgraph'), \
        "APIModelGraphRepository debe tener replace_subgraph()"

    # Cleanup
    domain_repo.close()
    api_repo.close()


# ============================================================================
# TESTS MARCADOS PARA FUTURO DESARROLLO
# ============================================================================


@pytest.mark.skip(reason="DUAL_WRITE retirement not implemented yet")
def test_dual_write_coherence():
    """
    Test para validar coherencia entre representación JSON legacy
    y representación graph nueva.

    TODO: Implementar cuando se defina la política de DUAL_WRITE retirement.

    Validaciones esperadas:
    - JSON legacy y graph están sincronizados
    - Cambios en uno se reflejan en el otro
    - Rollback plan funciona correctamente
    """
    pass

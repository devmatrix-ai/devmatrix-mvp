"""
Integration Tests for FullIRGraphLoader
----------------------------------------
Tests para validar que el FullIRGraphLoader carga correctamente
el grafo completo de ApplicationIR desde Neo4j.

Tests principales:
1. test_load_full_ir: Carga completa de ApplicationIR
2. test_load_stats: Verificar estadísticas de carga
3. test_cache_functionality: Verificar cache hit/miss
4. test_get_app_ids: Listar todas las aplicaciones

Sprint: Sprint 6 - FullIRGraphLoader
Fecha: 2025-11-29
"""

import pytest
from typing import Optional

from src.cognitive.services.full_ir_graph_loader import (
    FullIRGraphLoader,
    FullIRGraphLoadResult,
)
from src.cognitive.ir.application_ir import ApplicationIR


@pytest.fixture
def loader():
    """
    Fixture que crea un FullIRGraphLoader para testing.
    """
    loader = FullIRGraphLoader()
    yield loader
    loader.close()


class TestFullIRGraphLoader:
    """
    Tests de integración para FullIRGraphLoader.
    """

    def test_get_app_ids(self, loader: FullIRGraphLoader):
        """
        Verifica que get_app_ids retorna lista de app_ids.
        """
        app_ids = loader.get_app_ids()

        # Should return a list (possibly empty if no apps)
        assert isinstance(app_ids, list)

        # If there are apps, they should be strings
        for app_id in app_ids:
            assert isinstance(app_id, str)

        print(f"✅ Found {len(app_ids)} ApplicationIR records")

    def test_get_load_stats(self, loader: FullIRGraphLoader):
        """
        Verifica que get_load_stats retorna estadísticas.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]
        stats = loader.get_load_stats(app_id)

        # Should return stats dict
        assert isinstance(stats, dict)
        assert "entities" in stats
        assert "endpoints" in stats
        assert "flows" in stats
        assert "has_domain_model" in stats
        assert "has_api_model" in stats

        print(f"✅ Stats for {app_id}:")
        print(f"   Entities: {stats['entities']}")
        print(f"   Endpoints: {stats['endpoints']}")
        print(f"   Flows: {stats['flows']}")
        print(f"   Has Domain Model: {stats['has_domain_model']}")
        print(f"   Has API Model: {stats['has_api_model']}")

    def test_load_full_ir(self, loader: FullIRGraphLoader):
        """
        Verifica que load_full_ir carga ApplicationIR completo.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Load full IR
        result = loader.load_full_ir(app_id, include_tests=True, use_cache=False)

        # Verify result structure
        assert isinstance(result, FullIRGraphLoadResult)
        assert isinstance(result.application_ir, ApplicationIR)
        assert result.load_time_ms > 0
        assert result.cache_hit is False

        app_ir = result.application_ir

        # Verify app_id matches
        assert str(app_ir.app_id) == app_id

        # Verify submodels exist (may be empty but should not be None)
        assert app_ir.domain_model is not None
        assert app_ir.api_model is not None
        assert app_ir.infrastructure_model is not None

        print(f"✅ Loaded ApplicationIR {app_id} in {result.load_time_ms:.2f}ms")
        print(f"   Nodes loaded: {result.nodes_loaded}")
        print(f"   Relationships loaded: {result.relationships_loaded}")

        if app_ir.domain_model:
            print(f"   Entities: {len(app_ir.domain_model.entities)}")
        if app_ir.api_model:
            print(f"   Endpoints: {len(app_ir.api_model.endpoints)}")
        if app_ir.behavior_model:
            print(f"   Flows: {len(app_ir.behavior_model.flows)}")

    def test_cache_functionality(self, loader: FullIRGraphLoader):
        """
        Verifica que el cache funciona correctamente.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Clear cache first
        loader.invalidate_cache(app_id)

        # First load - should not hit cache
        result1 = loader.load_full_ir(app_id, use_cache=True)
        assert result1.cache_hit is False, "First load should not hit cache"

        # Second load - should hit cache
        result2 = loader.load_full_ir(app_id, use_cache=True)
        assert result2.cache_hit is True, "Second load should hit cache"

        # Verify cached IR is same
        assert str(result1.application_ir.app_id) == str(result2.application_ir.app_id)

        # Third load without cache - should not hit cache
        result3 = loader.load_full_ir(app_id, use_cache=False)
        assert result3.cache_hit is False, "Load without cache should not hit"

        print(f"✅ Cache functionality verified:")
        print(f"   First load: {result1.load_time_ms:.2f}ms (cache_hit={result1.cache_hit})")
        print(f"   Second load: {result2.load_time_ms:.2f}ms (cache_hit={result2.cache_hit})")
        print(f"   Third load (no cache): {result3.load_time_ms:.2f}ms (cache_hit={result3.cache_hit})")

    def test_exists(self, loader: FullIRGraphLoader):
        """
        Verifica que exists() funciona correctamente.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        # Existing app should return True
        assert loader.exists(app_ids[0]) is True

        # Non-existing app should return False
        assert loader.exists("non-existing-app-id-xyz") is False

        print(f"✅ exists() function works correctly")

    def test_load_without_tests(self, loader: FullIRGraphLoader):
        """
        Verifica que load_full_ir funciona sin cargar tests.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Load without tests
        result = loader.load_full_ir(app_id, include_tests=False, use_cache=False)

        assert isinstance(result, FullIRGraphLoadResult)
        assert result.metadata.get("include_tests") is False

        print(f"✅ Loaded ApplicationIR without tests in {result.load_time_ms:.2f}ms")

    def test_load_non_existing_app(self, loader: FullIRGraphLoader):
        """
        Verifica que load_full_ir lanza error para app inexistente.
        """
        with pytest.raises(ValueError) as exc_info:
            loader.load_full_ir("non-existing-app-id-xyz")

        assert "not found" in str(exc_info.value).lower()

        print(f"✅ Correctly raises error for non-existing app")

    def test_invalidate_cache(self, loader: FullIRGraphLoader):
        """
        Verifica que invalidate_cache funciona.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Load to populate cache
        loader.load_full_ir(app_id, use_cache=True)

        # Invalidate specific app
        loader.invalidate_cache(app_id)

        # Should not hit cache now
        result = loader.load_full_ir(app_id, use_cache=True)
        assert result.cache_hit is False

        # Populate again
        loader.load_full_ir(app_id, use_cache=True)

        # Invalidate all
        loader.invalidate_cache()

        # Should not hit cache now
        result = loader.load_full_ir(app_id, use_cache=True)
        assert result.cache_hit is False

        print(f"✅ Cache invalidation works correctly")


class TestFullIRGraphLoaderPerformance:
    """
    Tests de performance para FullIRGraphLoader.
    """

    def test_load_time_acceptable(self, loader: FullIRGraphLoader):
        """
        Verifica que el tiempo de carga está dentro de límites aceptables.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Clear cache
        loader.invalidate_cache(app_id)

        # Load and measure time
        result = loader.load_full_ir(app_id, use_cache=False)

        # Should complete in reasonable time (< 5 seconds)
        # This is a sanity check - actual time depends on data size
        assert result.load_time_ms < 5000, f"Load time too slow: {result.load_time_ms}ms"

        print(f"✅ Load time acceptable: {result.load_time_ms:.2f}ms")

    def test_multiple_loads_consistent(self, loader: FullIRGraphLoader):
        """
        Verifica que múltiples cargas retornan resultados consistentes.
        """
        app_ids = loader.get_app_ids()

        if not app_ids:
            pytest.skip("No ApplicationIR records found in database")

        app_id = app_ids[0]

        # Load multiple times
        results = []
        for _ in range(3):
            loader.invalidate_cache(app_id)
            result = loader.load_full_ir(app_id, use_cache=False)
            results.append(result)

        # All results should have same app_id
        app_ids_loaded = [str(r.application_ir.app_id) for r in results]
        assert all(aid == app_id for aid in app_ids_loaded)

        # All results should have similar node counts
        node_counts = [r.nodes_loaded for r in results]
        assert len(set(node_counts)) <= 1, "Node counts should be consistent"

        print(f"✅ Multiple loads are consistent")
        print(f"   Load times: {[f'{r.load_time_ms:.2f}ms' for r in results]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

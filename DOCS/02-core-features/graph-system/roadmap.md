## Roadmap: Graph Improvements (sin Neo4j)

### Objetivos
- Mejorar calidad y utilidad del grafo de dependencias para planificación, impacto, RAG y observabilidad sin agregar nueva infraestructura.
- Reducir tiempos de recomputo y latencias de consulta.
- Exponer APIs de consulta clave con caché.

### Alcance
- Precisión de dependencias, incrementalidad por diffs, persistencia SQL, precálculo/caché, APIs, planificación avanzada, integración con RAG, métricas y dashboard.

### Arquitectura (alto nivel)
- Cómputo en memoria con NetworkX para construcción, olas y métricas ligeras.
- Persistencia en SQL (PostgreSQL): nodos (átomos) y aristas (dependencias) con índices.
- Precálculos batch y cachés (in-memory/Redis) para consultas de baja latencia.
- APIs REST para neighborhood/impact/path corto/metrics.
- Integración RAG: boost por proximidad en grafo durante ranking.

### Workstreams

- Detección de dependencias
  - Tree-sitter por lenguaje (Python, TS/JS, Go).
  - Extracción: imports, defs, calls, def-use básico, tipos.
  - Normalización de símbolos (qualified names), desambiguación por scope.
  - Pesos y confianza por arista (evidencia múltiple).
  - Archivos: `src/dependency/graph_builder.py` (+ helpers por lenguaje).
  - Entregables: `_extract_symbols`, `_detect_dependencies`, tests unitarios por lenguaje.

- Incrementalidad por diffs de Git
  - Identificar archivos cambiados, átomos afectados y vecinos (k=1) para recomputo local.
  - Invalidación de aristas incidentes y recalculo parcial.
  - CLI/job: `graph update --since <commit>` y job post-commit en CI.
  - Archivos: `src/dependency/graph_incremental.py`, CLI en `scripts/`.
  - Métrica: % de recomputo evitado, tiempo ahorrado.

- Persistencia SQL y precálculo
  - Tablas:
    - `graph_atoms(id UUID PK, workspace_id TEXT, file_path TEXT, name TEXT, language TEXT, loc INT, complexity FLOAT, updated_at TIMESTAMP)`
    - `graph_edges(src_id UUID, dst_id UUID, type TEXT, weight FLOAT, workspace_id TEXT, PRIMARY KEY(src_id, dst_id))`
  - Índices: `graph_edges(src_id)`, `graph_edges(dst_id)`, compuestos por `workspace_id`.
  - Precálculos:
    - Orden topológico por workspace.
    - Fan-in/out por átomo.
    - Neighborhood k-hop (k≤3) cacheable.
  - Archivos: migraciones SQL, `src/repositories/graph_repo.py`.

- APIs de consulta (con caché)
  - `GET /graph/{workspace}/neighbors?id=<atom_id>&k=2`
  - `GET /graph/{workspace}/impact?id=<atom_id>` (dependents afectados)
  - `GET /graph/{workspace}/path?src=<id>&dst=<id>&k_max=4`
  - `GET /graph/{workspace}/metrics`
  - Caching: Redis/in-memory, TTL 5–30 min, keys por workspace+query.
  - Archivos: `src/api/routers/graph.py`, `src/services/graph_query_service.py`.

- Planificación y ejecución (olas)
  - Topological waves con límites de paralelismo ajustados por riesgo (complejidad, fan-in/out).
  - Replanificación local ante fallas de nodo (bloquear, recalcular subgrafo dependiente).
  - Archivos: `src/services/dependency_service.py` (plan), `src/services/execution_planner.py`.

- Integración RAG-aware
  - `graph_proximity_score`: k-hop inverso (dependencias entrantes) y PageRank local precalculado.
  - En `Retriever`: sumar `alpha * graph_proximity_score` al score final (configurable).
  - Archivos: `src/rag/retriever.py`, `src/rag/reranker.py` (toggle/boost), `src/graph/metrics.py`.

- Observabilidad y dashboard
  - Métricas: tiempo de build full/incremental, % incremental, latencias API, tamaños subgrafos, fallas por ola.
  - Panel: hotspots (fan-in/out altos), distribución de olas, tareas fallidas por ola.
  - Archivos: `src/observability/metrics.py`, `DOCS/rag/dashboard.md` (actualización).

### Plan por fases

- Fase 1 (1–2 semanas)
  - Incrementalidad por diffs (MVP).
  - Persistencia SQL + índices.
  - Endpoints `neighbors` e `impact` con caché.
  - Métricas básicas + actualización de dashboard.
  - KPI: -70% tiempo de recomputo en cambios parciales; P95 API < 50 ms.

- Fase 2 (1–2 semanas)
  - Tree-sitter + mejores dependencias (Python + 1 lenguaje extra).
  - Precálculos: topological order, fan-in/out, k-hop (≤3).
  - Plan de olas con límites de paralelismo por riesgo.
  - KPI: reducción de bloqueos; mejor distribución de olas.

- Fase 3 (1 semana)
  - RAG graph-boost (scoring híbrido).
  - `path` corto (k_max≤4) con caché.
  - Métricas extendidas (hotspots, fallas por ola).
  - KPI: mejora en relevancia RAG (CTR/aceptación interna).

### APIs (especificación breve)

- Neighbors
  - Request: `GET /graph/{workspace}/neighbors?id=<uuid>&k=2`
  - Response: `{ node: {...}, neighbors: [{id, type, weight}], depth: 2 }`

- Impact
  - Request: `GET /graph/{workspace}/impact?id=<uuid>`
  - Response: `{ affected: [<uuid>], count: N }`

- Path (k corto)
  - Request: `GET /graph/{workspace}/path?src=<uuid>&dst=<uuid>&k_max=4`
  - Response: `{ paths: [[uuid,...]], limited: true }`

- Metrics
  - Request: `GET /graph/{workspace}/metrics`
  - Response: `{ topo_waves: N, fan_in_top: [...], fan_out_top: [...], size: {nodes, edges} }`

### Esquema SQL (borrador)
- `graph_atoms(id, workspace_id, file_path, name, language, loc, complexity, updated_at)`
- `graph_edges(src_id, dst_id, type, weight, workspace_id)`
- Índices: `graph_edges_src_idx`, `graph_edges_dst_idx`, `graph_atoms_ws_idx`

### Testing
- Unit tests: extracción de símbolos y detección de dependencias por lenguaje; incrementalidad con fixtures de diffs.
- Integración: endpoints con datos de ejemplo, caché y auth si aplica.
- Performance: benchmarks de recomputo incremental vs full; latencias API con y sin caché.

### Riesgos y mitigaciones
- Costo de AST por lenguaje → cache por archivo y hashing de contenido.
- Falsos positivos en dependencias → pesos/umbrales y evidencias múltiples.
- Cache staleness → invalidación por workspace+commit y TTL corto.

### Entregables clave
- Módulos: `graph_incremental.py`, `graph_repo.py`, `graph_query_service.py`, `execution_planner.py`, `graph/metrics.py`.
- Endpoints: neighbors, impact, path, metrics.
- Migraciones SQL e índices.
- Documentación y dashboard actualizado.

### Métricas de éxito
- Build incremental: -70–90% tiempo vs full.
- APIs P95 < 50 ms (cache hit), < 250 ms (miss).
- Mejora en ranking RAG (offline eval A/B con ground truth interno).



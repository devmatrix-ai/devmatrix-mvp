# DevMatrix RAG System: Guía Completa de Implementación

## 🎯 Objetivo

Implementar un sistema RAG (Retrieval-Augmented Generation) en DevMatrix MVP para:
- **Mejorar precisión**: 70-80% → 90%+ 
- **Acelerar generación**: Reutilizar patrones probados
- **Reducir errores**: Aprender de código exitoso
- **Timeline**: 2-4 semanas de implementación

---

## 🏗️ Arquitectura RAG para DevMatrix

### Sistema Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVMATRIX RAG SYSTEM                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Code Generated  │────▶│  Embedding       │────▶│ Vector Store │
│  (Human Approved)│     │  Pipeline        │     │  (ChromaDB)  │
└──────────────────┘     └──────────────────┘     └──────────────┘
                                                           │
                         ┌─────────────────────────────────┘
                         │
                         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  User Request    │────▶│  Query Embedding │────▶│   Retrieval  │
│  (New Task)      │     │                  │     │  (Top K=5)   │
└──────────────────┘     └──────────────────┘     └──────────────┘
                                                           │
                         ┌─────────────────────────────────┘
                         │
                         ▼
                    ┌──────────────────┐
                    │  Context Builder │
                    │  • Similar code  │
                    │  • Templates     │
                    │  • Best practices│
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Agent Prompts   │
                    │  + RAG Context   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Code Generation │
                    │  (with examples) │
                    └──────────────────┘
```

---

## 📦 Stack Tecnológico Recomendado

### Opción 1: ChromaDB (Recomendado para MVP)

**✅ Pros:**
- Open source y gratuito
- Embedding automático incluido
- Fácil setup (pip install)
- Persistencia local
- No requiere API keys extra
- Perfecto para MVP

**❌ Cons:**
- Sin hosting cloud nativo (pero se puede deployar)
- Menos features enterprise

```bash
pip install chromadb
```

### Opción 2: Pinecone (Para producción a escala)

**✅ Pros:**
- Cloud-native
- Escalabilidad automática
- Alta disponibilidad
- APIs robustas

**❌ Cons:**
- De pago ($70/mes mínimo)
- Requiere API key
- Más complejo

### Opción 3: Weaviate (Alternativa enterprise)

**✅ Pros:**
- Muy potente
- Multi-modal
- GraphQL API

**❌ Cons:**
- Curva de aprendizaje
- Más infra

### **Recomendación para DevMatrix MVP: ChromaDB**

Razón: Gratis, rápido, suficiente para 10K-100K documentos.

---

## 🔧 Implementación Paso a Paso

### Fase 1: Setup Básico (Día 1-2)

#### 1.1. Instalación de dependencias

```bash
# En tu requirements.txt
chromadb==0.4.22
sentence-transformers==2.3.1
langchain-community==0.0.20
```

```bash
pip install -r requirements.txt
```

#### 1.2. Estructura de archivos nueva

```
src/
├── rag/
│   ├── __init__.py
│   ├── vector_store.py      # ChromaDB wrapper
│   ├── embeddings.py         # Embedding service
│   ├── indexer.py            # Indexa código aprobado
│   ├── retriever.py          # Busca ejemplos relevantes
│   └── context_builder.py    # Construye contexto para prompts
├── agents/
│   ├── orchestrator_agent.py  # MODIFICAR: agregar RAG
│   ├── implementation_agent.py # MODIFICAR: agregar RAG
│   └── ...
└── services/
    └── feedback_service.py    # NUEVO: captura código aprobado
```

---

### Fase 2: Vector Store Setup (Día 2-3)

#### 2.1. Vector Store Manager

```python
# src/rag/vector_store.py

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os

class DevMatrixVectorStore:
    """
    ChromaDB vector store para DevMatrix.
    Almacena código generado y aprobado para RAG.
    """
    
    def __init__(self, persist_directory: str = "./data/chroma_db"):
        """
        Inicializa ChromaDB con persistencia local.
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Configurar ChromaDB con persistencia
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        
        # Colecciones por tipo de código
        self.collections = {
            'code_snippets': self._get_or_create_collection('code_snippets'),
            'templates': self._get_or_create_collection('templates'),
            'patterns': self._get_or_create_collection('patterns'),
            'architectures': self._get_or_create_collection('architectures')
        }
    
    def _get_or_create_collection(self, name: str):
        """
        Obtiene o crea una colección.
        ChromaDB usa sentence-transformers por defecto.
        """
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}  # Similitud coseno
        )
    
    def add_code_snippet(
        self,
        code: str,
        metadata: Dict,
        collection_name: str = 'code_snippets'
    ) -> str:
        """
        Agrega un snippet de código al vector store.
        
        Args:
            code: El código fuente
            metadata: {
                'task_type': 'backend' | 'frontend' | 'database' | ...,
                'language': 'python' | 'javascript' | 'typescript' | ...,
                'framework': 'fastapi' | 'react' | 'django' | ...,
                'quality_score': float (0-10),
                'approved': bool,
                'created_at': timestamp,
                'file_path': str,
                'project_id': str,
                'tags': List[str]
            }
        
        Returns:
            ID del documento insertado
        """
        collection = self.collections[collection_name]
        
        # Generar ID único
        doc_id = f"{metadata['project_id']}_{metadata['task_type']}_{hash(code)}"
        
        # ChromaDB embeddings automáticos
        collection.add(
            documents=[code],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return doc_id
    
    def search_similar(
        self,
        query: str,
        collection_name: str = 'code_snippets',
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Busca código similar usando embeddings.
        
        Args:
            query: Descripción de lo que se busca
            collection_name: Colección donde buscar
            n_results: Número de resultados
            where: Filtros metadata (ej: {'language': 'python'})
        
        Returns:
            Lista de resultados con código y metadata
        """
        collection = self.collections[collection_name]
        
        # Búsqueda semántica
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where  # Filtrado por metadata
        )
        
        # Formatear resultados
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'code': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def get_by_filters(
        self,
        filters: Dict,
        collection_name: str = 'code_snippets',
        limit: int = 10
    ) -> List[Dict]:
        """
        Obtiene documentos por filtros exactos.
        
        Ejemplo:
            filters = {
                'task_type': 'backend',
                'language': 'python',
                'quality_score': {'$gte': 8.0}
            }
        """
        collection = self.collections[collection_name]
        
        results = collection.get(
            where=filters,
            limit=limit
        )
        
        formatted = []
        for i in range(len(results['ids'])):
            formatted.append({
                'id': results['ids'][i],
                'code': results['documents'][i],
                'metadata': results['metadatas'][i]
            })
        
        return formatted
    
    def update_metadata(
        self,
        doc_id: str,
        metadata_updates: Dict,
        collection_name: str = 'code_snippets'
    ):
        """
        Actualiza metadata de un documento.
        Útil para actualizar quality_score después de uso.
        """
        collection = self.collections[collection_name]
        
        # Obtener metadata actual
        current = collection.get(ids=[doc_id])
        if not current['ids']:
            raise ValueError(f"Document {doc_id} not found")
        
        # Merge metadata
        current_meta = current['metadatas'][0]
        updated_meta = {**current_meta, **metadata_updates}
        
        # Update
        collection.update(
            ids=[doc_id],
            metadatas=[updated_meta]
        )
    
    def delete_low_quality(
        self,
        min_quality_score: float = 5.0,
        collection_name: str = 'code_snippets'
    ) -> int:
        """
        Limpia código de baja calidad.
        """
        collection = self.collections[collection_name]
        
        # Buscar documentos con score bajo
        low_quality = collection.get(
            where={'quality_score': {'$lt': min_quality_score}}
        )
        
        if low_quality['ids']:
            collection.delete(ids=low_quality['ids'])
            return len(low_quality['ids'])
        
        return 0
    
    def get_stats(self) -> Dict:
        """
        Estadísticas del vector store.
        """
        stats = {}
        for name, collection in self.collections.items():
            count = collection.count()
            stats[name] = {
                'count': count,
                'name': name
            }
        
        return stats
```

#### 2.2. Test del Vector Store

```python
# tests/test_vector_store.py

import pytest
from src.rag.vector_store import DevMatrixVectorStore

def test_vector_store_basic():
    """Test básico de vector store"""
    store = DevMatrixVectorStore(persist_directory="./test_chroma_db")
    
    # Agregar código de prueba
    code_1 = """
def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
"""
    
    metadata_1 = {
        'task_type': 'backend',
        'language': 'python',
        'framework': 'none',
        'quality_score': 8.5,
        'approved': True,
        'created_at': '2025-01-15',
        'file_path': 'utils/math.py',
        'project_id': 'test_project_1',
        'tags': ['recursion', 'fibonacci', 'algorithm']
    }
    
    doc_id = store.add_code_snippet(code_1, metadata_1)
    assert doc_id is not None
    
    # Buscar similar
    results = store.search_similar(
        query="function to calculate fibonacci numbers",
        n_results=1
    )
    
    assert len(results) == 1
    assert 'fibonacci' in results[0]['code'].lower()
    assert results[0]['metadata']['quality_score'] == 8.5
    
    print("✅ Vector store test passed!")

if __name__ == '__main__':
    test_vector_store_basic()
```

---

### Fase 3: Indexer - Captura de Código Aprobado (Día 3-4)

#### 3.1. Feedback Service

```python
# src/services/feedback_service.py

from typing import Dict, Optional
from src.rag.vector_store import DevMatrixVectorStore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FeedbackService:
    """
    Servicio que captura código aprobado por humanos
    y lo indexa en el vector store para RAG.
    """
    
    def __init__(self, vector_store: DevMatrixVectorStore):
        self.vector_store = vector_store
    
    async def on_code_approved(
        self,
        code: str,
        task_metadata: Dict,
        quality_score: float,
        user_feedback: Optional[str] = None
    ):
        """
        Callback cuando el usuario aprueba código.
        
        Este método se llama desde el approval flow existente.
        """
        try:
            # Construir metadata completa
            metadata = {
                'task_type': task_metadata.get('task_type', 'general'),
                'language': self._detect_language(code),
                'framework': task_metadata.get('framework', 'unknown'),
                'quality_score': quality_score,
                'approved': True,
                'created_at': datetime.now().isoformat(),
                'file_path': task_metadata.get('file_path', 'unknown'),
                'project_id': task_metadata.get('project_id', 'unknown'),
                'tags': self._extract_tags(code, task_metadata),
                'user_feedback': user_feedback,
                'agent_used': task_metadata.get('agent_type', 'unknown')
            }
            
            # Indexar en vector store
            doc_id = self.vector_store.add_code_snippet(
                code=code,
                metadata=metadata,
                collection_name='code_snippets'
            )
            
            logger.info(f"✅ Código aprobado indexado: {doc_id}")
            
            # Si es un patrón reutilizable, también indexar en 'patterns'
            if self._is_reusable_pattern(code, metadata):
                self.vector_store.add_code_snippet(
                    code=code,
                    metadata=metadata,
                    collection_name='patterns'
                )
                logger.info(f"✅ Patrón reutilizable detectado e indexado")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Error indexando código aprobado: {e}")
            # No fallar el flujo principal si falla RAG
            return None
    
    async def on_code_rejected(
        self,
        code: str,
        reason: str,
        task_metadata: Dict
    ):
        """
        Callback cuando el usuario rechaza código.
        Útil para aprender qué NO hacer.
        """
        # TODO: Implementar negative examples
        # Por ahora, solo loggear
        logger.info(f"❌ Código rechazado: {reason[:100]}...")
    
    def _detect_language(self, code: str) -> str:
        """
        Detecta lenguaje de programación por heurísticas simples.
        """
        code_lower = code.lower()
        
        # Python
        if 'def ' in code or 'import ' in code or 'from ' in code:
            return 'python'
        
        # JavaScript/TypeScript
        if 'function ' in code or 'const ' in code or 'let ' in code:
            if 'interface ' in code or ': string' in code or ': number' in code:
                return 'typescript'
            return 'javascript'
        
        # SQL
        if 'select ' in code_lower or 'create table' in code_lower:
            return 'sql'
        
        # HTML
        if '<html' in code_lower or '<div' in code_lower:
            return 'html'
        
        # CSS
        if '{' in code and '}' in code and ':' in code and ';' in code:
            if 'color' in code_lower or 'margin' in code_lower:
                return 'css'
        
        return 'unknown'
    
    def _extract_tags(self, code: str, metadata: Dict) -> list:
        """
        Extrae tags relevantes del código.
        """
        tags = []
        
        # Tags de metadata
        if 'task_type' in metadata:
            tags.append(metadata['task_type'])
        
        if 'framework' in metadata:
            tags.append(metadata['framework'])
        
        # Tags por keywords en código
        code_lower = code.lower()
        
        keywords = {
            'api': ['api', 'endpoint', 'route', '@app.'],
            'database': ['database', 'db.', 'query', 'select', 'insert'],
            'auth': ['auth', 'login', 'jwt', 'token', 'password'],
            'validation': ['validate', 'validator', 'check', 'verify'],
            'async': ['async', 'await', 'asyncio'],
            'test': ['test', 'assert', 'expect', 'describe'],
            'crud': ['create', 'read', 'update', 'delete'],
            'model': ['class', 'model', 'schema'],
            'util': ['util', 'helper', 'common']
        }
        
        for tag, patterns in keywords.items():
            if any(pattern in code_lower for pattern in patterns):
                tags.append(tag)
        
        return list(set(tags))  # Remove duplicates
    
    def _is_reusable_pattern(self, code: str, metadata: Dict) -> bool:
        """
        Determina si el código es un patrón reutilizable.
        """
        # Criterios:
        # 1. Alta calidad (score >= 8.0)
        if metadata.get('quality_score', 0) < 8.0:
            return False
        
        # 2. No es muy largo (< 200 líneas)
        lines = code.count('\n')
        if lines > 200:
            return False
        
        # 3. No es muy corto (> 5 líneas)
        if lines < 5:
            return False
        
        # 4. Tiene algún tag útil
        tags = metadata.get('tags', [])
        useful_tags = ['api', 'database', 'auth', 'validation', 'model', 'crud']
        if not any(tag in useful_tags for tag in tags):
            return False
        
        return True
```

#### 3.2. Integración con Approval Flow Existente

```python
# src/agents/orchestrator_agent.py (MODIFICAR)

from src.services.feedback_service import FeedbackService
from src.rag.vector_store import DevMatrixVectorStore

class OrchestratorAgent:
    def __init__(self):
        # ... código existente ...
        
        # NUEVO: Agregar RAG components
        self.vector_store = DevMatrixVectorStore()
        self.feedback_service = FeedbackService(self.vector_store)
    
    async def handle_approval_response(
        self,
        action: str,  # 'approve' | 'reject' | 'modify'
        code: str,
        task_metadata: Dict,
        quality_score: float,
        user_feedback: Optional[str] = None
    ):
        """
        Handler cuando usuario aprueba/rechaza código.
        """
        if action == 'approve':
            # NUEVO: Indexar código aprobado en RAG
            await self.feedback_service.on_code_approved(
                code=code,
                task_metadata=task_metadata,
                quality_score=quality_score,
                user_feedback=user_feedback
            )
            
            # ... resto del código existente (git commit, etc.) ...
            
        elif action == 'reject':
            # NUEVO: Log código rechazado
            await self.feedback_service.on_code_rejected(
                code=code,
                reason=user_feedback or "User rejected",
                task_metadata=task_metadata
            )
            
            # ... resto del código existente (regenerar) ...
```

---

### Fase 4: Retriever - Búsqueda Inteligente (Día 4-5)

#### 4.1. Retriever Service

```python
# src/rag/retriever.py

from typing import List, Dict, Optional
from src.rag.vector_store import DevMatrixVectorStore
import logging

logger = logging.getLogger(__name__)

class RAGRetriever:
    """
    Servicio de retrieval inteligente.
    Busca ejemplos relevantes para una tarea nueva.
    """
    
    def __init__(self, vector_store: DevMatrixVectorStore):
        self.vector_store = vector_store
    
    def retrieve_for_task(
        self,
        task_description: str,
        task_type: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        n_results: int = 5,
        min_quality_score: float = 7.0
    ) -> List[Dict]:
        """
        Busca ejemplos relevantes para una tarea.
        
        Args:
            task_description: Descripción de la tarea
            task_type: 'backend' | 'frontend' | 'database' | ...
            language: Lenguaje objetivo (opcional)
            framework: Framework objetivo (opcional)
            n_results: Número de ejemplos a retornar
            min_quality_score: Score mínimo de calidad
        
        Returns:
            Lista de ejemplos relevantes con código y metadata
        """
        # Construir filtros
        where_filters = {
            'task_type': task_type,
            'approved': True,
            'quality_score': {'$gte': min_quality_score}
        }
        
        if language:
            where_filters['language'] = language
        
        if framework and framework != 'unknown':
            where_filters['framework'] = framework
        
        # Búsqueda semántica
        results = self.vector_store.search_similar(
            query=task_description,
            collection_name='code_snippets',
            n_results=n_results * 2,  # Buscar más para filtrar
            where=where_filters
        )
        
        # Post-filtrado y ranking
        ranked_results = self._rank_results(
            results,
            task_description,
            n_results
        )
        
        logger.info(f"✅ Retrieved {len(ranked_results)} examples for task: {task_description[:50]}...")
        
        return ranked_results
    
    def retrieve_patterns(
        self,
        query: str,
        n_results: int = 3
    ) -> List[Dict]:
        """
        Busca patrones reutilizables específicamente.
        """
        results = self.vector_store.search_similar(
            query=query,
            collection_name='patterns',
            n_results=n_results,
            where={'approved': True}
        )
        
        return results
    
    def _rank_results(
        self,
        results: List[Dict],
        query: str,
        top_k: int
    ) -> List[Dict]:
        """
        Ranking adicional de resultados.
        """
        # Scoring compuesto
        for result in results:
            score = 0.0
            
            # 1. Similitud semántica (ya viene en distance, menor = mejor)
            # Convertir distance a similarity score
            distance = result.get('distance', 1.0)
            semantic_score = max(0, 1.0 - distance)
            score += semantic_score * 0.4
            
            # 2. Quality score
            quality = result['metadata'].get('quality_score', 5.0)
            score += (quality / 10.0) * 0.3
            
            # 3. Recency (más reciente = mejor)
            # TODO: calcular basado en created_at
            score += 0.1
            
            # 4. Usage count (si tracking de uso existe)
            # TODO: implementar tracking de uso
            
            # 5. Bonus por tags coincidentes
            tags = result['metadata'].get('tags', [])
            query_lower = query.lower()
            matching_tags = sum(1 for tag in tags if tag in query_lower)
            score += min(matching_tags * 0.05, 0.2)
            
            result['final_score'] = score
        
        # Ordenar por score
        ranked = sorted(results, key=lambda x: x['final_score'], reverse=True)
        
        return ranked[:top_k]
    
    def get_diverse_examples(
        self,
        task_description: str,
        task_type: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Obtiene ejemplos diversos (no solo los más similares).
        Útil para ver diferentes approaches.
        """
        # Búsqueda inicial
        results = self.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            n_results=n_results * 3
        )
        
        # Diversificación (MMR-like)
        diverse = []
        remaining = results.copy()
        
        while len(diverse) < n_results and remaining:
            if not diverse:
                # Primer resultado: el mejor
                diverse.append(remaining.pop(0))
            else:
                # Siguiente: menos similar a los ya seleccionados
                best_candidate = None
                max_min_distance = -1
                
                for candidate in remaining:
                    # Calcular mínima similitud con seleccionados
                    min_dist = min(
                        self._code_similarity(candidate['code'], selected['code'])
                        for selected in diverse
                    )
                    
                    if min_dist > max_min_distance:
                        max_min_distance = min_dist
                        best_candidate = candidate
                
                if best_candidate:
                    diverse.append(best_candidate)
                    remaining.remove(best_candidate)
                else:
                    break
        
        return diverse
    
    def _code_similarity(self, code1: str, code2: str) -> float:
        """
        Similitud simple entre dos códigos (Jaccard).
        """
        # Tokenizar por palabras
        tokens1 = set(code1.lower().split())
        tokens2 = set(code2.lower().split())
        
        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
```

---

### Fase 5: Context Builder - Enriquecimiento de Prompts (Día 5-6)

#### 5.1. Context Builder

```python
# src/rag/context_builder.py

from typing import List, Dict, Optional
from src.rag.retriever import RAGRetriever
import logging

logger = logging.getLogger(__name__)

class RAGContextBuilder:
    """
    Construye contexto enriquecido para prompts usando RAG.
    """
    
    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever
    
    def build_context(
        self,
        task_description: str,
        task_type: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        include_patterns: bool = True,
        max_examples: int = 3
    ) -> str:
        """
        Construye contexto RAG para agregar a prompts.
        
        Returns:
            String formateado para insertar en system prompt
        """
        context_parts = []
        
        # 1. Ejemplos similares
        examples = self.retriever.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            language=language,
            framework=framework,
            n_results=max_examples
        )
        
        if examples:
            context_parts.append("## 📚 Ejemplos de Código Similar (Aprobados)\n")
            
            for i, example in enumerate(examples, 1):
                meta = example['metadata']
                code = example['code']
                
                context_parts.append(f"""
### Ejemplo {i} (Quality Score: {meta['quality_score']}/10)
**Framework:** {meta.get('framework', 'N/A')}
**Tags:** {', '.join(meta.get('tags', []))}

```{meta['language']}
{code}
```
""")
        
        # 2. Patrones reutilizables
        if include_patterns:
            patterns = self.retriever.retrieve_patterns(
                query=task_description,
                n_results=2
            )
            
            if patterns:
                context_parts.append("\n## 🧩 Patrones Reutilizables Relevantes\n")
                
                for i, pattern in enumerate(patterns, 1):
                    meta = pattern['metadata']
                    code = pattern['code']
                    
                    context_parts.append(f"""
### Patrón {i}
**Descripción:** {meta.get('description', 'Patrón genérico')}
**Casos de uso:** {', '.join(meta.get('tags', []))}

```{meta['language']}
{code}
```
""")
        
        # 3. Best practices (si existen)
        # TODO: implementar collection de best practices
        
        # 4. Anti-patterns (errores comunes)
        # TODO: implementar tracking de errores comunes
        
        if not context_parts:
            return ""
        
        # Header
        header = """
# 🎯 Contexto RAG: Ejemplos y Patrones Probados

Usa los siguientes ejemplos de código aprobado como referencia para generar
código de alta calidad. Adapta los patrones a las necesidades específicas de esta tarea.

**IMPORTANTE:** 
- NO copies código exactamente, adáptalo al contexto actual
- Usa los ejemplos como inspiración y guía
- Mantén el estilo y convenciones mostradas
- Asegúrate que el código generado sea único y apropiado

---
"""
        
        return header + "\n".join(context_parts)
    
    def build_minimal_context(
        self,
        task_description: str,
        task_type: str,
        max_length: int = 2000
    ) -> str:
        """
        Contexto mínimo para casos con límite de tokens.
        """
        examples = self.retriever.retrieve_for_task(
            task_description=task_description,
            task_type=task_type,
            n_results=1  # Solo el mejor ejemplo
        )
        
        if not examples:
            return ""
        
        example = examples[0]
        meta = example['metadata']
        code = example['code']
        
        # Truncar si es muy largo
        if len(code) > max_length:
            code = code[:max_length] + "\n# ... (truncado)"
        
        return f"""
# 📚 Ejemplo de Referencia (Score: {meta['quality_score']}/10)

```{meta['language']}
{code}
```

Usa este ejemplo como guía para la estructura y estilo.
"""
    
    def get_stats(self) -> Dict:
        """
        Estadísticas del sistema RAG.
        """
        return self.retriever.vector_store.get_stats()
```

---

### Fase 6: Integración con Agentes (Día 6-8)

#### 6.1. Modificar Implementation Agent

```python
# src/agents/implementation_agent.py (MODIFICAR)

from src.rag.retriever import RAGRetriever
from src.rag.context_builder import RAGContextBuilder
from src.rag.vector_store import DevMatrixVectorStore

class ImplementationAgent:
    def __init__(self, llm):
        self.llm = llm
        
        # NUEVO: RAG components
        self.vector_store = DevMatrixVectorStore()
        self.retriever = RAGRetriever(self.vector_store)
        self.context_builder = RAGContextBuilder(self.retriever)
        
        # System prompt base
        self.base_system_prompt = """
You are an expert software engineer specialized in writing production-ready code.
Your code should be:
- Clean and maintainable
- Well-documented
- Type-safe
- Following best practices
"""
    
    async def generate_code(
        self,
        task_description: str,
        task_type: str,
        language: str,
        framework: Optional[str] = None,
        use_rag: bool = True
    ) -> Dict:
        """
        Genera código con RAG context.
        """
        # NUEVO: Construir contexto RAG
        rag_context = ""
        if use_rag:
            rag_context = self.context_builder.build_context(
                task_description=task_description,
                task_type=task_type,
                language=language,
                framework=framework,
                max_examples=3
            )
        
        # Construir prompt completo
        full_prompt = f"""
{self.base_system_prompt}

{rag_context}

---

## 🎯 Tu Tarea

{task_description}

**Especificaciones:**
- Lenguaje: {language}
- Framework: {framework or 'ninguno'}
- Tipo: {task_type}

Genera código completo, limpio y production-ready.
"""
        
        # Generar código con LLM
        response = await self.llm.ainvoke(full_prompt)
        
        # Extraer código de la respuesta
        code = self._extract_code(response.content)
        
        return {
            'code': code,
            'prompt_used': full_prompt,
            'rag_enabled': use_rag,
            'rag_examples_used': rag_context.count('### Ejemplo') if rag_context else 0
        }
    
    def _extract_code(self, response: str) -> str:
        """
        Extrae código de la respuesta del LLM.
        """
        # Buscar bloques de código
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        
        if code_blocks:
            return code_blocks[0].strip()
        
        return response.strip()
```

#### 6.2. Modificar Orchestrator para Habilitar RAG

```python
# src/agents/orchestrator_agent.py (MODIFICAR)

class OrchestratorAgent:
    async def execute_task(
        self,
        task: Dict,
        state: Dict
    ) -> Dict:
        """
        Ejecuta una tarea con el agente apropiado.
        """
        task_type = task['type']
        
        # Determinar agente
        if task_type in ['backend', 'api', 'database']:
            agent = self.backend_agent
        elif task_type in ['frontend', 'ui', 'component']:
            agent = self.frontend_agent
        else:
            agent = self.implementation_agent
        
        # MODIFICADO: Agregar flag use_rag
        result = await agent.generate_code(
            task_description=task['description'],
            task_type=task_type,
            language=task.get('language', 'python'),
            framework=task.get('framework'),
            use_rag=True  # NUEVO: Siempre usar RAG
        )
        
        return result
```

---

### Fase 7: Testing y Validación (Día 9-10)

#### 7.1. Tests del Sistema RAG

```python
# tests/test_rag_system.py

import pytest
import asyncio
from src.rag.vector_store import DevMatrixVectorStore
from src.rag.retriever import RAGRetriever
from src.rag.context_builder import RAGContextBuilder
from src.services.feedback_service import FeedbackService

@pytest.fixture
def rag_system():
    """Setup completo del sistema RAG"""
    vector_store = DevMatrixVectorStore(persist_directory="./test_rag_db")
    retriever = RAGRetriever(vector_store)
    context_builder = RAGContextBuilder(retriever)
    feedback_service = FeedbackService(vector_store)
    
    return {
        'vector_store': vector_store,
        'retriever': retriever,
        'context_builder': context_builder,
        'feedback_service': feedback_service
    }

def test_full_rag_flow(rag_system):
    """
    Test del flujo completo:
    1. Usuario aprueba código
    2. Se indexa en vector store
    3. Se recupera para tarea similar
    4. Se construye contexto
    """
    # 1. Código aprobado
    approved_code = """
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.post("/users")
async def create_user(user: User):
    # TODO: Save to database
    return {"message": "User created", "user": user}
"""
    
    task_metadata = {
        'task_type': 'backend',
        'framework': 'fastapi',
        'file_path': 'api/users.py',
        'project_id': 'test_project'
    }
    
    # 2. Indexar
    doc_id = asyncio.run(
        rag_system['feedback_service'].on_code_approved(
            code=approved_code,
            task_metadata=task_metadata,
            quality_score=8.5
        )
    )
    
    assert doc_id is not None
    
    # 3. Recuperar para tarea similar
    results = rag_system['retriever'].retrieve_for_task(
        task_description="Create an API endpoint to register new users",
        task_type='backend',
        language='python',
        framework='fastapi',
        n_results=1
    )
    
    assert len(results) == 1
    assert 'create_user' in results[0]['code']
    
    # 4. Construir contexto
    context = rag_system['context_builder'].build_context(
        task_description="Create an endpoint to update user information",
        task_type='backend',
        language='python',
        framework='fastapi'
    )
    
    assert len(context) > 0
    assert 'Ejemplo' in context
    assert 'fastapi' in context.lower()
    
    print("✅ Full RAG flow test passed!")

def test_retrieval_quality(rag_system):
    """
    Test de calidad de retrieval.
    """
    # Agregar múltiples ejemplos
    examples = [
        {
            'code': 'def add(a, b): return a + b',
            'description': 'suma dos números',
            'quality': 9.0
        },
        {
            'code': 'def multiply(a, b): return a * b',
            'description': 'multiplica dos números',
            'quality': 8.5
        },
        {
            'code': 'def divide(a, b): return a / b if b != 0 else None',
            'description': 'divide dos números con validación',
            'quality': 9.5
        }
    ]
    
    for ex in examples:
        rag_system['vector_store'].add_code_snippet(
            code=ex['code'],
            metadata={
                'task_type': 'backend',
                'language': 'python',
                'framework': 'none',
                'quality_score': ex['quality'],
                'approved': True,
                'created_at': '2025-01-15',
                'file_path': 'utils.py',
                'project_id': 'test',
                'tags': ['math', 'function']
            }
        )
    
    # Buscar función de división
    results = rag_system['retriever'].retrieve_for_task(
        task_description="create a function to divide two numbers safely",
        task_type='backend',
        language='python',
        n_results=1
    )
    
    # Debe retornar la de mayor calidad (divide)
    assert len(results) > 0
    assert 'divide' in results[0]['code']
    assert results[0]['metadata']['quality_score'] == 9.5
    
    print("✅ Retrieval quality test passed!")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

### Fase 8: Monitoring y Analytics (Día 11-12)

#### 8.1. RAG Analytics Service

```python
# src/rag/analytics.py

from typing import Dict, List
from datetime import datetime, timedelta
from src.rag.vector_store import DevMatrixVectorStore
import logging

logger = logging.getLogger(__name__)

class RAGAnalytics:
    """
    Analytics y métricas del sistema RAG.
    """
    
    def __init__(self, vector_store: DevMatrixVectorStore):
        self.vector_store = vector_store
    
    def get_usage_stats(self) -> Dict:
        """
        Estadísticas de uso del RAG.
        """
        stats = self.vector_store.get_stats()
        
        # TODO: Agregar métricas de retrieval desde logs
        # - Número de búsquedas
        # - Tasa de hits
        # - Latencia promedio
        
        return {
            'timestamp': datetime.now().isoformat(),
            'collections': stats,
            'total_documents': sum(c['count'] for c in stats.values()),
        }
    
    def get_quality_distribution(self) -> Dict:
        """
        Distribución de quality scores en el store.
        """
        # Obtener todos los snippets
        all_snippets = self.vector_store.collections['code_snippets'].get()
        
        if not all_snippets['metadatas']:
            return {'distribution': {}}
        
        # Agrupar por quality score
        scores = [m.get('quality_score', 0) for m in all_snippets['metadatas']]
        
        # Histogram
        bins = {
            '0-5': 0,
            '5-7': 0,
            '7-8': 0,
            '8-9': 0,
            '9-10': 0
        }
        
        for score in scores:
            if score < 5:
                bins['0-5'] += 1
            elif score < 7:
                bins['5-7'] += 1
            elif score < 8:
                bins['7-8'] += 1
            elif score < 9:
                bins['8-9'] += 1
            else:
                bins['9-10'] += 1
        
        return {
            'distribution': bins,
            'average_score': sum(scores) / len(scores) if scores else 0,
            'total_samples': len(scores)
        }
    
    def get_language_breakdown(self) -> Dict:
        """
        Breakdown por lenguaje.
        """
        all_snippets = self.vector_store.collections['code_snippets'].get()
        
        if not all_snippets['metadatas']:
            return {}
        
        languages = {}
        for meta in all_snippets['metadatas']:
            lang = meta.get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
        
        return languages
    
    def get_most_retrieved_patterns(self, top_n: int = 10) -> List[Dict]:
        """
        Patrones más recuperados.
        
        TODO: Implementar tracking de retrieval counts
        """
        # Placeholder
        return []
    
    def cleanup_old_low_quality(
        self,
        days_old: int = 30,
        min_quality: float = 6.0
    ) -> int:
        """
        Limpia código viejo de baja calidad.
        """
        deleted = self.vector_store.delete_low_quality(
            min_quality_score=min_quality
        )
        
        logger.info(f"🧹 Cleaned {deleted} low-quality documents")
        
        return deleted
```

#### 8.2. Dashboard Endpoint (FastAPI)

```python
# src/api/routes/rag_routes.py (NUEVO)

from fastapi import APIRouter, Depends
from src.rag.vector_store import DevMatrixVectorStore
from src.rag.analytics import RAGAnalytics

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# Dependency
def get_analytics():
    vector_store = DevMatrixVectorStore()
    return RAGAnalytics(vector_store)

@router.get("/stats")
async def get_rag_stats(analytics: RAGAnalytics = Depends(get_analytics)):
    """
    GET /api/rag/stats
    
    Estadísticas del sistema RAG.
    """
    return {
        'usage': analytics.get_usage_stats(),
        'quality': analytics.get_quality_distribution(),
        'languages': analytics.get_language_breakdown()
    }

@router.post("/cleanup")
async def cleanup_rag_store(
    min_quality: float = 6.0,
    analytics: RAGAnalytics = Depends(get_analytics)
):
    """
    POST /api/rag/cleanup
    
    Limpia documentos de baja calidad.
    """
    deleted = analytics.cleanup_old_low_quality(min_quality=min_quality)
    
    return {
        'deleted_count': deleted,
        'message': f'Cleaned {deleted} low-quality documents'
    }
```

---

### Fase 9: Optimizaciones (Día 13-14)

#### 9.1. Caching de Retrievals

```python
# src/rag/retriever.py (OPTIMIZACIÓN)

from functools import lru_cache
import hashlib

class RAGRetriever:
    def __init__(self, vector_store: DevMatrixVectorStore):
        self.vector_store = vector_store
        self.cache = {}  # Simple in-memory cache
    
    def retrieve_for_task(
        self,
        task_description: str,
        task_type: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        n_results: int = 5,
        min_quality_score: float = 7.0
    ) -> List[Dict]:
        """
        Con caching para retrieval repetidos.
        """
        # Generar cache key
        cache_key = self._generate_cache_key(
            task_description, task_type, language, framework, n_results
        )
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"✅ Cache hit for retrieval")
            return self.cache[cache_key]
        
        # ... resto del código de retrieval ...
        
        # Guardar en cache
        self.cache[cache_key] = ranked_results
        
        # Limitar tamaño del cache
        if len(self.cache) > 1000:
            # FIFO simple
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        return ranked_results
    
    def _generate_cache_key(self, *args) -> str:
        """
        Genera hash para cache key.
        """
        key_str = '|'.join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
```

#### 9.2. Batch Indexing

```python
# src/services/feedback_service.py (OPTIMIZACIÓN)

class FeedbackService:
    def __init__(self, vector_store: DevMatrixVectorStore):
        self.vector_store = vector_store
        self.pending_batch = []
        self.batch_size = 10
    
    async def on_code_approved(self, code: str, task_metadata: Dict, quality_score: float):
        """
        Con batching para mejor performance.
        """
        # Agregar a batch
        self.pending_batch.append({
            'code': code,
            'metadata': self._build_metadata(task_metadata, quality_score)
        })
        
        # Flush si llegó al límite
        if len(self.pending_batch) >= self.batch_size:
            await self._flush_batch()
    
    async def _flush_batch(self):
        """
        Indexa batch completo.
        """
        if not self.pending_batch:
            return
        
        try:
            for item in self.pending_batch:
                self.vector_store.add_code_snippet(
                    code=item['code'],
                    metadata=item['metadata']
                )
            
            logger.info(f"✅ Indexed batch of {len(self.pending_batch)} documents")
            self.pending_batch = []
            
        except Exception as e:
            logger.error(f"❌ Batch indexing failed: {e}")
```

---

## 🎯 Plan de Implementación Completo

### Semana 1 (Días 1-7): Setup y Base

- **Día 1-2**: 
  - [x] Instalar ChromaDB y dependencias
  - [x] Crear `DevMatrixVectorStore`
  - [x] Tests básicos de vector store

- **Día 3-4**:
  - [x] Implementar `FeedbackService`
  - [x] Integrar con approval flow existente
  - [x] Tests de indexación

- **Día 5-6**:
  - [x] Implementar `RAGRetriever`
  - [x] Implementar `RAGContextBuilder`
  - [x] Tests de retrieval

- **Día 7**:
  - [x] Review y fixes
  - [x] Documentation

### Semana 2 (Días 8-14): Integración y Optimización

- **Día 8-9**:
  - [x] Integrar RAG en agents
  - [x] Tests E2E del flujo completo
  - [x] Validar mejora en calidad

- **Día 10-11**:
  - [x] Analytics y monitoring
  - [x] Dashboard endpoints
  - [x] Cleanup utilities

- **Día 12-13**:
  - [x] Optimizaciones (caching, batching)
  - [x] Performance tuning
  - [x] Load testing

- **Día 14**:
  - [x] Documentation completa
  - [x] Deployment a production
  - [x] Monitoring setup

---

## 📊 Métricas de Éxito

### Pre-RAG (Baseline)
```
Precisión estimada: 70-80%
Código aprobado sin modificaciones: 60-70%
Tiempo promedio por tarea: X minutos
Costo por tarea: $0.03 (Claude Sonnet)
```

### Post-RAG (Objetivo)
```
Precisión objetivo: 90%+
Código aprobado sin modificaciones: 85%+
Tiempo promedio por tarea: -20% (más rápido con ejemplos)
Costo: Similar (mismo modelo)
Quality score promedio: 8.5+/10
```

### Métricas Intermedias a Trackear

1. **Retrieval Accuracy**
   - % de retrievals con ejemplos relevantes
   - Score de similitud promedio
   - Objetivo: >80% relevancia

2. **Usage Rate**
   - % de generaciones que usan RAG
   - Objetivo: 100%

3. **Impact on Quality**
   - Quality score con RAG vs sin RAG
   - Objetivo: +1.5 puntos promedio

4. **Vector Store Growth**
   - Documentos indexados por día
   - Objetivo: Crecimiento constante

5. **User Satisfaction**
   - Tasa de aprobación de código
   - Modificaciones solicitadas
   - Objetivo: -30% en modificaciones

---

## 🚀 Deployment

### Production Setup

```bash
# 1. Build production vector DB path
mkdir -p /data/devmatrix/chroma_db

# 2. Environment variables
export CHROMA_DB_PATH=/data/devmatrix/chroma_db
export RAG_ENABLED=true
export RAG_MAX_EXAMPLES=3
export RAG_MIN_QUALITY=7.0

# 3. Initialize vector store
python scripts/init_rag.py

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify RAG is working
curl http://localhost:8000/api/rag/stats
```

### Backup Strategy

```bash
# Daily backup of ChromaDB
0 2 * * * tar -czf /backups/chroma_$(date +\%Y\%m\%d).tar.gz /data/devmatrix/chroma_db

# Keep last 30 days
find /backups -name "chroma_*.tar.gz" -mtime +30 -delete
```

---

## 💰 Costos

### Infraestructura
```
ChromaDB: $0 (self-hosted)
Storage: ~10GB para 100K documentos (~$0.50/mes)
Compute: Sin overhead significativo
Total: ~$1/mes
```

### Performance Impact
```
Latencia adicional: +50-100ms por retrieval
Latencia total: 2-3 segundos (acceptable)
Memory: +500MB para vector store en memoria
```

### ROI Esperado
```
Inversión: 2-4 semanas dev time
Beneficio: +10-15% precision → -50% tiempo de debugging
Break-even: 1-2 meses
```

---

## ⚠️ Considerations y Warnings

### 1. Cold Start Problem
**Problema**: Vector store vacío al inicio.

**Solución**:
- Seed inicial con templates genéricos
- Agregar ejemplos de documentación oficial
- Importar código de proyectos open source de alta calidad

```python
# scripts/seed_rag.py

def seed_vector_store():
    """Seed inicial del vector store"""
    
    seeds = [
        {
            'code': '# FastAPI endpoint template...',
            'metadata': {...}
        },
        # ... más seeds
    ]
    
    for seed in seeds:
        vector_store.add_code_snippet(
            code=seed['code'],
            metadata=seed['metadata'],
            collection_name='templates'
        )
```

### 2. Quality Control
**Problema**: Código malo indexado contamina RAG.

**Solución**:
- Solo indexar código con quality_score >= 7.0
- Cleanup periódico de bajo score
- Feedback loop: track si ejemplos RAG fueron útiles

### 3. Context Length Limits
**Problema**: Ejemplos muy largos exceden token limit.

**Solución**:
- Truncar ejemplos a 200 líneas max
- Usar solo fragmentos relevantes
- Compression de código repetitivo

### 4. Embedding Quality
**Problema**: sentence-transformers no específico para código.

**Solución** (futura):
- Usar CodeBERT o similar
- Fine-tune embeddings en tu dominio
- Por ahora, sentence-transformers es suficiente

---

## 🔄 Roadmap Post-MVP RAG

### Fase 2 (Próximos 2-3 meses)

1. **Embeddings especializados**
   - Migrar a CodeBERT
   - Fine-tuning en código DevMatrix

2. **Multi-modal retrieval**
   - Buscar por código + comentarios + nombres
   - Buscar por AST structure

3. **Negative examples**
   - Indexar código rechazado
   - "Avoid patterns like..."

4. **Usage tracking**
   - Trackear qué ejemplos se usan más
   - Re-rankear basado en utilidad real

5. **Hybrid search**
   - Combinar semantic + keyword search
   - Better precision

6. **Cross-project learning**
   - Compartir patrones entre proyectos
   - Privacy-preserving aggregation

---

## 📝 Checklist de Implementación

```markdown
### Setup Básico
- [ ] Instalar ChromaDB
- [ ] Crear vector store wrapper
- [ ] Test básico de indexación/retrieval

### Feedback Loop
- [ ] Implementar FeedbackService
- [ ] Integrar con approval flow
- [ ] Test de indexación en aprobación

### Retrieval
- [ ] Implementar RAGRetriever
- [ ] Ranking inteligente de resultados
- [ ] Diversity en ejemplos

### Context Building
- [ ] Implementar RAGContextBuilder
- [ ] Templates de contexto
- [ ] Formatting para diferentes agentes

### Integración
- [ ] Modificar ImplementationAgent
- [ ] Modificar otros agentes
- [ ] Tests E2E con RAG

### Monitoring
- [ ] Analytics service
- [ ] Dashboard endpoints
- [ ] Métricas de calidad

### Optimización
- [ ] Caching de retrievals
- [ ] Batch indexing
- [ ] Performance tuning

### Production
- [ ] Deployment scripts
- [ ] Backup strategy
- [ ] Monitoring alerts
- [ ] Documentation
```

---

## 🎉 Conclusión

Con esta implementación de RAG, DevMatrix pasará de:

**70-80% precision** → **90%+ precision**

El sistema aprenderá de cada código aprobado y mejorará continuamente. Es el gap más crítico entre el MVP actual y el plan original.

**Next steps inmediatos**:
1. Implementar Vector Store (Día 1)
2. Integrar Feedback Loop (Día 2-3)
3. Retriever + Context Builder (Día 4-6)
4. Integración con Agents (Día 7-10)
5. Testing y Production (Día 11-14)

¿Empezamos con el código del Vector Store? 🚀
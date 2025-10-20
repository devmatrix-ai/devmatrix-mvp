# DevMatrix: Sistema de Machine Learning y Aprendizaje Continuo

## 🎯 Objetivo

Construir un sistema de aprendizaje continuo que:
- **Aprende de cada generación**: Código aprobado/rechazado → Mejora automática
- **Predice complejidad**: Estima tiempo y dificultad antes de generar
- **Optimiza templates**: Evoluciona patrones automáticamente
- **Ajusta pesos de modelos**: Route inteligente según historial
- **Detecta patterns**: Identifica patrones exitosos emergentes

**Timeline**: 3-4 meses de desarrollo
**Impacto esperado**: +5-10% en precisión, -30% en tiempo de generación

---

## 🏗️ Arquitectura del Sistema ML

### Vista de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVMATRIX ML SYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Code Generated  │────▶│   Data Pipeline  │────▶│  Feature DB  │
│  (every attempt) │     │   (Extraction)   │     │ (PostgreSQL) │
└──────────────────┘     └──────────────────┘     └──────────────┘
                                                           │
                         ┌─────────────────────────────────┘
                         │
                         ▼
                    ┌──────────────────┐
                    │  Training Loop   │
                    │  (Nightly)       │
                    │                  │
                    │  • Success Model │
                    │  • Complexity    │
                    │  • Time Estimate │
                    │  • Quality Score │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Model Registry  │
                    │  (MLflow)        │
                    └────────┬─────────┘
                             │
                             ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Live Prediction │◀────│  Inference API   │◀────│ Model Serving│
│  (each request)  │     │  (FastAPI)       │     │ (in-memory)  │
└──────────────────┘     └──────────────────┘     └──────────────┘
         │
         ▼
┌──────────────────┐
│  Adaptive Agents │
│  • Model routing │
│  • Template sel. │
│  • Config tuning │
└──────────────────┘
```

---

## 📊 Modelos de Machine Learning

### 1. Success Predictor (Classifier)

**Objetivo**: Predecir si una generación será aprobada sin modificaciones.

**Input Features**:
```python
features = {
    # Task characteristics
    'task_type': categorical,           # backend, frontend, database, etc.
    'language': categorical,            # python, javascript, typescript, etc.
    'framework': categorical,           # fastapi, react, django, etc.
    'task_complexity': float,           # 0-10 (calculado por heurística)
    'task_description_length': int,     # Longitud de la descripción
    'num_requirements': int,            # Número de requerimientos explícitos
    
    # Historical context
    'similar_tasks_success_rate': float,  # Tasa de éxito en tareas similares
    'agent_past_performance': float,      # Performance del agente asignado
    'rag_examples_available': int,        # Número de ejemplos RAG disponibles
    'rag_avg_quality': float,             # Calidad promedio de ejemplos RAG
    
    # Model characteristics
    'model_used': categorical,          # claude-sonnet-4.5, deepseek, etc.
    'temperature': float,               # Temperatura del modelo
    'max_tokens': int,                  # Límite de tokens
    
    # Time context
    'hour_of_day': int,                 # 0-23
    'day_of_week': int,                 # 0-6
    'project_maturity': int             # Días desde inicio del proyecto
}
```

**Output**: 
```python
{
    'success_probability': float,  # 0.0 - 1.0
    'confidence': float,           # Model confidence
    'risk_factors': List[str]      # Factores de riesgo detectados
}
```

**Model Architecture**:
```python
# Gradient Boosting (XGBoost) o LightGBM
# Razón: Excelente para tabular data, interpretable

from xgboost import XGBClassifier

model = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    objective='binary:logistic',
    eval_metric='auc'
)
```

---

### 2. Complexity Estimator (Regressor)

**Objetivo**: Estimar complejidad/dificultad de una tarea en escala 0-10.

**Input Features**:
```python
features = {
    # Task analysis
    'description_length': int,
    'num_technical_terms': int,         # keywords técnicos detectados
    'num_entities': int,                # Entidades mencionadas (User, Order, etc.)
    'num_relationships': int,           # Relaciones entre entidades
    'num_constraints': int,             # Constraints explícitos
    'has_authentication': bool,
    'has_authorization': bool,
    'has_validation': bool,
    'has_database': bool,
    'has_api_integration': bool,
    'has_file_upload': bool,
    'has_real_time': bool,
    
    # Historical
    'avg_complexity_for_type': float,   # Complejidad promedio para este tipo
    'similar_tasks_complexity': float,  # Complejidad de tareas similares
    
    # Stack complexity
    'framework_complexity': float,      # Complejidad del framework
    'num_dependencies': int             # Dependencias requeridas
}
```

**Output**:
```python
{
    'complexity_score': float,      # 0.0 - 10.0
    'confidence_interval': tuple,   # (lower, upper)
    'complexity_factors': List[Dict]  # Qué contribuye a la complejidad
}
```

**Model Architecture**:
```python
# Random Forest Regressor
# Razón: Robusto, interpretable, maneja non-linearity

from sklearn.ensemble import RandomForestRegressor

model = RandomForestRegressor(
    n_estimators=150,
    max_depth=10,
    min_samples_split=5,
    random_state=42
)
```

---

### 3. Time Estimator (Regressor)

**Objetivo**: Predecir tiempo de generación en segundos.

**Input Features**:
```python
features = {
    # Task characteristics
    'complexity_score': float,          # Del modelo anterior
    'estimated_lines_of_code': int,     # Heurística basada en descripción
    'num_files_to_generate': int,
    
    # Model characteristics
    'model_name': categorical,
    'avg_tokens_per_task': float,
    'temperature': float,
    
    # Historical
    'similar_tasks_avg_time': float,
    'agent_avg_generation_time': float,
    'model_avg_latency': float,
    
    # System load
    'current_queue_size': int,
    'system_load': float
}
```

**Output**:
```python
{
    'estimated_seconds': float,
    'confidence_interval': tuple,
    'bottlenecks': List[str]  # Posibles cuellos de botella
}
```

---

### 4. Quality Score Predictor (Regressor)

**Objetivo**: Predecir quality score (0-10) que obtendrá el código generado.

**Input Features**:
```python
features = {
    # Generation context
    'success_probability': float,      # Del success predictor
    'complexity_score': float,
    'rag_examples_count': int,
    'rag_avg_quality': float,
    'model_used': categorical,
    'temperature': float,
    
    # Historical
    'agent_avg_quality': float,
    'similar_tasks_avg_quality': float,
    
    # Code characteristics (post-generation, para training)
    'lines_of_code': int,
    'cyclomatic_complexity': float,
    'num_functions': int,
    'num_classes': int,
    'has_type_hints': bool,
    'has_docstrings': bool,
    'has_tests': bool
}
```

**Output**:
```python
{
    'predicted_quality_score': float,  # 0.0 - 10.0
    'confidence': float,
    'quality_factors': List[Dict]
}
```

---

### 5. Template Selector (Ranking Model)

**Objetivo**: Rankear templates/patterns por probabilidad de éxito para una tarea.

**Input Features (per template)**:
```python
features = {
    # Template characteristics
    'template_id': str,
    'template_complexity': float,
    'template_usage_count': int,
    'template_success_rate': float,
    'template_avg_quality': float,
    'template_avg_time': float,
    
    # Similarity to current task
    'semantic_similarity': float,       # Embedding similarity
    'task_type_match': bool,
    'language_match': bool,
    'framework_match': bool,
    'tags_overlap': float,
    
    # Contextual
    'recent_usage_success': float,      # Éxito reciente
    'user_preference': float            # Si usuario prefiere ciertos templates
}
```

**Output**:
```python
{
    'ranked_templates': List[Tuple[str, float]],  # (template_id, score)
    'reasoning': Dict[str, str]                    # Por qué cada ranking
}
```

**Model Architecture**:
```python
# Learning to Rank (LambdaRank o LightGBM ranker)

import lightgbm as lgb

model = lgb.LGBMRanker(
    objective='lambdarank',
    metric='ndcg',
    n_estimators=100,
    learning_rate=0.1
)
```

---

## 🔄 Data Pipeline

### 1. Data Collection Schema

```python
# src/ml/schemas.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict

class GenerationEvent(BaseModel):
    """
    Evento de generación de código.
    Se captura en CADA generación, aprobada o no.
    """
    # IDs
    event_id: str
    task_id: str
    project_id: str
    user_id: str
    session_id: str
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime]
    approved_at: Optional[datetime]
    
    # Task context
    task_type: str                    # backend, frontend, etc.
    task_description: str
    language: str
    framework: Optional[str]
    
    # Generation config
    agent_type: str                   # implementation, backend, frontend
    model_used: str                   # claude-sonnet-4.5, etc.
    temperature: float
    max_tokens: int
    
    # RAG context
    rag_enabled: bool
    rag_examples_count: int
    rag_examples_ids: List[str]
    rag_avg_similarity: Optional[float]
    
    # Generated code
    generated_code: str
    file_path: str
    lines_of_code: int
    
    # Quality metrics (calculated)
    cyclomatic_complexity: Optional[float]
    num_functions: int
    num_classes: int
    has_type_hints: bool
    has_docstrings: bool
    has_tests: bool
    
    # Self-review
    self_review_score: Optional[float]  # 0-10
    self_review_feedback: Optional[str]
    
    # Human feedback
    user_action: Optional[str]        # approve, reject, modify
    user_feedback: Optional[str]
    modifications_requested: Optional[str]
    final_quality_score: Optional[float]
    
    # Performance
    generation_time_seconds: float
    tokens_used: int
    cost_usd: float
    
    # Outcome
    success: bool                     # True si aprobado sin modificaciones
    approved: bool                    # True si eventualmente aprobado
    num_regenerations: int            # Intentos hasta aprobación
    
    # Metadata
    metadata: Dict

class FeatureVector(BaseModel):
    """
    Vector de features para ML.
    Calculado a partir de GenerationEvent.
    """
    event_id: str
    
    # Task features
    task_type_encoded: int
    language_encoded: int
    framework_encoded: int
    task_complexity_score: float
    task_description_length: int
    num_requirements: int
    num_technical_terms: int
    
    # Historical features
    similar_tasks_success_rate: float
    agent_past_performance: float
    model_past_performance: float
    
    # RAG features
    rag_examples_count: int
    rag_avg_quality: float
    rag_avg_similarity: float
    
    # Context features
    hour_of_day: int
    day_of_week: int
    project_maturity_days: int
    
    # Target variables (for training)
    target_success: bool
    target_quality_score: Optional[float]
    target_time_seconds: Optional[float]
```

### 2. Data Collection Service

```python
# src/ml/data_collection.py

import asyncio
from typing import Dict, Optional
from datetime import datetime
from src.ml.schemas import GenerationEvent
from src.ml.feature_engineering import FeatureEngineer
import logging

logger = logging.getLogger(__name__)

class MLDataCollector:
    """
    Servicio que captura datos de cada generación para ML.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.feature_engineer = FeatureEngineer()
        self.buffer = []
        self.buffer_size = 50
    
    async def record_generation_start(
        self,
        task_id: str,
        task_context: Dict
    ) -> str:
        """
        Registra inicio de generación.
        """
        event = GenerationEvent(
            event_id=f"gen_{task_id}_{int(datetime.now().timestamp())}",
            task_id=task_id,
            started_at=datetime.now(),
            **task_context
        )
        
        # Guardar en DB
        await self._save_event(event)
        
        return event.event_id
    
    async def record_generation_complete(
        self,
        event_id: str,
        generated_code: str,
        generation_time: float,
        self_review_score: float,
        metadata: Dict
    ):
        """
        Registra finalización de generación.
        """
        # Calcular métricas del código
        code_metrics = self._analyze_code(generated_code)
        
        # Update event
        await self.db.update_generation_event(
            event_id=event_id,
            updates={
                'completed_at': datetime.now(),
                'generated_code': generated_code,
                'generation_time_seconds': generation_time,
                'self_review_score': self_review_score,
                'lines_of_code': code_metrics['loc'],
                'cyclomatic_complexity': code_metrics['complexity'],
                'num_functions': code_metrics['functions'],
                'num_classes': code_metrics['classes'],
                'has_type_hints': code_metrics['type_hints'],
                'has_docstrings': code_metrics['docstrings'],
                'metadata': metadata
            }
        )
    
    async def record_user_feedback(
        self,
        event_id: str,
        action: str,  # approve, reject, modify
        feedback: Optional[str],
        final_quality_score: Optional[float]
    ):
        """
        Registra feedback del usuario.
        """
        success = action == 'approve'
        approved = action != 'reject'
        
        await self.db.update_generation_event(
            event_id=event_id,
            updates={
                'approved_at': datetime.now() if approved else None,
                'user_action': action,
                'user_feedback': feedback,
                'final_quality_score': final_quality_score,
                'success': success,
                'approved': approved
            }
        )
        
        # Si hay suficientes datos, trigger feature engineering
        if success:
            await self._maybe_trigger_feature_engineering(event_id)
    
    async def _maybe_trigger_feature_engineering(self, event_id: str):
        """
        Trigger feature engineering si tenemos suficientes eventos.
        """
        self.buffer.append(event_id)
        
        if len(self.buffer) >= self.buffer_size:
            # Process batch
            asyncio.create_task(
                self._batch_feature_engineering(self.buffer.copy())
            )
            self.buffer = []
    
    async def _batch_feature_engineering(self, event_ids: List[str]):
        """
        Feature engineering en batch.
        """
        try:
            events = await self.db.get_generation_events(event_ids)
            
            for event in events:
                features = self.feature_engineer.extract_features(event)
                await self.db.save_feature_vector(features)
            
            logger.info(f"✅ Feature engineering completed for {len(events)} events")
            
        except Exception as e:
            logger.error(f"❌ Feature engineering failed: {e}")
    
    def _analyze_code(self, code: str) -> Dict:
        """
        Analiza código para extraer métricas.
        """
        # TODO: Implementar análisis completo
        # - Lines of code
        # - Cyclomatic complexity
        # - Number of functions/classes
        # - Type hints coverage
        # - Docstrings coverage
        
        return {
            'loc': code.count('\n'),
            'complexity': 0.0,  # TODO
            'functions': 0,     # TODO
            'classes': 0,       # TODO
            'type_hints': False, # TODO
            'docstrings': False  # TODO
        }
    
    async def _save_event(self, event: GenerationEvent):
        """
        Guarda evento en PostgreSQL.
        """
        await self.db.insert('ml_generation_events', event.dict())
```

---

### 3. Feature Engineering

```python
# src/ml/feature_engineering.py

from typing import Dict, List
from src.ml.schemas import GenerationEvent, FeatureVector
from datetime import datetime
import re

class FeatureEngineer:
    """
    Extrae features de eventos de generación.
    """
    
    def __init__(self):
        self.encoders = self._init_encoders()
    
    def extract_features(self, event: GenerationEvent) -> FeatureVector:
        """
        Extrae vector de features de un evento.
        """
        # Basic encoding
        task_type_encoded = self.encoders['task_type'].get(event.task_type, 0)
        language_encoded = self.encoders['language'].get(event.language, 0)
        framework_encoded = self.encoders['framework'].get(event.framework or 'none', 0)
        
        # Task complexity (heurística)
        complexity_score = self._calculate_task_complexity(event)
        
        # Historical features (requiere queries a DB)
        historical = self._get_historical_features(event)
        
        # RAG features
        rag_features = self._extract_rag_features(event)
        
        # Context features
        timestamp = event.started_at
        hour_of_day = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Construct feature vector
        return FeatureVector(
            event_id=event.event_id,
            
            # Task features
            task_type_encoded=task_type_encoded,
            language_encoded=language_encoded,
            framework_encoded=framework_encoded,
            task_complexity_score=complexity_score,
            task_description_length=len(event.task_description),
            num_requirements=self._count_requirements(event.task_description),
            num_technical_terms=self._count_technical_terms(event.task_description),
            
            # Historical features
            similar_tasks_success_rate=historical['similar_success_rate'],
            agent_past_performance=historical['agent_performance'],
            model_past_performance=historical['model_performance'],
            
            # RAG features
            rag_examples_count=rag_features['count'],
            rag_avg_quality=rag_features['avg_quality'],
            rag_avg_similarity=rag_features['avg_similarity'],
            
            # Context features
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            project_maturity_days=historical['project_maturity'],
            
            # Targets (for training)
            target_success=event.success,
            target_quality_score=event.final_quality_score,
            target_time_seconds=event.generation_time_seconds
        )
    
    def _calculate_task_complexity(self, event: GenerationEvent) -> float:
        """
        Calcula complejidad de tarea con heurística.
        """
        score = 0.0
        desc = event.task_description.lower()
        
        # Base por tipo
        complexity_by_type = {
            'backend': 5.0,
            'frontend': 4.0,
            'database': 6.0,
            'testing': 3.0,
            'documentation': 2.0
        }
        score += complexity_by_type.get(event.task_type, 4.0)
        
        # Keywords complejos
        complex_keywords = [
            'authentication', 'authorization', 'security',
            'real-time', 'websocket', 'streaming',
            'distributed', 'microservices', 'queue',
            'payment', 'transaction', 'blockchain',
            'machine learning', 'ai', 'model'
        ]
        
        for keyword in complex_keywords:
            if keyword in desc:
                score += 0.5
        
        # Longitud de descripción
        if len(event.task_description) > 500:
            score += 1.0
        
        # Normalizar a 0-10
        return min(10.0, score)
    
    def _count_requirements(self, description: str) -> int:
        """
        Cuenta requirements explícitos.
        """
        # Buscar bullets, numbers, "must", "should"
        bullets = description.count('- ')
        bullets += description.count('* ')
        bullets += len(re.findall(r'\d+\.\s', description))
        
        must_count = description.lower().count('must')
        should_count = description.lower().count('should')
        
        return bullets + must_count + should_count
    
    def _count_technical_terms(self, description: str) -> int:
        """
        Cuenta términos técnicos.
        """
        technical_terms = [
            'api', 'endpoint', 'route', 'controller', 'service',
            'model', 'schema', 'migration', 'database', 'query',
            'authentication', 'authorization', 'jwt', 'token',
            'validation', 'serializer', 'crud', 'rest', 'graphql',
            'component', 'hook', 'state', 'props', 'redux',
            'async', 'await', 'promise', 'callback',
            'docker', 'kubernetes', 'ci/cd', 'deployment'
        ]
        
        desc_lower = description.lower()
        count = sum(1 for term in technical_terms if term in desc_lower)
        
        return count
    
    def _get_historical_features(self, event: GenerationEvent) -> Dict:
        """
        Features históricas (requiere queries).
        """
        # TODO: Implementar queries reales
        return {
            'similar_success_rate': 0.75,  # Placeholder
            'agent_performance': 0.80,     # Placeholder
            'model_performance': 0.82,     # Placeholder
            'project_maturity': 14         # Placeholder
        }
    
    def _extract_rag_features(self, event: GenerationEvent) -> Dict:
        """
        Features de RAG.
        """
        if not event.rag_enabled:
            return {
                'count': 0,
                'avg_quality': 0.0,
                'avg_similarity': 0.0
            }
        
        # TODO: Obtener calidad real de ejemplos RAG
        return {
            'count': event.rag_examples_count,
            'avg_quality': 8.0,  # Placeholder
            'avg_similarity': event.rag_avg_similarity or 0.7
        }
    
    def _init_encoders(self) -> Dict:
        """
        Inicializa label encoders.
        """
        return {
            'task_type': {
                'backend': 0,
                'frontend': 1,
                'database': 2,
                'testing': 3,
                'documentation': 4,
                'devops': 5
            },
            'language': {
                'python': 0,
                'javascript': 1,
                'typescript': 2,
                'sql': 3,
                'html': 4,
                'css': 5
            },
            'framework': {
                'fastapi': 0,
                'django': 1,
                'flask': 2,
                'react': 3,
                'vue': 4,
                'angular': 5,
                'none': 6
            }
        }
```

---

## 🎓 Training Pipeline

### 1. Model Trainer

```python
# src/ml/training/trainer.py

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from xgboost import XGBClassifier
import mlflow
import mlflow.sklearn
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class SuccessPredictorTrainer:
    """
    Entrenamiento del modelo Success Predictor.
    """
    
    def __init__(self, db_connection, mlflow_tracking_uri: str):
        self.db = db_connection
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment("devmatrix-success-predictor")
    
    async def train(
        self,
        min_samples: int = 100,
        test_size: float = 0.2
    ) -> Dict:
        """
        Entrena modelo con datos históricos.
        """
        # 1. Load data
        logger.info("Loading training data...")
        df = await self._load_training_data(min_samples)
        
        if len(df) < min_samples:
            raise ValueError(f"Not enough training data: {len(df)} < {min_samples}")
        
        # 2. Prepare features
        X, y = self._prepare_features(df)
        
        # 3. Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        logger.info(f"Training set: {len(X_train)}, Test set: {len(X_test)}")
        
        # 4. Train with MLflow tracking
        with mlflow.start_run():
            # Log parameters
            params = {
                'n_estimators': 200,
                'max_depth': 6,
                'learning_rate': 0.1,
                'min_samples': min_samples
            }
            mlflow.log_params(params)
            
            # Train model
            model = XGBClassifier(
                n_estimators=params['n_estimators'],
                max_depth=params['max_depth'],
                learning_rate=params['learning_rate'],
                objective='binary:logistic',
                eval_metric='auc',
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'f1_score': f1_score(y_test, y_pred),
                'roc_auc': roc_auc_score(y_test, y_pred_proba)
            }
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log model
            mlflow.sklearn.log_model(model, "model")
            
            # Feature importance
            feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            logger.info(f"✅ Model trained. Accuracy: {metrics['accuracy']:.3f}, AUC: {metrics['roc_auc']:.3f}")
            
            return {
                'model': model,
                'metrics': metrics,
                'feature_importance': feature_importance,
                'run_id': mlflow.active_run().info.run_id
            }
    
    async def _load_training_data(self, min_samples: int) -> pd.DataFrame:
        """
        Carga datos de entrenamiento desde PostgreSQL.
        """
        query = """
        SELECT 
            fv.*,
            ge.success as target_success
        FROM ml_feature_vectors fv
        JOIN ml_generation_events ge ON fv.event_id = ge.event_id
        WHERE ge.user_action IS NOT NULL
        ORDER BY ge.completed_at DESC
        LIMIT 10000
        """
        
        df = await self.db.query_dataframe(query)
        return df
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepara features para training.
        """
        feature_columns = [
            'task_type_encoded',
            'language_encoded',
            'framework_encoded',
            'task_complexity_score',
            'task_description_length',
            'num_requirements',
            'num_technical_terms',
            'similar_tasks_success_rate',
            'agent_past_performance',
            'model_past_performance',
            'rag_examples_count',
            'rag_avg_quality',
            'rag_avg_similarity',
            'hour_of_day',
            'day_of_week',
            'project_maturity_days'
        ]
        
        X = df[feature_columns]
        y = df['target_success']
        
        return X, y
```

### 2. Automated Training Schedule

```python
# src/ml/training/scheduler.py

import schedule
import asyncio
from src.ml.training.trainer import SuccessPredictorTrainer
import logging

logger = logging.getLogger(__name__)

class TrainingScheduler:
    """
    Scheduler para reentrenamiento automático.
    """
    
    def __init__(self, db_connection, mlflow_uri: str):
        self.trainer = SuccessPredictorTrainer(db_connection, mlflow_uri)
    
    def start(self):
        """
        Inicia scheduler.
        """
        # Entrenar cada noche a las 2 AM
        schedule.every().day.at("02:00").do(self._run_training)
        
        logger.info("✅ Training scheduler started (daily at 02:00)")
        
        # Run loop
        while True:
            schedule.run_pending()
            asyncio.sleep(60)  # Check every minute
    
    async def _run_training(self):
        """
        Ejecuta training job.
        """
        try:
            logger.info("🎓 Starting automated training...")
            
            result = await self.trainer.train(min_samples=100)
            
            # Check if new model is better than current
            if await self._should_promote_model(result):
                await self._promote_model(result['run_id'])
                logger.info("✅ New model promoted to production")
            else:
                logger.info("⏭️ Current model is still better, keeping it")
                
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
    
    async def _should_promote_model(self, result: Dict) -> bool:
        """
        Decide si promover nuevo modelo.
        """
        # TODO: Comparar con modelo actual en producción
        # Por ahora, promover si accuracy > 0.75 y AUC > 0.80
        
        return (
            result['metrics']['accuracy'] > 0.75 and
            result['metrics']['roc_auc'] > 0.80
        )
    
    async def _promote_model(self, run_id: str):
        """
        Promueve modelo a producción.
        """
        import mlflow
        
        # Registrar modelo en Model Registry
        client = mlflow.tracking.MlflowClient()
        
        model_uri = f"runs:/{run_id}/model"
        model_version = mlflow.register_model(
            model_uri,
            "devmatrix-success-predictor"
        )
        
        # Transicionar a production
        client.transition_model_version_stage(
            name="devmatrix-success-predictor",
            version=model_version.version,
            stage="Production"
        )
        
        logger.info(f"✅ Model version {model_version.version} promoted to Production")
```

---

## 🔮 Inference Service

### 1. Model Serving

```python
# src/ml/inference/predictor.py

import mlflow
import mlflow.sklearn
from typing import Dict, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    """
    Servicio de inferencia en tiempo real.
    """
    
    def __init__(self, mlflow_tracking_uri: str):
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        self.models = {}
        self._load_models()
    
    def _load_models(self):
        """
        Carga modelos de producción en memoria.
        """
        try:
            # Success Predictor
            self.models['success'] = mlflow.sklearn.load_model(
                "models:/devmatrix-success-predictor/Production"
            )
            logger.info("✅ Success Predictor loaded")
            
            # Complexity Estimator
            # TODO: Cargar cuando esté entrenado
            
            # Time Estimator
            # TODO: Cargar cuando esté entrenado
            
        except Exception as e:
            logger.error(f"❌ Failed to load models: {e}")
    
    def predict_success(self, features: Dict) -> Dict:
        """
        Predice probabilidad de éxito.
        """
        if 'success' not in self.models:
            return {
                'success_probability': 0.5,
                'confidence': 0.0,
                'model_available': False
            }
        
        # Convert to DataFrame
        feature_names = [
            'task_type_encoded', 'language_encoded', 'framework_encoded',
            'task_complexity_score', 'task_description_length',
            'num_requirements', 'num_technical_terms',
            'similar_tasks_success_rate', 'agent_past_performance',
            'model_past_performance', 'rag_examples_count',
            'rag_avg_quality', 'rag_avg_similarity',
            'hour_of_day', 'day_of_week', 'project_maturity_days'
        ]
        
        X = pd.DataFrame([features], columns=feature_names)
        
        # Predict
        proba = self.models['success'].predict_proba(X)[0]
        success_prob = proba[1]
        
        # Confidence (entropy-based)
        import numpy as np
        entropy = -np.sum(proba * np.log2(proba + 1e-10))
        confidence = 1.0 - (entropy / np.log2(2))  # Normalize to [0, 1]
        
        return {
            'success_probability': float(success_prob),
            'confidence': float(confidence),
            'model_available': True,
            'risk_level': self._calculate_risk_level(success_prob)
        }
    
    def _calculate_risk_level(self, success_prob: float) -> str:
        """
        Categoriza nivel de riesgo.
        """
        if success_prob >= 0.85:
            return 'low'
        elif success_prob >= 0.70:
            return 'medium'
        elif success_prob >= 0.50:
            return 'high'
        else:
            return 'very_high'
    
    def reload_models(self):
        """
        Recarga modelos (llamar después de nuevo deploy).
        """
        logger.info("Reloading models...")
        self._load_models()
```

---

## 🎯 Integration con Orchestrator

```python
# src/agents/orchestrator_agent.py (MODIFICAR)

from src.ml.data_collection import MLDataCollector
from src.ml.inference.predictor import MLPredictor
from src.ml.feature_engineering import FeatureEngineer

class OrchestratorAgent:
    def __init__(self):
        # ... código existente ...
        
        # NUEVO: ML components
        self.ml_collector = MLDataCollector(db_connection)
        self.ml_predictor = MLPredictor(mlflow_tracking_uri)
        self.feature_engineer = FeatureEngineer()
    
    async def execute_task_with_ml(
        self,
        task: Dict,
        state: Dict
    ) -> Dict:
        """
        Ejecuta tarea con ML predictions.
        """
        # 1. Registrar inicio
        event_id = await self.ml_collector.record_generation_start(
            task_id=task['id'],
            task_context={
                'task_type': task['type'],
                'task_description': task['description'],
                'language': task.get('language', 'python'),
                'framework': task.get('framework'),
                'agent_type': task['agent'],
                'model_used': 'claude-sonnet-4.5',
                'temperature': 0.1,
                'max_tokens': 8000
            }
        )
        
        # 2. Extract features para prediction
        features = self._extract_features_for_prediction(task, state)
        
        # 3. Predict success probability
        prediction = self.ml_predictor.predict_success(features)
        
        logger.info(f"🔮 ML Prediction: {prediction['success_probability']:.2%} success probability (risk: {prediction['risk_level']})")
        
        # 4. Ajustar estrategia según predicción
        if prediction['risk_level'] == 'very_high':
            # Tarea de alto riesgo: usar estrategia más conservadora
            logger.warning("⚠️ High-risk task detected, using conservative strategy")
            task['temperature'] = 0.05  # Más determinista
            task['use_rag'] = True      # Forzar RAG
            task['max_examples'] = 5    # Más ejemplos
        
        # 5. Ejecutar generación
        start_time = datetime.now()
        result = await self._execute_generation(task, state)
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # 6. Registrar completion
        await self.ml_collector.record_generation_complete(
            event_id=event_id,
            generated_code=result['code'],
            generation_time=generation_time,
            self_review_score=result.get('quality_score', 0),
            metadata={
                'ml_prediction': prediction,
                'strategy_adjusted': prediction['risk_level'] == 'very_high'
            }
        )
        
        # 7. Agregar predicción al resultado
        result['ml_prediction'] = prediction
        result['event_id'] = event_id
        
        return result
    
    async def handle_user_feedback_with_ml(
        self,
        event_id: str,
        action: str,
        feedback: Optional[str],
        final_quality_score: Optional[float]
    ):
        """
        Registra feedback de usuario para ML.
        """
        await self.ml_collector.record_user_feedback(
            event_id=event_id,
            action=action,
            feedback=feedback,
            final_quality_score=final_quality_score
        )
    
    def _extract_features_for_prediction(self, task: Dict, state: Dict) -> Dict:
        """
        Extrae features para predicción en tiempo real.
        """
        # TODO: Implementar extracción real
        return {
            'task_type_encoded': 0,
            'language_encoded': 0,
            'framework_encoded': 0,
            'task_complexity_score': 5.0,
            'task_description_length': len(task['description']),
            'num_requirements': 3,
            'num_technical_terms': 5,
            'similar_tasks_success_rate': 0.75,
            'agent_past_performance': 0.80,
            'model_past_performance': 0.82,
            'rag_examples_count': 3,
            'rag_avg_quality': 8.0,
            'rag_avg_similarity': 0.7,
            'hour_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'project_maturity_days': 14
        }
```

---

## 📊 Dashboard y Monitoring

### 1. ML Metrics Dashboard

```python
# src/api/routes/ml_routes.py

from fastapi import APIRouter, Depends
from src.ml.inference.predictor import MLPredictor
from src.ml.analytics import MLAnalytics

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])

@router.get("/metrics")
async def get_ml_metrics():
    """
    GET /api/ml/metrics
    
    Métricas del sistema ML.
    """
    analytics = MLAnalytics()
    
    return {
        'model_performance': await analytics.get_model_performance(),
        'prediction_accuracy': await analytics.get_prediction_accuracy(),
        'feature_importance': await analytics.get_feature_importance(),
        'data_distribution': await analytics.get_data_distribution()
    }

@router.post("/predict")
async def predict_success(request: Dict):
    """
    POST /api/ml/predict
    
    Predicción de éxito para una tarea.
    """
    predictor = MLPredictor(mlflow_tracking_uri)
    
    prediction = predictor.predict_success(request['features'])
    
    return prediction

@router.post("/retrain")
async def trigger_retraining():
    """
    POST /api/ml/retrain
    
    Trigger manual de reentrenamiento.
    """
    # TODO: Implementar trigger
    return {'status': 'training_started'}
```

---

## 🎯 Timeline de Implementación

### Mes 1: Data Collection & Feature Engineering
- **Semana 1-2**: Schema y data collection
  - [ ] GenerationEvent schema
  - [ ] MLDataCollector service
  - [ ] PostgreSQL tables
  - [ ] Integration con approval flow

- **Semana 3-4**: Feature engineering
  - [ ] FeatureEngineer service
  - [ ] Feature extraction pipeline
  - [ ] Historical features queries
  - [ ] Testing y validación

### Mes 2: Model Development & Training
- **Semana 1-2**: Success Predictor
  - [ ] Model architecture
  - [ ] Training pipeline
  - [ ] Evaluation metrics
  - [ ] MLflow integration

- **Semana 3-4**: Otros modelos
  - [ ] Complexity Estimator
  - [ ] Time Estimator
  - [ ] Quality Score Predictor
  - [ ] Template Selector

### Mes 3: Inference & Integration
- **Semana 1-2**: Inference service
  - [ ] MLPredictor service
  - [ ] Model serving
  - [ ] Caching layer
  - [ ] Performance optimization

- **Semana 3-4**: Integration
  - [ ] Orchestrator integration
  - [ ] Adaptive strategies
  - [ ] A/B testing framework
  - [ ] Monitoring

### Mes 4: Production & Optimization
- **Semana 1-2**: Production deployment
  - [ ] Training scheduler
  - [ ] Model registry
  - [ ] CI/CD para modelos
  - [ ] Monitoring y alerting

- **Semana 3-4**: Optimization
  - [ ] Model performance tuning
  - [ ] Feature selection
  - [ ] Hyperparameter optimization
  - [ ] Documentation completa

---

## 📈 Métricas de Éxito

### Baseline (Sin ML)
```
Success rate: 70-80%
Average quality: 7.5/10
User satisfaction: ???
Time to approval: X minutes
```

### Con ML (Objetivo a 6 meses)
```
Success rate: 85%+ (gracias a predicciones)
Average quality: 8.5+/10
Prediction accuracy: 80%+
Model inference latency: <100ms
Retraining frequency: Daily
Data collection: 100% de generaciones
```

### KPIs a Trackear
1. **Model Accuracy**: Prediction vs actual outcome
2. **Success Rate**: Código aprobado sin modificaciones
3. **Quality Improvement**: Trend de quality scores
4. **Time Savings**: Reducción en regeneraciones
5. **Cost Efficiency**: Costo vs calidad obtenida

---

## 🚀 Next Level: Advanced ML

### Fase 2 (Después de 6 meses)

1. **Reinforcement Learning**
   - Agente que aprende estrategia óptima
   - Reward: quality score + user satisfaction
   
2. **Active Learning**
   - Identificar ejemplos más útiles para entrenar
   - Solicitar feedback selectivo al usuario

3. **Multi-Task Learning**
   - Un modelo que predice múltiples targets
   - Share representations entre tareas

4. **Neural Architecture Search**
   - Búsqueda automática de arquitectura óptima

5. **Federated Learning**
   - Aprender de múltiples usuarios sin compartir datos
   - Privacy-preserving ML

---

## 🎉 Conclusión

El sistema de ML continuo transformará DevMatrix de un generador estático a un **sistema inteligente que mejora constantemente**.

**Key Benefits**:
- ✅ Aprende de cada generación
- ✅ Predice problemas antes de generar
- ✅ Optimiza automáticamente estrategias
- ✅ Mejora calidad progresivamente
- ✅ Reduce costos y tiempo

**Investment**: 3-4 meses dev time
**ROI**: +10% precision, -30% tiempo, continuous improvement

¿Listo para empezar con el data collection schema? 🚀
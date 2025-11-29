"""
Requirements Classifier Trainer - Online Learning for Classification Improvement.

Gap 2 Implementation: Provides online learning capabilities for the
RequirementsClassifier by recording classification results and
periodically retraining when enough samples are collected.

Reference: DOCS/mvp/exit/learning/LEARNING_GAPS_IMPLEMENTATION_PLAN.md Gap 2
"""
import logging
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import numpy as np

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ClassificationSample:
    """
    Record of a single classification result for training.

    Stores both the predicted and actual class to enable
    error analysis and model improvement.
    """
    sample_id: str
    requirement_text: str
    predicted_domain: str
    actual_domain: str
    predicted_priority: str
    actual_priority: Optional[str] = None
    is_correct: bool = False
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ClassifierMetrics:
    """Metrics for classifier performance evaluation."""
    total_samples: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    domain_accuracy: Dict[str, float] = field(default_factory=dict)
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


# =============================================================================
# Requirements Classifier Trainer
# =============================================================================

class RequirementsClassifierTrainer:
    """
    Online learning trainer for RequirementsClassifier.

    Gap 2 Implementation:
    - Records classification results (predicted vs actual)
    - Accumulates misclassified samples for retraining
    - Periodically triggers fine-tuning when threshold met
    - Persists training data to Neo4j for cross-session learning

    Usage:
    ```python
    trainer = RequirementsClassifierTrainer(classifier)

    # After each classification
    trainer.record_result(
        requirement_text="Create a new product",
        predicted_domain="crud",
        actual_domain="crud"  # From validation
    )

    # Check if retraining needed
    if trainer.should_retrain():
        trainer.fine_tune_classifier()
    ```
    """

    # Neo4j node labels
    SAMPLE_LABEL = "ClassificationSample"
    METRICS_LABEL = "ClassifierMetrics"

    def __init__(
        self,
        classifier=None,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "devmatrix123",
        min_samples_for_retrain: int = 30,
        accuracy_threshold: float = 0.6
    ):
        """
        Initialize trainer.

        Args:
            classifier: RequirementsClassifier instance (optional, can set later)
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            min_samples_for_retrain: Minimum misclassified samples before retrain
            accuracy_threshold: Trigger retrain if accuracy falls below this
        """
        self.classifier = classifier
        self.min_samples_for_retrain = min_samples_for_retrain
        self.accuracy_threshold = accuracy_threshold

        # In-memory sample buffer
        self.pending_samples: List[ClassificationSample] = []
        self.misclassified_samples: List[ClassificationSample] = []

        # Neo4j connection
        try:
            self.driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password)
            )
            self._neo4j_available = True
            logger.info("RequirementsClassifierTrainer connected to Neo4j")
        except Exception as e:
            logger.warning(f"Neo4j not available, using in-memory only: {e}")
            self._neo4j_available = False
            self.driver = None

        # Load existing metrics from Neo4j
        self.metrics = self._load_metrics()

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def set_classifier(self, classifier):
        """Set or update the classifier instance."""
        self.classifier = classifier

    def record_result(
        self,
        requirement_text: str,
        predicted_domain: str,
        actual_domain: str,
        predicted_priority: str = "UNKNOWN",
        actual_priority: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ClassificationSample:
        """
        Record a classification result for learning.

        Args:
            requirement_text: The requirement text that was classified
            predicted_domain: Domain predicted by classifier
            actual_domain: Actual domain (from validation/ground truth)
            predicted_priority: Priority predicted by classifier
            actual_priority: Actual priority (if known)
            context: Additional context (endpoint, entity, etc.)

        Returns:
            ClassificationSample record
        """
        import uuid

        is_correct = predicted_domain.lower() == actual_domain.lower()

        sample = ClassificationSample(
            sample_id=f"cs_{uuid.uuid4().hex[:8]}",
            requirement_text=requirement_text,
            predicted_domain=predicted_domain.lower(),
            actual_domain=actual_domain.lower(),
            predicted_priority=predicted_priority,
            actual_priority=actual_priority,
            is_correct=is_correct,
            context=context or {},
            timestamp=datetime.now()
        )

        # Update metrics
        self.metrics.total_samples += 1
        if is_correct:
            self.metrics.correct_predictions += 1
        else:
            self.misclassified_samples.append(sample)

        # Update accuracy
        if self.metrics.total_samples > 0:
            self.metrics.accuracy = (
                self.metrics.correct_predictions / self.metrics.total_samples
            )

        # Update confusion matrix
        if actual_domain not in self.metrics.confusion_matrix:
            self.metrics.confusion_matrix[actual_domain] = {}
        if predicted_domain not in self.metrics.confusion_matrix[actual_domain]:
            self.metrics.confusion_matrix[actual_domain][predicted_domain] = 0
        self.metrics.confusion_matrix[actual_domain][predicted_domain] += 1

        # Persist to Neo4j
        self._persist_sample(sample)

        # Log progress
        if self.metrics.total_samples % 10 == 0:
            logger.info(
                f"Classification accuracy: {self.metrics.accuracy:.1%} "
                f"({self.metrics.correct_predictions}/{self.metrics.total_samples})"
            )

        return sample

    def should_retrain(self) -> bool:
        """
        Check if classifier should be retrained.

        Returns:
            True if retraining conditions are met
        """
        # Condition 1: Enough misclassified samples
        if len(self.misclassified_samples) >= self.min_samples_for_retrain:
            logger.info(
                f"Retrain trigger: {len(self.misclassified_samples)} "
                f"misclassified samples (threshold: {self.min_samples_for_retrain})"
            )
            return True

        # Condition 2: Accuracy below threshold (need minimum samples)
        if (self.metrics.total_samples >= 20 and
                self.metrics.accuracy < self.accuracy_threshold):
            logger.info(
                f"Retrain trigger: accuracy {self.metrics.accuracy:.1%} "
                f"below threshold {self.accuracy_threshold:.1%}"
            )
            return True

        return False

    def fine_tune_classifier(self) -> Dict[str, Any]:
        """
        Fine-tune the classifier using accumulated misclassified samples.

        Gap 2 Implementation:
        1. Analyzes misclassification patterns
        2. Updates domain templates with corrected examples
        3. Adjusts keyword weights based on error analysis

        Returns:
            Dict with fine-tuning results
        """
        if not self.classifier:
            logger.error("No classifier set for fine-tuning")
            return {"error": "No classifier set"}

        if not self.misclassified_samples:
            logger.info("No misclassified samples to learn from")
            return {"status": "no_samples"}

        logger.info(f"Fine-tuning classifier with {len(self.misclassified_samples)} samples...")

        results = {
            "samples_processed": len(self.misclassified_samples),
            "domain_updates": {},
            "keyword_additions": {},
            "template_updates": 0
        }

        # Group misclassifications by actual domain
        by_actual_domain: Dict[str, List[ClassificationSample]] = {}
        for sample in self.misclassified_samples:
            if sample.actual_domain not in by_actual_domain:
                by_actual_domain[sample.actual_domain] = []
            by_actual_domain[sample.actual_domain].append(sample)

        # Update domain templates with misclassified examples
        for domain, samples in by_actual_domain.items():
            if hasattr(self.classifier, 'domain_templates') and self.classifier.domain_templates:
                self._update_domain_template(domain, samples)
                results["template_updates"] += 1
                results["domain_updates"][domain] = len(samples)

            # Extract keywords from misclassified samples
            new_keywords = self._extract_keywords_from_samples(samples)
            if new_keywords:
                self._add_keywords_to_domain(domain, new_keywords)
                results["keyword_additions"][domain] = new_keywords

        # Clear processed samples
        processed_count = len(self.misclassified_samples)
        self.misclassified_samples = []

        # Persist updated metrics
        self._persist_metrics()

        logger.info(
            f"Fine-tuning complete: {processed_count} samples processed, "
            f"{results['template_updates']} templates updated"
        )

        return results

    def _update_domain_template(self, domain: str, samples: List[ClassificationSample]):
        """
        Update domain template embedding with new examples.

        Args:
            domain: Domain to update
            samples: Misclassified samples that should belong to this domain
        """
        if not self.classifier or not hasattr(self.classifier, 'embedding_model'):
            return

        if not self.classifier.embedding_model:
            return

        try:
            # Create text from samples
            sample_texts = [s.requirement_text for s in samples[:5]]  # Limit to 5
            combined_text = " ".join(sample_texts)

            # Encode new text
            new_embedding = self.classifier.embedding_model.encode(
                combined_text,
                convert_to_numpy=True
            )

            # Weighted average with existing template (80% old, 20% new)
            if domain in self.classifier.domain_templates:
                old_embedding = self.classifier.domain_templates[domain]
                updated_embedding = 0.8 * old_embedding + 0.2 * new_embedding
                # Normalize
                updated_embedding = updated_embedding / np.linalg.norm(updated_embedding)
                self.classifier.domain_templates[domain] = updated_embedding
                logger.info(f"Updated domain template for '{domain}' with {len(samples)} examples")

        except Exception as e:
            logger.error(f"Failed to update domain template: {e}")

    def _extract_keywords_from_samples(self, samples: List[ClassificationSample]) -> List[str]:
        """
        Extract common keywords from misclassified samples.

        Args:
            samples: Samples that were misclassified

        Returns:
            List of potential new keywords
        """
        import re
        from collections import Counter

        # Tokenize all samples
        all_words = []
        for sample in samples:
            # Extract words (alphanumeric, 3+ chars)
            words = re.findall(r'\b[a-záéíóúñ]{3,}\b', sample.requirement_text.lower())
            all_words.extend(words)

        # Find common words (appear in >50% of samples)
        word_counts = Counter(all_words)
        threshold = len(samples) * 0.5

        # Filter out common stop words
        stop_words = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have',
            'para', 'con', 'una', 'que', 'los', 'las', 'del', 'por'
        }

        new_keywords = [
            word for word, count in word_counts.items()
            if count >= threshold and word not in stop_words
        ][:5]  # Limit to 5 new keywords

        return new_keywords

    def _add_keywords_to_domain(self, domain: str, keywords: List[str]):
        """
        Add new keywords to a domain's keyword list.

        Args:
            domain: Domain to update
            keywords: New keywords to add
        """
        if not self.classifier or not hasattr(self.classifier, 'domain_keywords'):
            return

        if domain in self.classifier.domain_keywords:
            existing = set(self.classifier.domain_keywords[domain])
            new_kws = [kw for kw in keywords if kw not in existing]
            if new_kws:
                self.classifier.domain_keywords[domain].extend(new_kws)
                logger.info(f"Added keywords to '{domain}': {new_kws}")

    def _persist_sample(self, sample: ClassificationSample):
        """Persist sample to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                session.run(f"""
                    CREATE (s:{self.SAMPLE_LABEL} {{
                        sample_id: $sample_id,
                        requirement_text: $text,
                        predicted_domain: $predicted,
                        actual_domain: $actual,
                        is_correct: $is_correct,
                        timestamp: datetime()
                    }})
                """, {
                    "sample_id": sample.sample_id,
                    "text": sample.requirement_text[:500],
                    "predicted": sample.predicted_domain,
                    "actual": sample.actual_domain,
                    "is_correct": sample.is_correct
                })
        except Exception as e:
            logger.warning(f"Failed to persist sample: {e}")

    def _persist_metrics(self):
        """Persist current metrics to Neo4j."""
        if not self._neo4j_available or not self.driver:
            return

        try:
            with self.driver.session() as session:
                session.run(f"""
                    MERGE (m:{self.METRICS_LABEL} {{name: 'requirements_classifier'}})
                    SET m.total_samples = $total,
                        m.correct_predictions = $correct,
                        m.accuracy = $accuracy,
                        m.confusion_matrix = $confusion,
                        m.last_updated = datetime()
                """, {
                    "total": self.metrics.total_samples,
                    "correct": self.metrics.correct_predictions,
                    "accuracy": self.metrics.accuracy,
                    "confusion": json.dumps(self.metrics.confusion_matrix)
                })
        except Exception as e:
            logger.warning(f"Failed to persist metrics: {e}")

    def _load_metrics(self) -> ClassifierMetrics:
        """Load metrics from Neo4j or return defaults."""
        if not self._neo4j_available or not self.driver:
            return ClassifierMetrics()

        try:
            with self.driver.session() as session:
                result = session.run(f"""
                    MATCH (m:{self.METRICS_LABEL} {{name: 'requirements_classifier'}})
                    RETURN m
                """)
                record = result.single()

                if record:
                    m = record["m"]
                    confusion = json.loads(m.get("confusion_matrix", "{}"))
                    return ClassifierMetrics(
                        total_samples=m.get("total_samples", 0),
                        correct_predictions=m.get("correct_predictions", 0),
                        accuracy=m.get("accuracy", 0.0),
                        confusion_matrix=confusion
                    )
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")

        return ClassifierMetrics()

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get a detailed performance report.

        Returns:
            Dict with performance metrics and analysis
        """
        report = {
            "total_samples": self.metrics.total_samples,
            "correct_predictions": self.metrics.correct_predictions,
            "accuracy": f"{self.metrics.accuracy:.1%}",
            "misclassified_pending": len(self.misclassified_samples),
            "confusion_matrix": self.metrics.confusion_matrix,
            "needs_retraining": self.should_retrain()
        }

        # Domain-specific accuracy
        if self.metrics.confusion_matrix:
            domain_accuracy = {}
            for actual, predictions in self.metrics.confusion_matrix.items():
                total = sum(predictions.values())
                correct = predictions.get(actual, 0)
                if total > 0:
                    domain_accuracy[actual] = f"{correct / total:.1%}"
            report["domain_accuracy"] = domain_accuracy

        return report

    def load_misclassified_from_neo4j(self, limit: int = 100) -> List[ClassificationSample]:
        """
        Load misclassified samples from Neo4j for batch retraining.

        Args:
            limit: Maximum samples to load

        Returns:
            List of misclassified samples
        """
        if not self._neo4j_available or not self.driver:
            return []

        try:
            with self.driver.session() as session:
                result = session.run(f"""
                    MATCH (s:{self.SAMPLE_LABEL})
                    WHERE s.is_correct = false
                    RETURN s
                    ORDER BY s.timestamp DESC
                    LIMIT $limit
                """, limit=limit)

                samples = []
                for record in result:
                    s = record["s"]
                    samples.append(ClassificationSample(
                        sample_id=s["sample_id"],
                        requirement_text=s["requirement_text"],
                        predicted_domain=s["predicted_domain"],
                        actual_domain=s["actual_domain"],
                        is_correct=False
                    ))
                return samples
        except Exception as e:
            logger.error(f"Failed to load samples: {e}")
            return []


# =============================================================================
# Singleton Instance
# =============================================================================

_classifier_trainer: Optional[RequirementsClassifierTrainer] = None


def get_classifier_trainer() -> RequirementsClassifierTrainer:
    """Get singleton instance of RequirementsClassifierTrainer."""
    global _classifier_trainer
    if _classifier_trainer is None:
        import os
        _classifier_trainer = RequirementsClassifierTrainer(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "devmatrix123")
        )
    return _classifier_trainer

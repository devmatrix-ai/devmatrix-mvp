"""
Error Pattern Analyzer - Cognitive Feedback Loop Analysis

Analyzes error patterns to detect recurring issues, problematic tasks,
and measure the effectiveness of the feedback loop learning.

Purpose: Identify systemic issues and measure ML learning effectiveness
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter

from src.services.error_pattern_store import ErrorPatternStore, get_error_pattern_store
from src.observability import get_logger

logger = get_logger("services.error_pattern_analyzer")


@dataclass
class ErrorCluster:
    """Cluster of similar errors."""
    cluster_id: str
    error_count: int
    avg_similarity: float
    common_error_type: str
    common_task_description: str
    error_ids: List[str]
    first_seen: datetime
    last_seen: datetime
    is_recurring: bool


@dataclass
class ProblematicTask:
    """Task that consistently fails."""
    task_description: str
    failure_count: int
    success_count: int
    failure_rate: float
    common_error_types: List[str]
    last_failure: datetime


@dataclass
class LearningMetrics:
    """Metrics measuring feedback loop effectiveness."""
    total_errors: int
    errors_with_feedback: int
    success_rate_without_feedback: float
    success_rate_with_feedback: float
    improvement_percentage: float
    avg_retries_without_feedback: float
    avg_retries_with_feedback: float


class ErrorPatternAnalyzer:
    """
    Analyzes error patterns to detect recurring issues and measure learning.

    Features:
    - Detects recurring error patterns
    - Identifies problematic task types
    - Measures feedback loop effectiveness
    - Generates improvement recommendations
    """

    def __init__(self, pattern_store: Optional[ErrorPatternStore] = None):
        """
        Initialize error pattern analyzer.

        Args:
            pattern_store: ErrorPatternStore instance (creates new if not provided)
        """
        self.pattern_store = pattern_store or get_error_pattern_store()
        self.logger = logger

    async def analyze_recurring_errors(
        self,
        time_window_hours: int = 24,
        min_occurrences: int = 3
    ) -> List[ErrorCluster]:
        """
        Detect recurring error patterns in time window.

        Args:
            time_window_hours: Time window to analyze
            min_occurrences: Minimum occurrences to consider recurring

        Returns:
            List of error clusters representing recurring patterns
        """
        try:
            # Get error statistics from Neo4j
            with self.pattern_store.neo4j_driver.session() as session:
                # Get all errors in time window
                result = session.run(f"""
                    MATCH (e:CodeGenerationError)
                    WHERE e.timestamp > datetime() - duration('PT{time_window_hours}H')
                    RETURN
                        e.error_id AS error_id,
                        e.error_type AS error_type,
                        e.task_description AS task_description,
                        e.error_message AS error_message,
                        e.timestamp AS timestamp
                    ORDER BY e.timestamp DESC
                """)

                errors = [dict(record) for record in result]

            if len(errors) < min_occurrences:
                self.logger.info(
                    f"Not enough errors to analyze ({len(errors)} < {min_occurrences})"
                )
                return []

            # Group errors by error message similarity
            error_groups = defaultdict(list)
            for error in errors:
                # Simplified grouping by error type + first 100 chars of message
                key = f"{error['error_type']}:{error['error_message'][:100]}"
                error_groups[key].append(error)

            # Create clusters for recurring patterns
            clusters = []
            for group_key, group_errors in error_groups.items():
                if len(group_errors) >= min_occurrences:
                    error_ids = [e['error_id'] for e in group_errors]
                    timestamps = [e['timestamp'] for e in group_errors]

                    cluster = ErrorCluster(
                        cluster_id=str(uuid.uuid4()),
                        error_count=len(group_errors),
                        avg_similarity=0.85,  # Simplified - could use actual embeddings
                        common_error_type=group_errors[0]['error_type'],
                        common_task_description=group_errors[0]['task_description'],
                        error_ids=error_ids,
                        first_seen=min(timestamps),
                        last_seen=max(timestamps),
                        is_recurring=True
                    )
                    clusters.append(cluster)

            self.logger.info(
                f"Found {len(clusters)} recurring error clusters",
                extra={"time_window_hours": time_window_hours}
            )

            return clusters

        except Exception as e:
            self.logger.error(f"Failed to analyze recurring errors: {e}")
            return []

    async def identify_problematic_tasks(
        self,
        failure_rate_threshold: float = 0.5,
        min_attempts: int = 3
    ) -> List[ProblematicTask]:
        """
        Identify task types that consistently fail.

        Args:
            failure_rate_threshold: Minimum failure rate to flag (0.0-1.0)
            min_attempts: Minimum attempts required for analysis

        Returns:
            List of problematic tasks
        """
        try:
            with self.pattern_store.neo4j_driver.session() as session:
                # Get error counts by task description
                error_result = session.run("""
                    MATCH (e:CodeGenerationError)
                    RETURN
                        e.task_description AS task_description,
                        count(e) AS failure_count,
                        collect(e.error_type) AS error_types,
                        max(e.timestamp) AS last_failure
                """)

                error_data = {
                    record['task_description']: {
                        'failures': record['failure_count'],
                        'error_types': record['error_types'],
                        'last_failure': record['last_failure']
                    }
                    for record in error_result
                }

                # Get success counts by task description
                success_result = session.run("""
                    MATCH (s:SuccessfulCode)
                    RETURN
                        s.task_description AS task_description,
                        count(s) AS success_count
                """)

                success_data = {
                    record['task_description']: record['success_count']
                    for record in success_result
                }

            # Calculate failure rates
            problematic = []
            for task_desc, error_info in error_data.items():
                failures = error_info['failures']
                successes = success_data.get(task_desc, 0)
                total = failures + successes

                if total >= min_attempts:
                    failure_rate = failures / total

                    if failure_rate >= failure_rate_threshold:
                        # Get most common error types
                        error_type_counts = Counter(error_info['error_types'])
                        common_errors = [
                            error_type for error_type, _ in error_type_counts.most_common(3)
                        ]

                        problematic.append(ProblematicTask(
                            task_description=task_desc,
                            failure_count=failures,
                            success_count=successes,
                            failure_rate=failure_rate,
                            common_error_types=common_errors,
                            last_failure=error_info['last_failure']
                        ))

            # Sort by failure rate (highest first)
            problematic.sort(key=lambda x: x.failure_rate, reverse=True)

            self.logger.info(
                f"Identified {len(problematic)} problematic task types",
                extra={"threshold": failure_rate_threshold}
            )

            return problematic

        except Exception as e:
            self.logger.error(f"Failed to identify problematic tasks: {e}")
            return []

    async def calculate_learning_effectiveness(
        self,
        time_window_hours: int = 24
    ) -> LearningMetrics:
        """
        Measure effectiveness of cognitive feedback loop.

        Args:
            time_window_hours: Time window for analysis

        Returns:
            Learning metrics showing improvement
        """
        try:
            with self.pattern_store.neo4j_driver.session() as session:
                # Get total errors in window
                total_result = session.run(f"""
                    MATCH (e:CodeGenerationError)
                    WHERE e.timestamp > datetime() - duration('PT{time_window_hours}H')
                    RETURN count(e) AS total
                """)
                total_errors = total_result.single()['total']

                # Get errors where feedback was used (attempt > 1)
                feedback_result = session.run(f"""
                    MATCH (e:CodeGenerationError)
                    WHERE e.timestamp > datetime() - duration('PT{time_window_hours}H')
                      AND e.attempt > 1
                    RETURN count(e) AS with_feedback
                """)
                errors_with_feedback = feedback_result.single()['with_feedback']

                # Get success counts by feedback usage
                success_result = session.run(f"""
                    MATCH (s:SuccessfulCode)
                    WHERE s.timestamp > datetime() - duration('PT{time_window_hours}H')
                    RETURN
                        s.metadata.used_feedback AS used_feedback,
                        count(s) AS count,
                        avg(s.metadata.attempt) AS avg_attempt
                """)

                success_stats = {
                    record['used_feedback']: {
                        'count': record['count'],
                        'avg_attempt': record['avg_attempt']
                    }
                    for record in success_result
                }

            # Calculate metrics
            with_feedback_successes = success_stats.get(True, {}).get('count', 0)
            without_feedback_successes = success_stats.get(False, {}).get('count', 0)

            with_feedback_total = with_feedback_successes + errors_with_feedback
            without_feedback_total = without_feedback_successes + (total_errors - errors_with_feedback)

            success_rate_with_feedback = (
                with_feedback_successes / with_feedback_total
                if with_feedback_total > 0 else 0.0
            )

            success_rate_without_feedback = (
                without_feedback_successes / without_feedback_total
                if without_feedback_total > 0 else 0.0
            )

            improvement = (
                ((success_rate_with_feedback - success_rate_without_feedback) / success_rate_without_feedback * 100)
                if success_rate_without_feedback > 0 else 0.0
            )

            avg_retries_with = success_stats.get(True, {}).get('avg_attempt', 1.0)
            avg_retries_without = success_stats.get(False, {}).get('avg_attempt', 1.0)

            metrics = LearningMetrics(
                total_errors=total_errors,
                errors_with_feedback=errors_with_feedback,
                success_rate_without_feedback=success_rate_without_feedback,
                success_rate_with_feedback=success_rate_with_feedback,
                improvement_percentage=improvement,
                avg_retries_without_feedback=avg_retries_without,
                avg_retries_with_feedback=avg_retries_with
            )

            self.logger.info(
                "Learning effectiveness calculated",
                extra={
                    "improvement": f"{improvement:.1f}%",
                    "success_with_feedback": f"{success_rate_with_feedback:.2%}",
                    "success_without_feedback": f"{success_rate_without_feedback:.2%}"
                }
            )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to calculate learning effectiveness: {e}")
            return LearningMetrics(
                total_errors=0,
                errors_with_feedback=0,
                success_rate_without_feedback=0.0,
                success_rate_with_feedback=0.0,
                improvement_percentage=0.0,
                avg_retries_without_feedback=0.0,
                avg_retries_with_feedback=0.0
            )

    async def generate_improvement_recommendations(
        self,
        clusters: List[ErrorCluster],
        problematic_tasks: List[ProblematicTask],
        learning_metrics: LearningMetrics
    ) -> Dict[str, Any]:
        """
        Generate actionable improvement recommendations.

        Args:
            clusters: Recurring error clusters
            problematic_tasks: Consistently failing tasks
            learning_metrics: Learning effectiveness metrics

        Returns:
            Dict with categorized recommendations
        """
        recommendations = {
            "critical_issues": [],
            "optimization_opportunities": [],
            "system_insights": [],
            "learning_status": {}
        }

        # Critical issues from recurring clusters
        if clusters:
            for cluster in clusters[:3]:  # Top 3 most frequent
                recommendations["critical_issues"].append({
                    "type": "recurring_error",
                    "severity": "high",
                    "description": f"Error '{cluster.common_error_type}' occurred {cluster.error_count} times",
                    "task_pattern": cluster.common_task_description[:100],
                    "recommendation": "Investigate root cause and add specific validation"
                })

        # Problematic tasks
        if problematic_tasks:
            for task in problematic_tasks[:3]:  # Top 3 highest failure rate
                recommendations["critical_issues"].append({
                    "type": "problematic_task",
                    "severity": "high" if task.failure_rate > 0.8 else "medium",
                    "description": f"Task type fails {task.failure_rate:.1%} of the time",
                    "task_description": task.task_description[:100],
                    "failure_count": task.failure_count,
                    "common_errors": task.common_error_types,
                    "recommendation": "Review task description or add explicit constraints"
                })

        # Learning effectiveness insights
        if learning_metrics.improvement_percentage < 10:
            recommendations["optimization_opportunities"].append({
                "type": "low_learning_improvement",
                "severity": "medium",
                "description": f"Feedback loop only improving success rate by {learning_metrics.improvement_percentage:.1f}%",
                "recommendation": "Consider enriching error patterns with more context or examples"
            })
        elif learning_metrics.improvement_percentage > 30:
            recommendations["system_insights"].append({
                "type": "effective_learning",
                "description": f"Feedback loop improving success rate by {learning_metrics.improvement_percentage:.1f}%",
                "insight": "Learning system is working well - continue monitoring"
            })

        # Learning status summary
        recommendations["learning_status"] = {
            "total_errors_analyzed": learning_metrics.total_errors,
            "feedback_loop_usage": f"{learning_metrics.errors_with_feedback}/{learning_metrics.total_errors}",
            "success_rate_improvement": f"{learning_metrics.improvement_percentage:.1f}%",
            "is_learning_effective": learning_metrics.improvement_percentage > 10
        }

        self.logger.info(
            "Generated improvement recommendations",
            extra={
                "critical_issues": len(recommendations["critical_issues"]),
                "optimization_opportunities": len(recommendations["optimization_opportunities"])
            }
        )

        return recommendations


# Singleton instance
_error_pattern_analyzer: Optional[ErrorPatternAnalyzer] = None


def get_error_pattern_analyzer() -> ErrorPatternAnalyzer:
    """Get singleton instance of ErrorPatternAnalyzer."""
    global _error_pattern_analyzer
    if _error_pattern_analyzer is None:
        _error_pattern_analyzer = ErrorPatternAnalyzer()
    return _error_pattern_analyzer

"""
Health Check System

Provides health monitoring for system components with
detailed status reporting.
"""

import time
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for a component."""

    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["last_check"] = self.last_check.isoformat()
        return data


class HealthCheck:
    """
    System health monitoring.

    Provides comprehensive health checking for all system
    components with detailed status reporting.

    Example:
        >>> health = HealthCheck()
        >>> health.register("database", check_database)
        >>> health.register("redis", check_redis)
        >>> status = health.check_all()
        >>> print(status["status"])  # "healthy" or "degraded" or "unhealthy"
    """

    def __init__(self):
        """Initialize health check system."""
        self._checks: Dict[str, Callable[[], ComponentHealth]] = {}
        self._last_results: Dict[str, ComponentHealth] = {}

    def register(
        self,
        name: str,
        check_func: Callable[[], ComponentHealth],
    ):
        """
        Register health check function.

        Args:
            name: Component name
            check_func: Function that returns ComponentHealth
        """
        self._checks[name] = check_func

    def check_component(self, name: str) -> ComponentHealth:
        """
        Check specific component health.

        Args:
            name: Component name

        Returns:
            Component health status
        """
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Component '{name}' not registered",
            )

        start_time = time.time()
        try:
            result = self._checks[name]()
            result.latency_ms = (time.time() - start_time) * 1000
            self._last_results[name] = result
            return result
        except Exception as e:
            result = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000,
            )
            self._last_results[name] = result
            return result

    def check_all(self) -> Dict[str, Any]:
        """
        Check all registered components.

        Returns:
            Dictionary with overall status and component details
        """
        results = {}
        for name in self._checks:
            results[name] = self.check_component(name)

        # Determine overall status
        statuses = [r.status for r in results.values()]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "components": {
                name: health.to_dict()
                for name, health in results.items()
            },
        }

    def get_last_results(self) -> Dict[str, ComponentHealth]:
        """Get last health check results."""
        return self._last_results.copy()

    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        status = self.check_all()
        return status["status"] == HealthStatus.HEALTHY.value


# Utility functions for common health checks
def create_redis_health_check(redis_manager) -> Callable[[], ComponentHealth]:
    """
    Create Redis health check function.

    Args:
        redis_manager: RedisManager instance

    Returns:
        Health check function
    """
    def check():
        try:
            redis_manager.client.ping()
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis connection healthy",
            )
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}",
            )
    return check


def create_postgres_health_check(postgres_manager) -> Callable[[], ComponentHealth]:
    """
    Create PostgreSQL health check function.

    Args:
        postgres_manager: PostgresManager instance

    Returns:
        Health check function
    """
    def check():
        try:
            # Try a simple query
            with postgres_manager.engine.connect() as conn:
                conn.execute("SELECT 1")
            return ComponentHealth(
                name="postgres",
                status=HealthStatus.HEALTHY,
                message="PostgreSQL connection healthy",
            )
        except Exception as e:
            return ComponentHealth(
                name="postgres",
                status=HealthStatus.UNHEALTHY,
                message=f"PostgreSQL connection failed: {str(e)}",
            )
    return check


def create_api_health_check(api_url: str) -> Callable[[], ComponentHealth]:
    """
    Create API health check function.

    Args:
        api_url: API endpoint URL

    Returns:
        Health check function
    """
    def check():
        try:
            import requests
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                return ComponentHealth(
                    name="api",
                    status=HealthStatus.HEALTHY,
                    message=f"API responding: {response.status_code}",
                )
            else:
                return ComponentHealth(
                    name="api",
                    status=HealthStatus.DEGRADED,
                    message=f"API degraded: {response.status_code}",
                )
        except Exception as e:
            return ComponentHealth(
                name="api",
                status=HealthStatus.UNHEALTHY,
                message=f"API unreachable: {str(e)}",
            )
    return check

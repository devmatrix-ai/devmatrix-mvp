"""
Example Custom Tool Plugin

Demonstrates how to create custom tool plugins that can be used
by agents in the Devmatrix system.
"""

from typing import Any, Dict, List

from src.plugins.base import BasePlugin, PluginMetadata, PluginType


class WebScraperTool(BasePlugin):
    """
    Custom tool plugin for web scraping.

    Shows how to create a tool that agents can use during execution.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web-scraper-tool",
            version="1.0.0",
            author="Devmatrix Team",
            description="Scrapes and extracts data from web pages",
            plugin_type=PluginType.TOOL,
            dependencies=["requests", "beautifulsoup4"],
            tags=["web", "scraping", "extraction"],
        )

    def initialize(self) -> None:
        """Initialize web scraper configuration."""
        self.user_agent = self.config.get(
            "user_agent", "Devmatrix-Bot/1.0"
        )
        self.timeout = self.config.get("timeout", 30)
        print(f"Initialized {self.metadata.name}")

    def validate(self) -> bool:
        """Validate tool configuration."""
        # Check timeout is positive
        if self.config.get("timeout", 30) <= 0:
            return False
        return True

    def scrape_url(self, url: str, selectors: List[str]) -> Dict[str, Any]:
        """
        Scrape data from a URL using CSS selectors.

        Args:
            url: URL to scrape
            selectors: List of CSS selectors to extract

        Returns:
            Dictionary with extracted data
        """
        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        # Mock scraping - in production, use requests + BeautifulSoup
        return {
            "url": url,
            "status": "success",
            "data": {selector: f"Mock data for {selector}" for selector in selectors},
            "timestamp": "2025-10-13T00:00:00Z",
        }

    def cleanup(self) -> None:
        """Clean up any open connections."""
        super().cleanup()
        print(f"Cleaned up {self.metadata.name}")


class DatabaseQueryTool(BasePlugin):
    """
    Custom tool for database queries.

    Example of a tool plugin that provides database access to agents.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="database-query-tool",
            version="1.0.0",
            author="Devmatrix Team",
            description="Executes safe database queries",
            plugin_type=PluginType.TOOL,
            dependencies=["sqlalchemy"],
            tags=["database", "query", "sql"],
        )

    def initialize(self) -> None:
        """Initialize database connection."""
        self.connection_string = self.config.get("connection_string")
        self.read_only = self.config.get("read_only", True)
        # In production, establish actual connection
        self.connected = True
        print(f"Initialized {self.metadata.name}")

    def validate(self) -> bool:
        """Validate database configuration."""
        if not self.config.get("connection_string"):
            print("Missing connection_string in config")
            return False
        return True

    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """
        Execute a database query safely.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        if not self.read_only and ("INSERT" in query.upper() or "UPDATE" in query.upper() or "DELETE" in query.upper()):
            raise RuntimeError("Write operations not allowed in read-only mode")

        # Mock query execution
        return [
            {"id": 1, "name": "Mock Result 1"},
            {"id": 2, "name": "Mock Result 2"},
        ]

    def cleanup(self) -> None:
        """Close database connection."""
        super().cleanup()
        self.connected = False
        print(f"Cleaned up {self.metadata.name}")

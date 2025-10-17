"""
Example Custom Agent Plugin

Demonstrates how to create a custom agent plugin that integrates
with the Devmatrix multi-agent system.
"""

from typing import Any, Dict, Optional

from src.plugins.base import BasePlugin, PluginMetadata, PluginType


class SentimentAnalysisAgent(BasePlugin):
    """
    Custom agent that performs sentiment analysis on text.

    This example shows how to create a specialized agent plugin
    that can be dynamically loaded and used in workflows.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sentiment-analysis-agent",
            version="1.0.0",
            author="Devmatrix Team",
            description="Analyzes text sentiment using NLP techniques",
            plugin_type=PluginType.AGENT,
            dependencies=["transformers", "torch"],
            tags=["nlp", "sentiment", "analysis"],
        )

    def initialize(self) -> None:
        """
        Initialize the sentiment analysis model.

        In a real implementation, this would load a pre-trained model.
        """
        # Mock initialization - in production, load actual model
        self.model_loaded = True
        print(f"Initialized {self.metadata.name}")

    def validate(self) -> bool:
        """
        Validate that required dependencies are available.

        Returns:
            True if plugin is ready to use
        """
        # Check configuration
        required_keys = ["model_name", "threshold"]
        for key in required_keys:
            if key not in self.config:
                print(f"Missing required config: {key}")
                return False

        # In production, check if dependencies are installed
        return True

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of input text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis results

        Note:
            This is a MOCK implementation for demonstration purposes.

            For production, replace with real sentiment analysis:
            - transformers: Use HuggingFace sentiment models
              (e.g., "distilbert-base-uncased-finetuned-sst-2-english")
            - TextBlob: Simple polarity/subjectivity scoring
            - VADER: Rule-based sentiment for social media text
            - spaCy: With custom sentiment training

            Example production implementation:
            ```python
            from transformers import pipeline
            classifier = pipeline("sentiment-analysis")
            result = classifier(text)[0]
            return {
                "sentiment": result["label"].lower(),
                "confidence": result["score"],
                "model": "distilbert-base-uncased-finetuned-sst-2-english"
            }
            ```
        """
        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        # MOCK IMPLEMENTATION - Replace in production
        # This dummy score is based on text length modulo 100
        # and does NOT represent actual sentiment
        score = len(text) % 100 / 100  # Dummy metric
        sentiment = "positive" if score > 0.5 else "negative"

        return {
            "text": text,
            "sentiment": sentiment,
            "confidence": score,
            "model": self.config.get("model_name", "mock-model"),
            "_mock": True,  # Flag indicating this is mock data
        }

    def cleanup(self) -> None:
        """Clean up model resources."""
        super().cleanup()
        self.model_loaded = False
        print(f"Cleaned up {self.metadata.name}")


class DataValidationAgent(BasePlugin):
    """
    Custom agent that validates data structures.

    Example of a simpler agent plugin for data validation tasks.
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="data-validation-agent",
            version="1.0.0",
            author="Devmatrix Team",
            description="Validates data structures against schemas",
            plugin_type=PluginType.AGENT,
            dependencies=["jsonschema"],
            tags=["validation", "data", "schema"],
        )

    def initialize(self) -> None:
        """Initialize validator."""
        self.validation_rules = self.config.get("rules", {})
        print(f"Initialized {self.metadata.name}")

    def validate(self) -> bool:
        """Validate plugin is ready."""
        # Simple validation - just check if rules are provided
        return isinstance(self.validation_rules, dict)

    def validate_data(self, data: Dict[str, Any], schema: str) -> Dict[str, Any]:
        """
        Validate data against a schema.

        Args:
            data: Data to validate
            schema: Schema identifier

        Returns:
            Validation results
        """
        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        # Mock validation
        is_valid = isinstance(data, dict)

        return {
            "valid": is_valid,
            "schema": schema,
            "errors": [] if is_valid else ["Data must be a dictionary"],
        }

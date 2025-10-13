# Plugin System Developer Guide

The Devmatrix plugin system allows developers to extend the framework with custom agents, tools, workflows, and middleware without modifying the core codebase.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Types](#plugin-types)
- [Plugin Lifecycle](#plugin-lifecycle)
- [Loading Plugins](#loading-plugins)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Architecture Overview

The plugin system consists of three main components:

1. **BasePlugin**: Abstract base class that all plugins must inherit from
2. **PluginLoader**: Discovers and loads plugins from filesystem
3. **PluginRegistry**: Central registry for managing loaded plugins

### Plugin Architecture Diagram

```
┌─────────────────────────────────────────┐
│          PluginRegistry                 │
│  ┌────────────────────────────────────┐ │
│  │  Loaded Plugins:                   │ │
│  │  - my-agent (enabled)              │ │
│  │  - web-scraper-tool (enabled)      │ │
│  │  - custom-workflow (disabled)      │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Lazy-Loaded Classes:              │ │
│  │  - data-validator                  │ │
│  │  - sentiment-analyzer              │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
           │
           │ discovers & loads
           ▼
┌─────────────────────────────────────────┐
│          PluginLoader                   │
│  - Scans directories                    │
│  - Validates plugins                    │
│  - Instantiates classes                 │
└─────────────────────────────────────────┘
           │
           │ loads from
           ▼
┌─────────────────────────────────────────┐
│      Plugin Directory                   │
│  my_custom_agent.py                     │
│  web_scraper_tool.py                    │
│  data_validator.py                      │
└─────────────────────────────────────────┘
```

## Creating a Plugin

### Step 1: Define Plugin Metadata

Every plugin must define metadata describing its identity, capabilities, and dependencies:

```python
from src.plugins.base import BasePlugin, PluginMetadata, PluginType

class MyCustomAgent(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-custom-agent",
            version="1.0.0",
            author="Your Name",
            description="A custom agent for specific tasks",
            plugin_type=PluginType.AGENT,
            dependencies=["requests", "pandas"],
            tags=["data-processing", "analysis"],
        )
```

### Step 2: Implement Required Methods

All plugins must implement three abstract methods:

#### initialize()

Called once when the plugin is first loaded. Use for expensive setup:

```python
def initialize(self) -> None:
    """Initialize plugin resources."""
    self.api_key = self.get_config("api_key")
    self.model = load_ml_model(self.config.get("model_path"))
    self.cache = {}
    print(f"Initialized {self.metadata.name}")
```

#### validate()

Checks if the plugin is properly configured and ready to use:

```python
def validate(self) -> bool:
    """Validate plugin configuration."""
    # Check required config
    if not self.get_config("api_key"):
        print("Missing required config: api_key")
        return False

    # Check dependencies
    try:
        import requests
        import pandas
    except ImportError:
        print("Missing required dependencies")
        return False

    return True
```

#### cleanup() (optional override)

Called when plugin is unloaded or system shuts down:

```python
def cleanup(self) -> None:
    """Clean up plugin resources."""
    super().cleanup()  # Call parent cleanup
    if hasattr(self, 'model'):
        self.model.unload()
    if hasattr(self, 'cache'):
        self.cache.clear()
    print(f"Cleaned up {self.metadata.name}")
```

### Step 3: Add Plugin-Specific Methods

Add methods that provide your plugin's functionality:

```python
def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process data using custom logic."""
    if not self.is_enabled:
        raise RuntimeError("Plugin not enabled")

    # Your custom logic here
    result = self.model.predict(data)

    return {
        "input": data,
        "output": result,
        "confidence": result.confidence,
    }
```

## Plugin Types

Devmatrix supports four plugin types:

### 1. AGENT Plugins

Custom agents that can participate in multi-agent workflows:

```python
class CustomAnalyzer(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom-analyzer",
            plugin_type=PluginType.AGENT,
            # ...
        )

    def analyze(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis on task."""
        pass
```

### 2. TOOL Plugins

Tools that agents can use during execution:

```python
class WebScraperTool(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web-scraper",
            plugin_type=PluginType.TOOL,
            # ...
        )

    def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape data from URL."""
        pass
```

### 3. WORKFLOW Plugins

Custom workflow definitions:

```python
class DataPipelineWorkflow(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="data-pipeline",
            plugin_type=PluginType.WORKFLOW,
            # ...
        )

    def create_workflow(self) -> StateGraph:
        """Create custom LangGraph workflow."""
        pass
```

### 4. MIDDLEWARE Plugins

Middleware for request/response processing:

```python
class AuthMiddleware(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="auth-middleware",
            plugin_type=PluginType.MIDDLEWARE,
            # ...
        )

    async def process(self, request: Request, call_next):
        """Process request and response."""
        pass
```

## Plugin Lifecycle

### Lifecycle States

1. **Registered**: Plugin class registered, not yet instantiated
2. **Instantiated**: Plugin object created
3. **Initialized**: Plugin's `initialize()` called successfully
4. **Enabled**: Plugin ready for use
5. **Disabled**: Plugin temporarily deactivated
6. **Cleaned Up**: Plugin resources released

### State Transitions

```
Registered → Instantiated → Initialized → Enabled
                                 ↑            ↓
                                 └── Disabled ←┘
                                       ↓
                                  Cleaned Up
```

### Lifecycle Methods

```python
# Registration (lazy loading)
registry.register_class(MyPlugin)

# First access triggers instantiation + initialization
plugin = registry.get("my-plugin")  # Auto-enabled

# Disable temporarily
plugin.disable()

# Re-enable
plugin.enable()

# Cleanup and unregister
registry.unregister("my-plugin")  # Calls cleanup()
```

## Loading Plugins

### Method 1: Direct Registration

```python
from src.plugins.registry import PluginRegistry

registry = PluginRegistry()

# Register plugin class (lazy loading)
registry.register_class(MyCustomAgent)

# Register plugin instance
plugin = MyCustomAgent(config={"key": "value"})
plugin.enable()
registry.register(plugin)
```

### Method 2: Directory Scanning

```python
from pathlib import Path

# Load all plugins from directory
count = registry.load_from_directory(Path("/path/to/plugins"))
print(f"Loaded {count} plugins")

# Load only specific plugin type
count = registry.load_from_directory(
    Path("/path/to/plugins"),
    plugin_type=PluginType.AGENT
)
```

### Method 3: Discovery with PluginLoader

```python
from src.plugins.loader import PluginLoader

loader = PluginLoader([Path("/plugins/dir1"), Path("/plugins/dir2")])

# Discover all plugins
plugin_classes = loader.discover_plugins()

# Discover specific type
agent_classes = loader.discover_plugins(PluginType.AGENT)

# Load plugin instance
plugin = loader.load_plugin(plugin_classes[0], config={})
```

## Configuration

### Providing Configuration

Pass configuration when instantiating or loading:

```python
config = {
    "api_key": "secret-key",
    "endpoint": "https://api.example.com",
    "timeout": 30,
    "retry_attempts": 3,
}

# Method 1: Direct instantiation
plugin = MyPlugin(config)

# Method 2: Via loader
plugin = loader.load_plugin(MyPluginClass, config)

# Method 3: Via registry (set before first access)
registry.register_class(MyPluginClass)
# Configuration must be provided before first get()
```

### Accessing Configuration

Inside your plugin, use `get_config()`:

```python
class MyPlugin(BasePlugin):
    def initialize(self) -> None:
        # Get required config
        self.api_key = self.get_config("api_key")

        # Get optional config with default
        self.timeout = self.get_config("timeout", default=30)

        # Get all config
        all_config = self.config
```

### Configuration Schema

Define expected configuration in metadata:

```python
@property
def metadata(self) -> PluginMetadata:
    return PluginMetadata(
        name="my-plugin",
        # ...
        config_schema={
            "required": ["api_key", "endpoint"],
            "optional": ["timeout", "retry_attempts"],
            "defaults": {
                "timeout": 30,
                "retry_attempts": 3,
            },
        },
    )
```

## Best Practices

### 1. Plugin Naming

- Use lowercase with hyphens: `my-custom-agent`
- Be descriptive: `sentiment-analysis-agent` not `sa-agent`
- Include type suffix for clarity: `-agent`, `-tool`, `-workflow`

### 2. Version Management

- Follow semantic versioning: `MAJOR.MINOR.PATCH`
- Update version on breaking changes
- Document version compatibility in README

### 3. Dependencies

- List all external dependencies in metadata
- Use specific versions: `requests>=2.28.0,<3.0.0`
- Validate dependencies in `validate()` method
- Provide clear error messages if dependencies missing

### 4. Error Handling

```python
def process(self, data: Dict) -> Dict:
    """Process data with proper error handling."""
    if not self.is_enabled:
        raise RuntimeError(f"Plugin {self.metadata.name} not enabled")

    try:
        result = self._do_processing(data)
        return {"status": "success", "result": result}
    except ValueError as e:
        return {"status": "error", "error": f"Invalid data: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### 5. Resource Management

```python
def initialize(self) -> None:
    """Initialize with proper resource management."""
    self.connection = create_connection(self.config)
    self.file_handle = open(self.config["file"], "r")

def cleanup(self) -> None:
    """Always clean up resources."""
    super().cleanup()
    if hasattr(self, 'connection'):
        self.connection.close()
    if hasattr(self, 'file_handle'):
        self.file_handle.close()
```

### 6. Testing

Always provide comprehensive tests for your plugins:

```python
def test_plugin_initialization():
    """Test plugin initializes correctly."""
    config = {"api_key": "test-key"}
    plugin = MyPlugin(config)
    plugin.enable()

    assert plugin.is_enabled
    assert plugin.is_initialized

def test_plugin_validation():
    """Test plugin validation."""
    # Valid config
    plugin = MyPlugin({"api_key": "key"})
    assert plugin.validate()

    # Invalid config
    plugin = MyPlugin({})
    assert not plugin.validate()
```

## Examples

### Complete Agent Plugin Example

See `examples/plugins/custom_agent_plugin.py`:

```python
class SentimentAnalysisAgent(BasePlugin):
    """Agent that analyzes text sentiment."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="sentiment-analysis-agent",
            version="1.0.0",
            author="Devmatrix Team",
            description="Analyzes text sentiment using NLP",
            plugin_type=PluginType.AGENT,
            dependencies=["transformers", "torch"],
            tags=["nlp", "sentiment"],
        )

    def initialize(self) -> None:
        from transformers import pipeline
        self.pipeline = pipeline(
            "sentiment-analysis",
            model=self.get_config("model_name", "default-model")
        )

    def validate(self) -> bool:
        required = ["model_name", "threshold"]
        return all(self.get_config(k) for k in required)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        result = self.pipeline(text)[0]
        return {
            "text": text,
            "sentiment": result["label"],
            "confidence": result["score"],
        }
```

### Complete Tool Plugin Example

See `examples/plugins/custom_tool_plugin.py`:

```python
class WebScraperTool(BasePlugin):
    """Tool for web scraping."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web-scraper-tool",
            version="1.0.0",
            author="Devmatrix Team",
            description="Scrapes data from web pages",
            plugin_type=PluginType.TOOL,
            dependencies=["requests", "beautifulsoup4"],
            tags=["web", "scraping"],
        )

    def initialize(self) -> None:
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.get_config("user_agent", "Bot/1.0")
        })

    def validate(self) -> bool:
        return self.get_config("timeout", 30) > 0

    def scrape_url(self, url: str) -> Dict[str, Any]:
        from bs4 import BeautifulSoup

        if not self.is_enabled:
            raise RuntimeError("Plugin not enabled")

        response = self.session.get(
            url,
            timeout=self.get_config("timeout", 30)
        )
        soup = BeautifulSoup(response.content, "html.parser")

        return {
            "url": url,
            "title": soup.title.string if soup.title else None,
            "text": soup.get_text()[:1000],  # First 1000 chars
        }

    def cleanup(self) -> None:
        super().cleanup()
        if hasattr(self, 'session'):
            self.session.close()
```

## Testing Your Plugins

### Unit Tests

```python
import pytest
from your_plugin import YourPlugin

def test_plugin_lifecycle():
    """Test complete plugin lifecycle."""
    plugin = YourPlugin({"key": "value"})

    # Test validation
    assert plugin.validate()

    # Test enable
    plugin.enable()
    assert plugin.is_enabled
    assert plugin.is_initialized

    # Test disable
    plugin.disable()
    assert not plugin.is_enabled

    # Test cleanup
    plugin.cleanup()
    assert not plugin.is_initialized

def test_plugin_functionality():
    """Test plugin's main functionality."""
    plugin = YourPlugin({"key": "value"})
    plugin.enable()

    result = plugin.your_method("input")
    assert result["status"] == "success"
```

### Integration Tests

```python
def test_plugin_loading():
    """Test loading plugin via registry."""
    registry = PluginRegistry()

    # Load from directory
    count = registry.load_from_directory(Path("./plugins"))
    assert count > 0

    # Get plugin
    plugin = registry.get("your-plugin-name")
    assert plugin is not None
    assert plugin.is_enabled
```

## Troubleshooting

### Plugin Not Found

```python
# Check plugin directory exists
assert plugin_dir.exists()

# Check file naming (no leading underscore)
assert not filename.startswith("_")

# Verify plugin class inherits from BasePlugin
assert issubclass(YourPlugin, BasePlugin)
```

### Validation Fails

```python
# Check required configuration
config = {
    "api_key": "...",  # All required fields
}

# Enable debug logging
plugin = YourPlugin(config)
if not plugin.validate():
    print("Validation failed - check config and dependencies")
```

### Import Errors

```python
# Install plugin dependencies
pip install -r plugin_requirements.txt

# Verify in validate() method
def validate(self) -> bool:
    try:
        import required_package
        return True
    except ImportError:
        print("Missing required_package")
        return False
```

## Further Reading

- [Plugin Base Classes API](./base.py)
- [Plugin Loader API](./loader.py)
- [Plugin Registry API](./registry.py)
- [Example Plugins](../../examples/plugins/)
- [Plugin Tests](../../tests/unit/test_plugin_*.py)

## Contributing

To contribute a plugin:

1. Create your plugin following this guide
2. Add comprehensive tests
3. Document configuration requirements
4. Submit PR with example usage
5. Update this README if needed

For questions or issues, please open a GitHub issue.

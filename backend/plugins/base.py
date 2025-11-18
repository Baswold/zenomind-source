"""
Base plugin interface and metadata
Defines the contract for all plugins
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger


class PluginCapability(Enum):
    """Plugin capability types"""
    TOOL = "tool"  # Provides a tool/function
    DATA_SOURCE = "data_source"  # Provides data access
    INTEGRATION = "integration"  # Third-party integration
    PROCESSOR = "processor"  # Data processor
    ANALYZER = "analyzer"  # Analysis capability
    GENERATOR = "generator"  # Content generator
    CUSTOM = "custom"  # Custom capability


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str = "Unknown"
    capabilities: List[PluginCapability] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    enabled_by_default: bool = True
    min_agent_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "capabilities": [cap.value for cap in self.capabilities],
            "dependencies": self.dependencies,
            "config_schema": self.config_schema,
            "enabled_by_default": self.enabled_by_default,
            "min_agent_version": self.min_agent_version
        }


class Plugin(ABC):
    """
    Base plugin class

    All plugins must inherit from this class and implement the required methods
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config or {}
        self.enabled = False
        self.initialized = False
        self.metadata: Optional[PluginMetadata] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the plugin

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the plugin and cleanup resources"""
        pass

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata

        Returns:
            PluginMetadata instance
        """
        pass

    async def validate_config(self) -> bool:
        """
        Validate plugin configuration

        Returns:
            True if config is valid, False otherwise
        """
        # Default implementation - override for custom validation
        return True

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check

        Returns:
            Dictionary with health status
        """
        return {
            "healthy": self.enabled and self.initialized,
            "enabled": self.enabled,
            "initialized": self.initialized,
            "timestamp": datetime.now().isoformat()
        }

    def get_capabilities(self) -> List[PluginCapability]:
        """Get plugin capabilities"""
        if self.metadata:
            return self.metadata.capabilities
        return []

    async def on_enable(self):
        """Called when plugin is enabled"""
        logger.info(f"🔌 Plugin enabled: {self.metadata.name if self.metadata else 'Unknown'}")

    async def on_disable(self):
        """Called when plugin is disabled"""
        logger.info(f"🔌 Plugin disabled: {self.metadata.name if self.metadata else 'Unknown'}")


class ToolPlugin(Plugin):
    """
    Base class for tool plugins

    Tool plugins provide executable functions/tools for the agent
    """

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the tool

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    def get_tool_schema(self) -> Dict[str, Any]:
        """
        Get tool schema for the agent

        Returns:
            Dictionary describing tool parameters and usage
        """
        pass


class DataSourcePlugin(Plugin):
    """
    Base class for data source plugins

    Data source plugins provide access to external data
    """

    @abstractmethod
    async def fetch(self, query: str, **kwargs) -> Any:
        """
        Fetch data from the source

        Args:
            query: Data query
            **kwargs: Additional parameters

        Returns:
            Fetched data
        """
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the data source

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results
        """
        pass


class IntegrationPlugin(Plugin):
    """
    Base class for integration plugins

    Integration plugins connect to third-party services
    """

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the external service

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from the external service"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to external service"""
        pass


# Example plugin implementation
class CalculatorPlugin(ToolPlugin):
    """Example calculator plugin"""

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="calculator",
            name="Calculator",
            version="1.0.0",
            description="Basic arithmetic calculator",
            author="ZenoMind Team",
            capabilities=[PluginCapability.TOOL],
            enabled_by_default=True
        )

    async def initialize(self) -> bool:
        """Initialize calculator"""
        self.metadata = self.get_metadata()
        self.initialized = True
        logger.info("🧮 Calculator plugin initialized")
        return True

    async def shutdown(self):
        """Shutdown calculator"""
        self.initialized = False
        logger.info("🧮 Calculator plugin shutdown")

    async def execute(self, operation: str, a: float, b: float) -> float:
        """
        Execute calculation

        Args:
            operation: Operation (+, -, *, /)
            a: First operand
            b: Second operand

        Returns:
            Calculation result
        """
        operations = {
            "+": lambda x, y: x + y,
            "-": lambda x, y: x - y,
            "*": lambda x, y: x * y,
            "/": lambda x, y: x / y if y != 0 else float('inf')
        }

        if operation not in operations:
            raise ValueError(f"Unsupported operation: {operation}")

        result = operations[operation](a, b)
        logger.info(f"🧮 Calculation: {a} {operation} {b} = {result}")

        return result

    def get_tool_schema(self) -> Dict[str, Any]:
        """Get calculator tool schema"""
        return {
            "name": "calculator",
            "description": "Perform basic arithmetic calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["+", "-", "*", "/"],
                        "description": "Arithmetic operation"
                    },
                    "a": {
                        "type": "number",
                        "description": "First operand"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second operand"
                    }
                },
                "required": ["operation", "a", "b"]
            }
        }

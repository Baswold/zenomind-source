"""
Plugin registry - Global plugin discovery and registration
"""

from typing import Dict, List, Optional, Type
from .base import Plugin, PluginCapability
from loguru import logger


class PluginRegistry:
    """
    Global plugin registry

    Maintains a catalog of all available plugins for discovery
    """

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_classes: Dict[str, Type[Plugin]] = {}

    def register(self, plugin: Plugin):
        """
        Register a plugin instance

        Args:
            plugin: Plugin instance to register
        """
        if not plugin.metadata:
            logger.warning("Cannot register plugin without metadata")
            return

        plugin_id = plugin.metadata.plugin_id

        self.plugins[plugin_id] = plugin
        self.plugin_classes[plugin_id] = type(plugin)

        logger.debug(f"📝 Registered plugin: {plugin_id}")

    def register_class(self, plugin_id: str, plugin_class: Type[Plugin]):
        """
        Register a plugin class for later instantiation

        Args:
            plugin_id: Unique plugin identifier
            plugin_class: Plugin class
        """
        self.plugin_classes[plugin_id] = plugin_class
        logger.debug(f"📝 Registered plugin class: {plugin_id}")

    def unregister(self, plugin_id: str):
        """
        Unregister a plugin

        Args:
            plugin_id: Plugin ID to unregister
        """
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]

        if plugin_id in self.plugin_classes:
            del self.plugin_classes[plugin_id]

        logger.debug(f"📝 Unregistered plugin: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin instance by ID"""
        return self.plugins.get(plugin_id)

    def get_plugin_class(self, plugin_id: str) -> Optional[Type[Plugin]]:
        """Get plugin class by ID"""
        return self.plugin_classes.get(plugin_id)

    def list_plugins(self) -> List[str]:
        """List all registered plugin IDs"""
        return list(self.plugins.keys())

    def list_plugin_classes(self) -> List[str]:
        """List all registered plugin class IDs"""
        return list(self.plugin_classes.keys())

    def find_by_capability(self, capability: PluginCapability) -> List[Plugin]:
        """
        Find plugins by capability

        Args:
            capability: Capability to search for

        Returns:
            List of matching plugins
        """
        return [
            plugin for plugin in self.plugins.values()
            if capability in plugin.get_capabilities()
        ]

    def get_registry_info(self) -> Dict:
        """Get registry information"""
        return {
            "total_plugins": len(self.plugins),
            "total_classes": len(self.plugin_classes),
            "plugins": [
                {
                    "plugin_id": p.metadata.plugin_id,
                    "name": p.metadata.name,
                    "version": p.metadata.version,
                    "enabled": p.enabled
                }
                for p in self.plugins.values()
                if p.metadata
            ]
        }


# Global registry instance
plugin_registry = PluginRegistry()

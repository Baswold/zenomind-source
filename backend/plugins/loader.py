"""
Plugin loader - Dynamic plugin discovery and loading
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import List, Type, Dict, Any
from loguru import logger

from .base import Plugin
from .registry import plugin_registry


class PluginLoader:
    """
    Plugin loader - Discovers and loads plugins from filesystem

    Features:
    - Auto-discovery of plugins from directories
    - Dynamic import and class loading
    - Validation of plugin interfaces
    - Dependency checking
    """

    def __init__(self, plugin_dirs: List[str] = None):
        """
        Initialize plugin loader

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or ["./plugins/builtins", "./plugins/custom"]
        self.discovered_plugins: Dict[str, Type[Plugin]] = {}

    def discover_plugins(self) -> List[Type[Plugin]]:
        """
        Discover all plugins in configured directories

        Returns:
            List of discovered plugin classes
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)

            if not plugin_path.exists():
                logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue

            logger.info(f"🔍 Discovering plugins in: {plugin_dir}")

            # Find all Python files in directory
            for py_file in plugin_path.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                try:
                    plugins = self._load_plugins_from_file(py_file)
                    discovered.extend(plugins)

                except Exception as e:
                    logger.error(f"Failed to load plugins from {py_file}: {e}")

        logger.info(f"✅ Discovered {len(discovered)} plugins")
        return discovered

    def _load_plugins_from_file(self, file_path: Path) -> List[Type[Plugin]]:
        """
        Load plugin classes from a Python file

        Args:
            file_path: Path to Python file

        Returns:
            List of plugin classes found in file
        """
        plugins = []

        # Import the module
        module_name = file_path.stem
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        if not spec or not spec.loader:
            return plugins

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find all Plugin subclasses
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip the Plugin base class itself
            if obj is Plugin:
                continue

            # Check if it's a Plugin subclass
            if issubclass(obj, Plugin):
                plugins.append(obj)
                self.discovered_plugins[name] = obj

                logger.debug(f"  📦 Found plugin class: {name}")

        return plugins

    def load_plugin_class(self, class_name: str) -> Type[Plugin]:
        """
        Load a specific plugin class by name

        Args:
            class_name: Name of the plugin class

        Returns:
            Plugin class

        Raises:
            ValueError: If plugin class not found
        """
        if class_name not in self.discovered_plugins:
            raise ValueError(f"Plugin class not found: {class_name}")

        return self.discovered_plugins[class_name]

    def register_discovered_plugins(self):
        """Register all discovered plugins in the global registry"""
        for class_name, plugin_class in self.discovered_plugins.items():
            try:
                # Create temporary instance to get metadata
                temp_instance = plugin_class()
                metadata = temp_instance.get_metadata()

                # Register class in registry
                plugin_registry.register_class(metadata.plugin_id, plugin_class)

                logger.info(f"📝 Registered: {metadata.name} ({metadata.plugin_id})")

            except Exception as e:
                logger.error(f"Failed to register plugin {class_name}: {e}")

    def get_discovered_info(self) -> List[Dict[str, Any]]:
        """Get information about discovered plugins"""
        info = []

        for class_name, plugin_class in self.discovered_plugins.items():
            try:
                temp_instance = plugin_class()
                metadata = temp_instance.get_metadata()

                info.append({
                    "class_name": class_name,
                    "plugin_id": metadata.plugin_id,
                    "name": metadata.name,
                    "version": metadata.version,
                    "description": metadata.description,
                    "capabilities": [cap.value for cap in metadata.capabilities]
                })

            except Exception as e:
                info.append({
                    "class_name": class_name,
                    "error": str(e)
                })

        return info


# Global plugin loader instance
plugin_loader = PluginLoader()

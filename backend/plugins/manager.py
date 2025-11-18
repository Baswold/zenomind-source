"""
Plugin manager - Manages plugin lifecycle and orchestration
"""

from typing import Dict, List, Optional, Type
import asyncio
from loguru import logger

from .base import Plugin, PluginMetadata, PluginCapability
from .registry import plugin_registry


class PluginManager:
    """
    Plugin manager - Central system for plugin management

    Features:
    - Plugin loading and unloading
    - Lifecycle management (initialize, enable, disable, shutdown)
    - Dependency resolution
    - Health monitoring
    - Configuration management
    """

    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.enabled_plugins: Dict[str, Plugin] = {}
        self._lock = asyncio.Lock()

    async def load_plugin(
        self,
        plugin_class: Type[Plugin],
        config: Optional[Dict] = None
    ) -> bool:
        """
        Load a plugin

        Args:
            plugin_class: Plugin class to instantiate
            config: Plugin configuration

        Returns:
            True if loaded successfully
        """
        async with self._lock:
            try:
                # Create plugin instance
                plugin = plugin_class(config=config)

                # Get metadata
                metadata = plugin.get_metadata()
                plugin_id = metadata.plugin_id

                # Check if already loaded
                if plugin_id in self.plugins:
                    logger.warning(f"Plugin {plugin_id} already loaded")
                    return False

                # Validate config
                if not await plugin.validate_config():
                    logger.error(f"Invalid configuration for plugin {plugin_id}")
                    return False

                # Initialize plugin
                if not await plugin.initialize():
                    logger.error(f"Failed to initialize plugin {plugin_id}")
                    return False

                plugin.initialized = True
                plugin.metadata = metadata

                # Store plugin
                self.plugins[plugin_id] = plugin

                # Auto-enable if configured
                if metadata.enabled_by_default:
                    await self.enable_plugin(plugin_id)

                # Register in global registry
                plugin_registry.register(plugin)

                logger.info(f"✅ Loaded plugin: {metadata.name} v{metadata.version}")
                return True

            except Exception as e:
                logger.error(f"Failed to load plugin: {e}")
                return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin

        Args:
            plugin_id: Plugin ID to unload

        Returns:
            True if unloaded successfully
        """
        async with self._lock:
            try:
                if plugin_id not in self.plugins:
                    logger.warning(f"Plugin {plugin_id} not found")
                    return False

                plugin = self.plugins[plugin_id]

                # Disable if enabled
                if plugin_id in self.enabled_plugins:
                    await self.disable_plugin(plugin_id)

                # Shutdown plugin
                await plugin.shutdown()

                # Remove from registry
                plugin_registry.unregister(plugin_id)

                # Remove from manager
                del self.plugins[plugin_id]

                logger.info(f"✅ Unloaded plugin: {plugin_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to unload plugin {plugin_id}: {e}")
                return False

    async def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a plugin

        Args:
            plugin_id: Plugin ID to enable

        Returns:
            True if enabled successfully
        """
        async with self._lock:
            try:
                if plugin_id not in self.plugins:
                    logger.warning(f"Plugin {plugin_id} not found")
                    return False

                if plugin_id in self.enabled_plugins:
                    logger.info(f"Plugin {plugin_id} already enabled")
                    return True

                plugin = self.plugins[plugin_id]

                # Call on_enable hook
                await plugin.on_enable()

                plugin.enabled = True
                self.enabled_plugins[plugin_id] = plugin

                logger.info(f"✅ Enabled plugin: {plugin_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to enable plugin {plugin_id}: {e}")
                return False

    async def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin

        Args:
            plugin_id: Plugin ID to disable

        Returns:
            True if disabled successfully
        """
        async with self._lock:
            try:
                if plugin_id not in self.enabled_plugins:
                    logger.info(f"Plugin {plugin_id} not enabled")
                    return True

                plugin = self.enabled_plugins[plugin_id]

                # Call on_disable hook
                await plugin.on_disable()

                plugin.enabled = False
                del self.enabled_plugins[plugin_id]

                logger.info(f"✅ Disabled plugin: {plugin_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to disable plugin {plugin_id}: {e}")
                return False

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)

    def get_enabled_plugins(self) -> List[Plugin]:
        """Get all enabled plugins"""
        return list(self.enabled_plugins.values())

    def get_plugins_by_capability(
        self,
        capability: PluginCapability
    ) -> List[Plugin]:
        """
        Get plugins that provide a specific capability

        Args:
            capability: Capability to search for

        Returns:
            List of matching plugins
        """
        return [
            plugin for plugin in self.enabled_plugins.values()
            if capability in plugin.get_capabilities()
        ]

    async def health_check_all(self) -> Dict[str, Dict]:
        """
        Perform health check on all plugins

        Returns:
            Dictionary mapping plugin_id to health status
        """
        health_status = {}

        for plugin_id, plugin in self.plugins.items():
            try:
                health_status[plugin_id] = await plugin.health_check()
            except Exception as e:
                health_status[plugin_id] = {
                    "healthy": False,
                    "error": str(e)
                }

        return health_status

    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin

        Args:
            plugin_id: Plugin ID to reload

        Returns:
            True if reloaded successfully
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return False

        # Get plugin class and config
        plugin_class = type(plugin)
        config = plugin.config

        # Unload and reload
        if await self.unload_plugin(plugin_id):
            return await self.load_plugin(plugin_class, config)

        return False

    def get_plugin_info(self) -> List[Dict]:
        """Get information about all loaded plugins"""
        info = []

        for plugin_id, plugin in self.plugins.items():
            if plugin.metadata:
                plugin_info = plugin.metadata.to_dict()
                plugin_info["enabled"] = plugin.enabled
                plugin_info["initialized"] = plugin.initialized
                info.append(plugin_info)

        return info

    async def shutdown_all(self):
        """Shutdown all plugins"""
        logger.info("🔌 Shutting down all plugins...")

        # Disable all
        for plugin_id in list(self.enabled_plugins.keys()):
            await self.disable_plugin(plugin_id)

        # Shutdown all
        for plugin_id in list(self.plugins.keys()):
            await self.unload_plugin(plugin_id)

        logger.info("✅ All plugins shutdown")


# Global plugin manager instance
plugin_manager = PluginManager()

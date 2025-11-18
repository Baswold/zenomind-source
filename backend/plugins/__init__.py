"""
Plugin system for ZenoMind
Enables dynamic extension of agent capabilities through custom tools
"""

from .base import Plugin, PluginMetadata, PluginCapability
from .manager import PluginManager
from .loader import PluginLoader
from .registry import plugin_registry

__all__ = [
    'Plugin',
    'PluginMetadata',
    'PluginCapability',
    'PluginManager',
    'PluginLoader',
    'plugin_registry'
]

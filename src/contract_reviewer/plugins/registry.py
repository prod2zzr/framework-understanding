"""Plugin discovery and registration."""

import importlib
import logging
from importlib.metadata import entry_points

from contract_reviewer.plugins.base import ReviewPlugin

logger = logging.getLogger(__name__)

_registry: dict[str, ReviewPlugin] = {}


def register_plugin(plugin: ReviewPlugin) -> None:
    """Register a plugin by name."""
    _registry[plugin.name] = plugin
    logger.info("Registered plugin: %s v%s", plugin.name, plugin.version)


def get_plugin(name: str) -> ReviewPlugin | None:
    return _registry.get(name)


def get_all_plugins() -> dict[str, ReviewPlugin]:
    return dict(_registry)


def discover_plugins() -> None:
    """Discover and register plugins from entry_points and built-in modules."""
    # Built-in plugins
    try:
        from contract_reviewer.plugins.builtin import risk_clauses, compliance_civil_code, term_fairness
        for module in [risk_clauses, compliance_civil_code, term_fairness]:
            if hasattr(module, "plugin"):
                register_plugin(module.plugin)
    except ImportError:
        logger.debug("Some built-in plugins not available")

    # External plugins via entry_points
    try:
        eps = entry_points(group="contract_reviewer.plugins")
        for ep in eps:
            try:
                plugin_cls = ep.load()
                if isinstance(plugin_cls, type) and issubclass(plugin_cls, ReviewPlugin):
                    register_plugin(plugin_cls())
                elif isinstance(plugin_cls, ReviewPlugin):
                    register_plugin(plugin_cls)
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", ep.name, e)
    except Exception:
        pass

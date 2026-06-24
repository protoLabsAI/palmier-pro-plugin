"""Test bootstrap — load the single-file plugin with NO protoAgent host present.

``__init__.py`` has no host imports, so executing it standalone is safe. A
``FakeRegistry`` stands in for the host registry so ``register()`` can be smoke-tested
and the contributed MCP factory exercised directly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_plugin():
    spec = importlib.util.spec_from_file_location("palmier_pro_under_test", ROOT / "__init__.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def plugin():
    return _load_plugin()


class FakeRegistry:
    """Mirrors the host registry surface the plugin touches (graph/plugins/testkit.py)."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.tools: list = []
        self.routers: list = []
        self.surfaces: list = []
        self.mcp_servers: list = []
        self.skill_dirs: list = []
        self.subagents: list = []

    def register_tool(self, t):
        self.tools.append(t)

    def register_tools(self, ts):
        self.tools.extend(ts)

    def register_router(self, router, prefix=None):
        self.routers.append((prefix, router))

    def register_surface(self, start, stop=None, name=None, reload=None):
        self.surfaces.append(name)

    def register_mcp_server(self, factory):
        self.mcp_servers.append(factory)

    def register_skill_dir(self, path):
        self.skill_dirs.append(str(path))

    def register_subagent(self, config):
        self.subagents.append(config)


@pytest.fixture
def make_registry():
    def _make(config: dict | None = None) -> FakeRegistry:
        return FakeRegistry(config)

    return _make

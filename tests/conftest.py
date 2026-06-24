"""Test bootstrap — load the plugin as a synthetic package with NO protoAgent host.

The plugin is multi-module (`from .bridge import ...`), so we register a synthetic
package whose __path__ is the repo root, letting relative imports resolve standalone.
__init__.py keeps host/heavy imports inside register(), so executing it here is safe.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PKG = "palmier_pro"

if PKG not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        PKG, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    assert _spec and _spec.loader
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[PKG] = _mod
    _spec.loader.exec_module(_mod)


@pytest.fixture
def plugin():
    return sys.modules[PKG]


class FakeRegistry:
    """Mirrors the host registry surface the plugin touches (graph/plugins/testkit.py)."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.tools: list = []
        self.routers: list = []
        self.surfaces: list = []
        self.skill_dirs: list = []
        self.subagents: list = []
        self.mcp_servers: list = []

    def register_tool(self, t):
        self.tools.append(t)

    def register_tools(self, ts):
        self.tools.extend(ts)

    def register_router(self, router, prefix=None):
        self.routers.append((prefix, router))

    def register_surface(self, start, stop=None, name=None, reload=None):
        self.surfaces.append({"start": start, "stop": stop, "name": name})

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

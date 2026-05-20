"""Auto-discovery of TTS engine specs.

Scans this package for any `*_spec.py` module exporting `ENGINE_NAME` and
`ENGINE_PARAMS`. Adding a new engine is just: drop `<name>_spec.py` next to
this file. No central list to update.

The specs are pure data (no engine-package imports), so this discovery works
in every `.venv-<engine>/` regardless of which engine's deps are installed.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from types import ModuleType

logger = logging.getLogger(__name__)

_specs: dict[str, ModuleType] = {}
_discovered = False


def _discover() -> None:
    global _discovered
    if _discovered:
        return
    pkg_dir = Path(__file__).parent
    for info in pkgutil.iter_modules([str(pkg_dir)]):
        if not info.name.endswith("_spec"):
            continue
        full = f"tts.tts.{info.name}"
        try:
            module = importlib.import_module(full)
        except Exception:
            logger.exception("Failed to import engine spec %s", full)
            continue
        name = getattr(module, "ENGINE_NAME", None)
        params = getattr(module, "ENGINE_PARAMS", None)
        if not name or params is None:
            logger.warning("Spec module %s missing ENGINE_NAME or ENGINE_PARAMS", full)
            continue
        _specs[name] = module
    _discovered = True


def supported_engines() -> list[str]:
    _discover()
    return list(_specs.keys())


def engine_params(name: str) -> list[dict] | None:
    _discover()
    mod = _specs.get(name)
    return getattr(mod, "ENGINE_PARAMS", None) if mod else None

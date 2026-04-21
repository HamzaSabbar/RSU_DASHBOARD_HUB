from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    from boards.macro_national.schemas import ExpectedFile


@dataclass
class BoardSpec:
    slug: str
    title: str
    description: str
    expected_files: list[ExpectedFile]
    router: APIRouter


_REGISTRY: dict[str, BoardSpec] | None = None


def discover_boards() -> dict[str, BoardSpec]:
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    registry: dict[str, BoardSpec] = {}
    import boards as boards_pkg

    for module_info in pkgutil.iter_modules(boards_pkg.__path__):
        if not module_info.ispkg:
            continue
        module = importlib.import_module(f"boards.{module_info.name}")
        spec = getattr(module, "BOARD_SPEC", None)
        if isinstance(spec, BoardSpec):
            registry[spec.slug] = spec

    _REGISTRY = registry
    return registry

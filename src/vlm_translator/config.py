from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from .models import AppConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        raw: dict[str, Any] = tomllib.load(handle)
    config = AppConfig.model_validate(raw)
    return _resolve_paths(config, config_path.parent)


def _resolve_paths(config: AppConfig, base_dir: Path) -> AppConfig:
    data = config.model_dump()
    for key in ("parsed_laws_path", "prompt_path", "results_path", "output_schema_path"):
        value = getattr(config, key)
        if value is not None and not value.is_absolute():
            data[key] = base_dir / value
    return AppConfig.model_validate(data)


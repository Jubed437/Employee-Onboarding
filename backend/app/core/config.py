from pathlib import Path

import yaml
from pydantic import BaseModel

from app.domain.schemas import (
    PlaybooksConfig,
    PoliciesConfig,
    ProfileConfig,
    ScoringConfig,
)


class ConfigLoadError(ValueError):
    """Raised when a YAML configuration cannot be loaded or validated."""


def load_yaml_config[ConfigModel: BaseModel](
    path: Path, model: type[ConfigModel]
) -> ConfigModel:
    try:
        with path.open(encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file)
        return model.model_validate(raw_config)
    except (OSError, yaml.YAMLError, ValueError) as error:
        raise ConfigLoadError(f"Invalid configuration in {path}: {error}") from error


def load_profile(path: Path) -> ProfileConfig:
    return load_yaml_config(path, ProfileConfig)


def load_playbooks(path: Path) -> PlaybooksConfig:
    return load_yaml_config(path, PlaybooksConfig)


def load_scoring(path: Path) -> ScoringConfig:
    return load_yaml_config(path, ScoringConfig)


def load_policies(path: Path) -> PoliciesConfig:
    return load_yaml_config(path, PoliciesConfig)

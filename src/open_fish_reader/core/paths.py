from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_cache_path, user_data_path, user_log_path

from ..version import APP_NAME


@dataclass(frozen=True, slots=True)
class AppPaths:
    data: Path
    databases: Path
    backups: Path
    config: Path
    logs: Path
    cache: Path


def get_app_paths() -> AppPaths:
    data = Path(user_data_path(APP_NAME, appauthor=False, roaming=False))
    return AppPaths(
        data,
        data / "databases",
        data / "backups",
        data / "config",
        Path(user_log_path(APP_NAME, appauthor=False)),
        Path(user_cache_path(APP_NAME, appauthor=False)),
    )


def ensure_app_directories() -> AppPaths:
    paths = get_app_paths()
    for p in (paths.data, paths.databases, paths.backups, paths.config, paths.logs, paths.cache):
        p.mkdir(parents=True, exist_ok=True)
    return paths

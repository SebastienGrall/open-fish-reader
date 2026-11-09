import json
from dataclasses import asdict, dataclass
from pathlib import Path
from .paths import get_app_paths
@dataclass(slots=True)
class AppSettings:
    last_station_folder: str | None = None
    playback_speed: float = 1.0
    auto_resume_after_observation: bool = True
    quick_validation_enabled: bool = True
class SettingsManager:
    def __init__(self, path: Path | None = None): self.path = path or get_app_paths().config/'settings.json'
    def load(self) -> AppSettings:
        if not self.path.exists(): return AppSettings()
        try:
            data=json.loads(self.path.read_text(encoding='utf-8')); allowed=AppSettings.__dataclass_fields__.keys()
            return AppSettings(**{k:v for k,v in data.items() if k in allowed})
        except (OSError, json.JSONDecodeError, TypeError): return AppSettings()
    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True); tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding='utf-8'); tmp.replace(self.path)

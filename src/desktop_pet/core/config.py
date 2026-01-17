from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Tuple


def appdata_dir() -> Path:
    # Windows: %APPDATA%
    base = Path.home() / "AppData" / "Roaming"
    return base / "WinterPTer"


@dataclass
class AppConfig:
    always_on_top: bool = True
    scale: float = 1.0
    pos: Tuple[int, int] | None = None  # (x, y)
    gif_path: str = "assets/pet.gif"    # 默认从项目根/assets 取

    #_path: Path | None = None
    _path: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def load(cls) -> "AppConfig":
        cfg_dir = appdata_dir()
        cfg_path = cfg_dir / "config.json"
        cfg_dir.mkdir(parents=True, exist_ok=True)

        cfg = cls()
        cfg._path = cfg_path

        if cfg_path.exists():
            try:
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                cfg._apply_dict(data)
            except Exception:
                # 配置坏了就用默认（也可以做备份/修复逻辑）
                pass
        else:
            cfg.save()
        return cfg

    def save(self) -> None:
        if self._path is None:
            self._path = appdata_dir() / "config.json"
            self._path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        data.pop("_path", None)   #

        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
    )


    def _apply_dict(self, data: Dict[str, Any]) -> None:
        if "always_on_top" in data:
            self.always_on_top = bool(data["always_on_top"])
        if "scale" in data:
            self.scale = float(data["scale"])
        if "pos" in data and data["pos"] is not None:
            self.pos = (int(data["pos"][0]), int(data["pos"][1]))
        if "gif_path" in data:
            self.gif_path = str(data["gif_path"])

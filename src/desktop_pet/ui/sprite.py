from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap


@dataclass
class SpriteSet:
    name: str
    folder: Path
    fps: int = 12
    loop: bool = True


class SpriteAnimator(QObject):
    frame_changed = Signal(QPixmap)

    def __init__(self, scale: float = 1.0, parent: QObject | None = None):
        super().__init__(parent)
        self.scale = max(0.05, float(scale))

        self._frames: List[QPixmap] = []
        self._index = 0
        self._loop = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next)

    def load(self, sprite: SpriteSet) -> None:
        files = sorted(sprite.folder.glob("*.png"))
        if not files:
            raise FileNotFoundError(f"No PNG frames found in: {sprite.folder}")

        self._loop = sprite.loop
        self._index = 0
        self._frames = [QPixmap(str(p)) for p in files]

        self.set_fps(sprite.fps)
        self._emit_current()

    def set_fps(self, fps: int) -> None:
        fps = max(1, int(fps))
        self._timer.setInterval(int(1000 / fps))

    def start(self) -> None:
        if self._frames:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_scale(self, scale: float) -> None:
        self.scale = max(0.05, float(scale))
        self._emit_current()

    def _emit_current(self) -> None:
        if not self._frames:
            return
        pm = self._frames[self._index]
        if self.scale != 1.0 and not pm.isNull():
            w = max(1, int(pm.width() * self.scale))
            h = max(1, int(pm.height() * self.scale))
            pm = pm.scaled(w, h)  # 默认平滑策略够用了
        self.frame_changed.emit(pm)

    def _next(self) -> None:
        if not self._frames:
            return
        self._index += 1
        if self._index >= len(self._frames):
            if self._loop:
                self._index = 0
            else:
                self._index = len(self._frames) - 1
                self.stop()
        self._emit_current()

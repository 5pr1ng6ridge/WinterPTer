from __future__ import annotations

import ctypes
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path


from PySide6.QtCore import Qt, QPoint, QTimer, Signal, QRect
from PySide6.QtGui import QPixmap, QMovie
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QMessageBox

from ..core.config import AppConfig
from .sprite import SpriteAnimator, SpriteSet

from random import randint

def project_root() -> Path:
    # Prefer the PyInstaller temp extraction dir when bundled, otherwise repo root.
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[3]
    #return Path.cwd()
    
WM_HOTKEY = 0x0312
    
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # 防止长按连发

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]
user32.UnregisterHotKey.restype = wintypes.BOOL
    

class PetWindow(QWidget):
    hotkeyPressed = Signal(int)
    def __init__(self, cfg: AppConfig, persist: bool = True):
        super().__init__()
        self.cfg = cfg
        self.persist = persist

        self._dragging = False
        self._drag_offset = QPoint()
        self._press_pos = QPoint()
        self._moved = False
        self._meow = False
        self._left_double_click = False
        self._right_double_click = False
        self._left_click_timer = QTimer(self)
        self._left_click_timer.setSingleShot(True)
        self._left_click_timer.timeout.connect(self._handle_left_click)
        self._right_click_timer = QTimer(self)
        self._right_click_timer.setSingleShot(True)
        self._right_click_timer.timeout.connect(self._handle_right_click)
        self._double_interval = self._calc_double_interval()
        if QApplication.instance() is not None:
            QApplication.instance().setDoubleClickInterval(self._double_interval)

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Tool, True)  # 不占任务栏
        self.set_always_on_top(cfg.always_on_top)
        
        self.child_window = None 

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        # ---- 皮肤列表：PNG 或 GIF ----
        self.skins = self._load_skins(project_root() / "assets" / "skins")
        if not self.skins:
            raise FileNotFoundError("No skins found in assets/skins (png/gif)")

        self.skin_index = 0
        self._movie: QMovie | None = None

        # 初始皮肤
        self.apply_skin(self.skin_index)

        # 初始位置
        if cfg.pos is not None:
            self.move(cfg.pos[0], cfg.pos[1])
        else:
            self.move(500, 500)

        # 鼠标穿透
        self._click_through_enabled = False
        QTimer.singleShot(0, lambda: self.set_click_through(self._click_through_enabled))

    
    
    def register_hotkey(self, hotkey_id: int, modifiers: int, vk: int) -> None:
        hwnd = wintypes.HWND(int(self.winId()))  # winId() 会确保窗口句柄存在
        ok = user32.RegisterHotKey(hwnd, int(hotkey_id), int(modifiers), int(vk))
        if not ok:
            raise OSError(f"RegisterHotKey failed id={hotkey_id}, err={ctypes.get_last_error()}")
    
    def unregister_hotkey(self, hotkey_id: int) -> None:
        hwnd = wintypes.HWND(int(self.winId()))
        user32.UnregisterHotKey(hwnd, int(hotkey_id))
        
    def nativeEvent(self, eventType, message):
    # 兼容 Qt6/PySide6：eventType 可能是 QByteArray/bytes/str
        try:
            et = bytes(eventType).decode(errors="ignore")
        except Exception:
            et = str(eventType)

        if "windows" in et:  # 避免不同版本名字不一样
            try:
                addr = int(message)
            except TypeError:
                addr = message.__int__()

            msg = ctypes.cast(addr, ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_HOTKEY:
                hotkey_id = int(msg.wParam)
                self.hotkeyPressed.emit(hotkey_id)
                return True, 0

        return super().nativeEvent(eventType, message)

    

    def _load_skins(self, folder: Path) -> list[Path]:
        if not folder.exists():
            return []
        files = []
        for ext in ("*.png", "*.gif"):
            files.extend(folder.glob(ext))
        return sorted(files)

    def next_skin(self) -> None:
        self.skin_index = (self.skin_index + 1) % len(self.skins)
        self.apply_skin(self.skin_index)
    
    def random_skin(self) -> None:
        self.skin_index = randint(0,len(self.skins)) % len(self.skins)
        self.apply_skin(self.skin_index)
        
    def apply_skin(self, index: int) -> None:
        path = self.skins[index]
        suffix = path.suffix.lower()

        # 清理旧 movie
        if self._movie is not None:
            self._movie.stop()
            self._movie.deleteLater()
            self._movie = None

        if suffix == ".gif":
            mv = QMovie(str(path))
            self._movie = mv
            self.label.setMovie(mv)
            mv.frameChanged.connect(lambda _: self._resize_to_label())
            mv.start()
            QTimer.singleShot(0, self._resize_to_label)
        else:
            pm = QPixmap(str(path))
            if pm.isNull():
                return
            self.label.setPixmap(pm)
            self._resize_to_pixmap(pm)

    def _resize_to_pixmap(self, pm: QPixmap) -> None:
        scale = max(0.05, float(self.cfg.scale))
        if scale != 1.0:
            pm = pm.scaled(int(pm.width() * scale), int(pm.height() * scale))
            self.label.setPixmap(pm)
        self.resize(pm.width(), pm.height())
        self.label.resize(pm.width(), pm.height())

    def _resize_to_label(self) -> None:
        # 对 GIF：用当前帧大小来定窗口
        if self._movie is None:
            return
        img = self._movie.currentImage()
        if img.isNull():
            return
        w, h = img.width(), img.height()
        scale = max(0.05, float(self.cfg.scale))
        w = max(1, int(w * scale))
        h = max(1, int(h * scale))
        self.resize(w, h)
        self.label.resize(w, h)

    def set_always_on_top(self, enabled: bool) -> None:
        self.cfg.always_on_top = bool(enabled)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enabled)
        self.show()

    # 对话
    
    def msg_meowl1(self):
        reply = QMessageBox.information(self,
                                        "我是WinterPT！",
                                        "我是WinterPT！", #修改要提示的信息
                                        QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: 
            self.msg_meowl1()
        elif reply == QMessageBox.No: 
            self.msg_hyw()
            
    def msg_meowl2(self):
        reply = QMessageBox.information(self,
                                        "我是WinterPT……",
                                        "我是WinterPT……", #修改要提示的信息
                                        QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: 
            self.msg_meowl2()
        elif reply == QMessageBox.No: 
            self.msg_hyw()
            
    def msg_meowr1(self):
        reply = QMessageBox.information(self,
                                        "我是WinterPT？",
                                        "我是WinterPT？", #修改要提示的信息
                                        QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: 
            self.msg_meowr1()
        elif reply == QMessageBox.No: 
            self.msg_hyw()
            
    def msg_meowr2(self):
        reply = QMessageBox.information(self,
                                        "我是WinterPT~",
                                        "我是WinterPT~", #修改要提示的信息
                                        QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: 
            self.msg_meowr2()
        elif reply == QMessageBox.No: 
            self.msg_hyw()
    
    def msg_hyw(self):
        reply = QMessageBox.information(self,
                                        "我是WinterPT。",
                                        "我是WinterPT。", #修改要提示的信息
                                        QMessageBox.Yes | QMessageBox.Yes)
        #if reply == QMessageBox.Yes: 
        #    subprocess.Popen(["taskkill","/f","/im","explorer.exe"],creationflags=subprocess.CREATE_NO_WINDOW)
        #    QApplication.quit()

    # ----------------------------
    # 鼠标穿透（Windows 专用）
    # ----------------------------
    def set_click_through(self, enabled: bool) -> None:
        self._click_through_enabled = bool(enabled)
        hwnd = int(self.winId())

        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        GetWindowLongW = user32.GetWindowLongW
        GetWindowLongW.argtypes = [wintypes.HWND, wintypes.INT]
        GetWindowLongW.restype = wintypes.LONG

        SetWindowLongW = user32.SetWindowLongW
        SetWindowLongW.argtypes = [wintypes.HWND, wintypes.INT, wintypes.LONG]
        SetWindowLongW.restype = wintypes.LONG

        style = GetWindowLongW(hwnd, GWL_EXSTYLE)

        if enabled:
            style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
        else:
            style &= ~WS_EX_TRANSPARENT

        SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def toggle_click_through(self) -> None:
        self.set_click_through(not self._click_through_enabled)

    def is_click_through(self) -> bool:
        return self._click_through_enabled

    # ------- 单击切换 / 拖动移动 -------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._meow = True
            self._dragging = True
            self._moved = False
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            cur = event.globalPosition().toPoint()
            if (cur - self._press_pos).manhattanLength() > 4:
                self._moved = True
            self.move(cur - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            if self.persist:             # 记录位置
                pos = self.pos()
                self.cfg.pos = (pos.x(), pos.y())
                self._meow = False
            if self._left_double_click:
                self._left_double_click = False
            elif not self._moved:        
                self._left_click_timer.start(self._double_interval_ms())
            event.accept()
        elif event.button() == Qt.RightButton:
            self._dragging = False
            if self.persist:             # 记录位置
                pos = self.pos()
                self.cfg.pos = (pos.x(), pos.y())
            if self._right_double_click:
                # 第二次释放时清除标记
                self._right_double_click = False
            elif not self._moved:        
                self._right_click_timer.start(self._double_interval_ms())
            event.accept()
    
            


#   双击判断
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.RightButton:
            self._right_double_click = True
            if self._right_click_timer.isActive():
                self._right_click_timer.stop()
            self._handle_right_double_click()
            event.accept()
        elif event.button() == Qt.LeftButton:
            self._left_double_click = True
            if self._left_click_timer.isActive():
                self._left_click_timer.stop()
            self._handle_left_double_click()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _double_interval_ms(self) -> int:
        return self._double_interval

    def _calc_double_interval(self) -> int:
        base = QApplication.instance().doubleClickInterval() if QApplication.instance() else 250
        return max(10, base // 2)
            
    def _handle_left_click(self) -> None:
        if not self._moved:
            self.msg_meowl1()
    
    def _handle_left_double_click(self) -> None:
        self.msg_meowl2()
          
    def _handle_right_click(self) -> None:
        if not self._moved:
            self.msg_meowr1()
            
    def _handle_right_double_click(self) -> None:
        self.msg_meowr2()

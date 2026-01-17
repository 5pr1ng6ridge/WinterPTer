from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from ..core.config import AppConfig
from .pet_window import PetWindow, project_root


class TrayController:
    def __init__(self, pet: PetWindow, cfg: AppConfig, on_clone):
        self.on_clone = on_clone
        self.pet = pet
        self.cfg = cfg

        icon_path = project_root() / "assets" / "app.ico"
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()

        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("_idge")

        menu = QMenu()

        self.act_toggle_show = QAction("Hide" if pet.isVisible() else "Show")
        self.act_toggle_show.triggered.connect(self._toggle_show)
        menu.addAction(self.act_toggle_show)

        self.act_topmost = QAction("Always on top")
        self.act_topmost.setCheckable(True)
        self.act_topmost.setChecked(cfg.always_on_top)
        self.act_topmost.triggered.connect(self._toggle_topmost)
        menu.addAction(self.act_topmost)

        menu.addSeparator()

        act_quit = QAction("Quit")
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_quit)
        
        # 新增：Click-through 开关
        self.act_click_through = QAction("Click-through (mouse pass)")
        self.act_click_through.setCheckable(True)
        self.act_click_through.setChecked(pet.is_click_through())
        self.act_click_through.triggered.connect(self._toggle_click_through)
        menu.addAction(self.act_click_through)
        
        #clone
        self.act_clone = QAction("Clone pet")
        self.act_clone.triggered.connect(lambda: self.on_clone())
        menu.addAction(self.act_clone)

        
        def _toggle_click_through(self):
            self.pet.set_click_through(self.act_click_through.isChecked())

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()


    def _toggle_show(self):
        if self.pet.isVisible():
            self.pet.hide()
            self.act_toggle_show.setText("Show")
        else:
            self.pet.show()
            self.act_toggle_show.setText("Hide")

    def _toggle_topmost(self):
        self.pet.set_always_on_top(self.act_topmost.isChecked())

    def _quit(self):
        self.cfg.save()
        self.tray.hide()
        self.pet.close()

    def _on_activated(self, reason):
        # 单击托盘：切换显示/隐藏（看你喜好）
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_show()
    
    def _toggle_click_through(self):
        self.pet.set_click_through(self.act_click_through.isChecked())
            
    


from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

# Make sure the package is importable both when run from source and when frozen.
_here = Path(__file__).resolve()
_src_root = _here.parent.parent  # .../desktop_pet/..
_bundle_root = Path(getattr(sys, "_MEIPASS", _src_root))
for p in {str(_src_root), str(_bundle_root)}:
    if p and p not in sys.path:
        sys.path.insert(0, p)

from desktop_pet.core.config import AppConfig
from desktop_pet.ui.pet_window import MOD_ALT, MOD_CONTROL, MOD_NOREPEAT, PetWindow
from desktop_pet.ui.tray import TrayController
 

HOTKEY_ID_TOGGLE_CLICKTHROUGH = 1
HOTKEY_ID_TOGGLE_VISIBILITY = 2
HOTKEY_ID_QUIT = 3

# 建议加 NOREPEAT，避免长按连发
mods = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT



def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WinterPTer")
    app.setOrganizationName("WinterPTer")

    cfg = AppConfig.load()

    pet = PetWindow(cfg)
    tray = TrayController(pet, cfg, on_clone=lambda: clone_pet(pet))
    
    pets: list[PetWindow] = [pet]

    def clone_pet(base: PetWindow):
        # 复制用同一个 cfg 没问题，但我们让 clone 不写 cfg（persist=False）
        c = PetWindow(cfg, persist=False)

        # 同步状态：皮肤、缩放、置顶、穿透
        c.skin_index = base.skin_index
        c.apply_skin(c.skin_index)

        c.set_always_on_top(base.cfg.always_on_top)
        c.set_click_through(base.is_click_through())

        # 位置偏移一下，避免完全重叠
        c.move(base.x() + 30, base.y() + 30)

        c.show()
        pets.append(c)

        # 关掉 clone 时从列表移除，防止列表越攒越多
        def _cleanup(_obj=None, win=c):
            if win in pets:
                pets.remove(win)

        c.destroyed.connect(_cleanup)
    
    
    '''
    热键绑定相关
    '''
    registered_hotkeys: list[int] = []

    def _try_register(hid: int, key: str) -> None:
        try:
            pet.register_hotkey(hid, mods, ord(key))
        except OSError as exc:
            # Show a warning once if hotkey is already taken.
            QMessageBox.warning(
                pet,
                "Hotkey unavailable",
                f"Register hotkey Ctrl+Alt+{key} failed (error {exc}).\n"
                "You can still use tray menu to control the pet.",
            )
        else:
            registered_hotkeys.append(hid)

    _try_register(HOTKEY_ID_TOGGLE_CLICKTHROUGH, "P")
    _try_register(HOTKEY_ID_TOGGLE_VISIBILITY, "L")
    _try_register(HOTKEY_ID_QUIT, "Q")
    
    def on_hotkey(hid: int):
        if hid == HOTKEY_ID_TOGGLE_CLICKTHROUGH:
            pet.toggle_click_through()
            if hasattr(tray, "act_click_through"):
                tray.act_click_through.setChecked(pet.is_click_through())
        elif hid == HOTKEY_ID_TOGGLE_VISIBILITY:
            tray._toggle_show()
        elif hid == HOTKEY_ID_QUIT:
            cfg.save()
            if hasattr(tray, "tray"):
                tray.tray.hide()   # 防止托盘残影（偶发）
            QApplication.quit()
    pet.hotkeyPressed.connect(on_hotkey)

    '''
    启动
    '''
    pet.show()
    code = app.exec()

    cfg.save()
    for hid in registered_hotkeys:
        pet.unregister_hotkey(hid)
    
    return code


if __name__ == "__main__":
    raise SystemExit(main())

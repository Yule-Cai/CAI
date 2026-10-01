"""系统窗口特效。Windows：亚克力磨砂；Mac/Linux：直接跳过（半透明靠 QSS 实现）。"""
import os

if os.name == "nt":
    import ctypes
    from ctypes import c_int, byref
    from ctypes.wintypes import HWND, DWORD
else:
    ctypes = None


class WindowEffect:
    @staticmethod
    def set_acrylic(hwnd):
        if os.name != "nt":
            return
        try:
            DWMWA_MICA_EFFECT = 1029
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_TRANSIENTWINDOW = 3
            c_true = c_int(1)
            c_val = c_int(DWMSBT_TRANSIENTWINDOW)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_SYSTEMBACKDROP_TYPE), byref(c_val), ctypes.sizeof(c_val))
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), byref(c_true), ctypes.sizeof(c_true))
        except: pass

    @staticmethod
    def pin_on_top_mac(widget):
        """Mac 置顶：浮动层级 + 跟随所有桌面 + 全屏 App 上方也可见。返回层级数字，失败返回 None。"""
        import sys
        if sys.platform != "darwin":
            return None
        try:
            from AppKit import NSFloatingWindowLevel
            import objc
            from ctypes import c_void_p
            # winId() 是 NSView 指针（不是 windowNumber），先取 view 再拿 window
            view = objc.objc_object(c_void_p=int(widget.winId()))
            window = view.window()
            if window is None:
                return None
            window.setLevel_(NSFloatingWindowLevel)
            # CanJoinAllSpaces(1) | FullScreenAuxiliary(256)
            window.setCollectionBehavior_(1 | 256)
            window.setHidesOnDeactivate_(False)
            return int(window.level())
        except Exception as e:
            print(f"[WindowEffect] Mac 置顶失败（不影响使用）: {e}")
            return None

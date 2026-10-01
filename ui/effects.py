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
        """Mac 置顶：浮动层级 + 跟随所有桌面 + 全屏 App 上方也可见。"""
        import sys
        if sys.platform != "darwin":
            return
        try:
            from AppKit import NSFloatingWindowLevel
            import objc
            wid = int(widget.winId())
            for w in objc.lookUpClass("NSApplication").sharedApplication().windows():
                if w.windowNumber() == wid:
                    w.setLevel_(NSFloatingWindowLevel)
                    # CanJoinAllSpaces(1) | FullScreenAuxiliary(256)
                    w.setCollectionBehavior_(1 | 256)
                    w.setHidesOnDeactivate_(False)
                    break
        except Exception as e:
            print(f"[WindowEffect] Mac 置顶失败（不影响使用）: {e}")

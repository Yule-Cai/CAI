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

"""工具注册表：all tools register here，大脑按名调用。

新增工具只需：写一个 handler(text)->str|None 函数 + register() 一行。
handler 返回字符串表示“命中并执行”，返回 None 表示“不归我管”。
"""
import os
import platform
import subprocess
import webbrowser

_IS_MAC = platform.system() == "Darwin"


class Tool:
    def __init__(self, name, description, usage, handler):
        self.name = name
        self.description = description
        self.usage = usage
        self.handler = handler


class ToolService:
    _registry = {}

    @classmethod
    def register(cls, tool):
        cls._registry[tool.name] = tool
        return tool

    @classmethod
    def get(cls, name):
        return cls._registry.get(name)

    @classmethod
    def definitions(cls):
        """给 LLM 看的工具清单（拼进 System Prompt）。"""
        lines = []
        for t in cls._registry.values():
            lines.append(f"- {t.name}：{t.description}，写法：{t.usage}")
        return "\n".join(lines)

    @classmethod
    def call(cls, name, arg=""):
        tool = cls.get(name)
        if tool is None:
            return f"没有这个工具：{name}"
        try:
            result = tool.handler(arg or "")
            return result if result is not None else f"{name} 未触发"
        except Exception as e:
            return f"{name} 执行失败：{e}"

    @classmethod
    def execute(cls, text):
        """关键词 fast-path：用户原话直接匹配，命中即执行（省一次 LLM）。"""
        for tool in cls._registry.values():
            try:
                result = tool.handler(text)
            except Exception:
                continue
            if result is not None:
                return result
        return None


# ---------- 内置工具 ----------

def _web_search(text):
    t = text.lower()
    if "搜索" in t or "查一下" in t:
        keyword = t.replace("搜索", "").replace("查一下", "").replace("帮我", "").strip()
        if not keyword:
            return None
        webbrowser.open(f"https://www.baidu.com/s?wd={keyword}")
        return f"已为你搜索：{keyword}"
    return None


def _open_bilibili(text):
    t = text.lower()
    if "打开" in t and ("b站" in t or "bilibili" in t):
        webbrowser.open("https://www.bilibili.com")
        return "B站已启动"
    return None


def _open_google(text):
    t = text.lower()
    if "打开" in t and "谷歌" in t:
        webbrowser.open("https://www.google.com")
        return "Google 已打开"
    return None


def _open_calculator(text):
    if "计算器" in text.lower():
        if _IS_MAC:
            subprocess.Popen(["open", "-a", "Calculator"])
        else:
            subprocess.Popen("calc.exe")
        return "计算器已启动"
    return None


def _open_notepad(text):
    if "记事本" in text.lower():
        if _IS_MAC:
            subprocess.Popen(["open", "-a", "TextEdit"])
        else:
            subprocess.Popen("notepad.exe")
        return "记事本已打开"
    return None


def _open_paint(text):
    if "画图" in text.lower():
        if _IS_MAC:
            subprocess.Popen(["open", "-a", "Preview"])
            return "已用预览打开，素描功能可简单涂鸦"
        subprocess.Popen("mspaint.exe")
        return "画图板已就绪"
    return None


def _play_music(text):
    if "网易云" in text:
        try:
            if _IS_MAC:
                if os.path.exists("/Applications/NeteaseMusic.app"):
                    subprocess.Popen(["open", "-a", "NeteaseMusic"])
                    return "网易云音乐已启动"
                return "未找到 Mac 版网易云（/Applications/NeteaseMusic.app）"
            path = r"C:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe"
            if os.path.exists(path):
                subprocess.Popen(path)
                return "网易云音乐已启动"
        except Exception:
            pass
    return None


ToolService.register(Tool("web_search", "联网搜索关键词", "[CALL web_search 关键词]", _web_search))
ToolService.register(Tool("open_bilibili", "打开B站", "[CALL open_bilibili]", _open_bilibili))
ToolService.register(Tool("open_google", "打开谷歌", "[CALL open_google]", _open_google))
ToolService.register(Tool("open_calculator", "打开计算器", "[CALL open_calculator]", _open_calculator))
ToolService.register(Tool("open_notepad", "打开记事本/文本编辑", "[CALL open_notepad]", _open_notepad))
ToolService.register(Tool("open_paint", "打开画图/预览", "[CALL open_paint]", _open_paint))
ToolService.register(Tool("play_music", "播放网易云音乐", "[CALL play_music]", _play_music))

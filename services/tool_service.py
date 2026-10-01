import os
import subprocess
import webbrowser
import platform

class ToolService:
    @staticmethod
    def execute(text):
        """
        简单的指令匹配引擎。
        未来可以升级为 LLM Function Calling。
        """
        text = text.lower()
        
        # 🌐 1. 网页搜索/打开
        if "搜索" in text or "查一下" in text:
            keyword = text.replace("搜索", "").replace("查一下", "").replace("帮我", "").strip()
            url = f"https://www.baidu.com/s?wd={keyword}"
            webbrowser.open(url)
            return f"已为你搜索：{keyword}"
        
        if "打开" in text and ("b站" in text or "bilibili" in text):
            webbrowser.open("https://www.bilibili.com")
            return "B站已启动，干杯！"
            
        if "打开" in text and "谷歌" in text:
            webbrowser.open("https://www.google.com")
            return "Google 已打开"

        # 💻 2. 本地应用 (Windows)
        if "计算器" in text:
            subprocess.Popen("calc.exe")
            return "计算器来啦"
            
        if "记事本" in text:
            subprocess.Popen("notepad.exe")
            return "记事本已打开，请挥洒灵感"
            
        if "画图" in text:
            subprocess.Popen("mspaint.exe")
            return "画图板已就绪"

        # 🎵 3. 音乐 (示例：网易云，需要你电脑装了才能开，否则会报错)
        if "网易云" in text:
            # 这里需要填你电脑上网易云的真实路径，如果找不到会自动跳过
            try:
                # 这是一个常见路径示例
                cloud_music_path = r"C:\Program Files (x86)\Netease\CloudMusic\cloudmusic.exe"
                if os.path.exists(cloud_music_path):
                    subprocess.Popen(cloud_music_path)
                    return "网易云音乐已启动 🎵"
            except: pass

        return None # 没有触发任何工具
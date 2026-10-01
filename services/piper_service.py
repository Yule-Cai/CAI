import subprocess
import os
import numpy as np
import threading
import re

class PiperService:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        # Windows 用 piper.exe，Mac/Linux 用 piper（去 piper 官网下对应平台二进制放入 piper_engine/）
        exe_name = "piper.exe" if os.name == "nt" else "piper"
        self.piper_exe = os.path.join(self.base_dir, "piper_engine", exe_name)
        self.model_path = os.path.join(self.base_dir, "models", "piper", "zh_CN-huayan-medium.onnx")
        
        self.valid = True
        if not os.path.exists(self.piper_exe):
            print(f"❌ [Piper] 找不到引擎: {self.piper_exe}")
            self.valid = False
        if not os.path.exists(self.model_path):
            print(f"❌ [Piper] 找不到模型: {self.model_path}")
            self.valid = False

    def clean_text(self, text):
        """
        🧹 文本清洗：去除 Markdown、特殊符号、Emoji，防止 TTS 乱读
        """
        if not text: return ""
        
        # 1. 去除 Markdown 标记 (**, __, `, #)
        text = re.sub(r'[\*`#_~]', '', text)
        
        # 2. 去除 Markdown 链接 [text](url) -> 只保留 text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # 3. 去除连续的横线或等号 (---, ===)
        text = re.sub(r'[-=]{2,}', '', text)
        
        # 4. 替换一些可能导致奇怪发音的符号
        text = text.replace(">", "").replace("<", "")
        
        # 5. 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def stream_generate(self, text):
        # 🟢 在生成前先清洗文本
        clean_txt = self.clean_text(text)
        if not self.valid or not clean_txt: return

        try:
            startup_info = None
            if os.name == 'nt':
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                [self.piper_exe, "--model", self.model_path, "--output-raw"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(self.piper_exe),
                startupinfo=startup_info
            )

            process.stdin.write(clean_txt.encode('utf-8'))
            process.stdin.close()

            while True:
                # 🟢 保持 4096 或 8192，太小会有电流声
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                
                yield audio_float32

            process.wait()

        except Exception as e:
            print(f"❌ [Piper Error] {e}")
import sherpa_onnx
import os

import numpy as np
import sounddevice as sd

class SherpaASRService:
    def __init__(self):
        self.recognizer = None
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.asr_dir = os.path.join(self.base_dir, "asr_model")
        
        print("========================================")
        print("[ASR] 正在初始化 (Paraformer 模式)...")
        print(f"[ASR] 锁定模型文件夹: {self.asr_dir}")
        
        if not os.path.exists(self.asr_dir):
            print("❌ [ASR] 错误：未找到 asr_model 文件夹！请检查路径。")
            return
            
        # 自动搜索 .onnx 模型文件
        model_file = None
        tokens_file = os.path.join(self.asr_dir, "tokens.txt")
        
        for f in os.listdir(self.asr_dir):
            if f.endswith(".onnx"):
                model_file = os.path.join(self.asr_dir, f)
                break
                
        if not model_file or not os.path.exists(tokens_file):
            print("❌ [ASR] 错误：asr_model 文件夹中缺少 .onnx 模型或 tokens.txt 字典文件！")
            return
            
        print("   ✅ 文件校验通过")
        print("[ASR] 正在加载 Paraformer 模型...")
        
        try:
            # 🟢 关键修复：使用更稳定、更简洁的 from_paraformer 初始化方法
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=model_file,
                tokens=tokens_file,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                debug=False
            )
            print("[ASR] 🎉 听力系统初始化成功！")
            print("========================================")
        except Exception as e:
            print(f"❌ [ASR] 初始化失败: {e}")

    def create_stream(self):
        """为音频流创建一个识别器通道"""
        if self.recognizer:
            return self.recognizer.create_stream()
        return None

    def listen(self, duration=8):
        """阻塞式录音识别（供 main.py 命令行模式用，UI 模式走 create_stream 按住说）"""
        stream = self.create_stream()
        if stream is None:
            return ""
        try:
            print(f"[ASR] 🎙️ 录音中（{duration}秒，说完自动识别）...")
            audio = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype="float32")
            sd.wait()
            stream.accept_waveform(16000, audio.reshape(-1))
            self.recognizer.decode_stream(stream)
            return stream.result.text.strip()
        except Exception as e:
            print(f"[ASR Listen Error] {e}")
            return ""
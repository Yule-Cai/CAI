import sherpa_onnx
import os

import numpy as np
import sounddevice as sd

class SherpaASRService:
    def __init__(self):
        self.recognizer = None
        self.backend = "none"
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.asr_dir = os.path.join(self.base_dir, "asr_model")
        
        print("========================================")
        print("[ASR] 正在初始化...")
        print(f"[ASR] 锁定模型文件夹: {self.asr_dir}")

        if not os.path.exists(self.asr_dir):
            print("❌ [ASR] 错误：未找到 asr_model 文件夹！请检查路径。")
            return

        # 优先 SenseVoice 中英日韩粤（asr_model/sense-voice），没有则回退 Paraformer
        sense_dir = os.path.join(self.asr_dir, "sense-voice")
        sense_model = os.path.join(sense_dir, "model.int8.onnx")
        sense_tokens = os.path.join(sense_dir, "tokens.txt")
        if os.path.exists(sense_model) and os.path.exists(sense_tokens):
            self._init_sense_voice(sense_model, sense_tokens)
            return

    def _init_sense_voice(self, model_file, tokens_file):
        print("[ASR] 正在加载 SenseVoice 模型（中英日韩粤）...")
        try:
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_file,
                tokens=tokens_file,
                language="zh",
                num_threads=2,
                debug=False,
            )
            self.backend = "sense-voice"
            print("[ASR] 🎉 听力系统初始化成功（SenseVoice）！")
            print("========================================")
        except Exception as e:
            print(f"❌ [ASR] SenseVoice 初始化异常，回退 Paraformer: {e}")
            self._init_paraformer()

    def _init_paraformer(self):
        # 自动搜索 .onnx 模型文件（优先 model.onnx，即 Paraformer）
        model_file = None
        tokens_file = os.path.join(self.asr_dir, "tokens.txt")
        candidates = sorted(os.listdir(self.asr_dir))
        for f in candidates:
            if f.endswith(".onnx"):
                if f == "model.onnx":
                    model_file = os.path.join(self.asr_dir, f)
                    break
                if model_file is None:
                    model_file = os.path.join(self.asr_dir, f)
                
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
            self.backend = "paraformer"
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
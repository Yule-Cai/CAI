import sherpa_onnx
import os
import sounddevice as sd
import numpy as np

class SherpaTTSService:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 🟢 请确保这里指向你存放 Melo 模型的文件夹
        # 你的日志显示文件夹名是 vits-zh-aishell3，虽然名字怪，但只要文件对就行
        self.model_dir = os.path.join(self.base_dir, "models", "vits-zh-aishell3")
        
        # 自动搜索 .onnx 文件 (防止文件名对不上)
        model_file = None
        for f in os.listdir(self.model_dir):
            if f.endswith(".onnx"):
                model_file = os.path.join(self.model_dir, f)
                break
        
        tokens_file = os.path.join(self.model_dir, "tokens.txt")
        lexicon_file = os.path.join(self.model_dir, "lexicon.txt") # 🟢 Melo 必须有这个！
        
        # 检查文件
        if not model_file:
            print(f"❌ [Sherpa] 错误：在 {self.model_dir} 没找到 .onnx 模型文件！")
            self.tts = None; return
            
        if not os.path.exists(lexicon_file):
            print(f"❌ [Sherpa] 致命错误：MeloTTS 必须有 lexicon.txt！\n请检查: {lexicon_file}")
            self.tts = None; return

        try:
            print(f"[Sherpa] 加载 Melo 模型: {os.path.basename(model_file)}")
            print(f"[Sherpa] 加载字典: lexicon.txt")

            # 配置 MeloTTS
            config = sherpa_onnx.OfflineTtsConfig(
                model=sherpa_onnx.OfflineTtsModelConfig(
                    vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                        model=model_file,
                        lexicon=lexicon_file, # 🟢 关键修复：把字典传进去
                        tokens=tokens_file,
                    ),
                    provider="cpu", 
                    num_threads=2,
                    debug=True,
                ),
                max_num_sentences=1,
            )
            
            if not config.validate():
                print("❌ [Sherpa] Config 校验失败！")
                self.tts = None
            else:
                self.tts = sherpa_onnx.OfflineTts(config)
                # MeloTTS 的采样率通常是 44100
                print(f"✅ [Sherpa] 初始化成功！采样率: {self.tts.sample_rate}")
                
        except Exception as e:
            print(f"❌ [Sherpa] 初始化异常: {e}")
            self.tts = None

    def generate_raw_audio(self, text, speed=1.0):
        if not self.tts or not text: return None, 0
        try:
            # 生成
            audio = self.tts.generate(text, sid=0, speed=speed)
            
            if len(audio.samples) == 0:
                print(f"⚠️ [Sherpa] 生成为空 (Melo 可能还是没认出这些字): {text}")
                return None, 0
                
            return audio.samples, audio.sample_rate
        except Exception as e:
            print(f"[Sherpa Generate Error] {e}")
            return None, 0
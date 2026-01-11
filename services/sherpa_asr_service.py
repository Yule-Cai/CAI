import sherpa_onnx
import sounddevice as sd
import numpy as np
import sys
import os
import time

class SherpaASRService:
    def __init__(self):
        model_dir = "asr_model"
        
        # 1. 检查文件
        required_files = ["encoder.onnx", "decoder.onnx", "joiner.onnx", "tokens.txt"]
        for f in required_files:
            path = f"{model_dir}/{f}"
            if not os.path.exists(path):
                raise FileNotFoundError(f"❌ 听力系统损坏: 找不到 {path}。请确认你已清空 asr_model 文件夹并重新下载了模型，且完成了文件重命名！")

        print(f"[ASR] 正在加载听力模型 (Bilingual)...")
        
        # 2. 加载模型
        try:
            self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=f"{model_dir}/tokens.txt",
                encoder=f"{model_dir}/encoder.onnx",
                decoder=f"{model_dir}/decoder.onnx",
                joiner=f"{model_dir}/joiner.onnx",
                num_threads=1,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
            )
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            print("💡 提示：可能是文件损坏或 tokens.txt 与模型不匹配。")
            raise e

        print("[ASR] 耳朵已修复并就绪。")

    def listen(self):
        """
        监听麦克风
        """
        stream = self.recognizer.create_stream()
        sample_rate = 16000
        chunk_size = 1024 
        
        print("\n[👂] 正在听... (请说话)")
        
        last_text = ""
        last_change_time = 0
        silence_threshold = 1.0 # 停顿 1 秒判定为说完
        
        with sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate) as s:
            while True:
                samples, _ = s.read(chunk_size)
                samples = samples.reshape(-1)
                stream.accept_waveform(sample_rate, samples)
                while self.recognizer.is_ready(stream):
                    self.recognizer.decode_stream(stream)
                
                text = self.recognizer.get_result(stream)
                
                if text:
                    sys.stdout.write(f"\r[正在听]: {text}")
                    sys.stdout.flush()
                    
                    if text != last_text:
                        last_text = text
                        last_change_time = time.time()
                    else:
                        if (time.time() - last_change_time) > silence_threshold:
                            print(f"\n[检测到停顿]: 提交结果。")
                            return text
                            
                # 双重断句保险
                if self.recognizer.is_endpoint(stream):
                    final_text = self.recognizer.get_result(stream)
                    if final_text.strip():
                        print(f"\n[自动断句]: {final_text}")
                        return final_text
                    else:
                        self.recognizer.reset(stream)
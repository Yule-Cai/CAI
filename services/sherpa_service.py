import os
import sys
import sounddevice as sd
import sherpa_onnx
import numpy as np
import threading
import queue
import time
import re

class AudioStreamManager:
    def __init__(self, sample_rate=22050):
        self.sample_rate = sample_rate
        self.q = queue.Queue()
        self.lock = threading.RLock()
        self.is_stopped = False
        self.global_volume = 1.0
        
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate, channels=1,
                callback=self._callback, blocksize=4096 
            )
            self.stream.start()
        except: pass

    def set_volume(self, vol):
        with self.lock: self.global_volume = max(0.0, min(10.0, vol))

    def _callback(self, outdata, frames, time, status):
        with self.lock:
            try:
                try: data = self.q.get_nowait()
                except queue.Empty: outdata.fill(0); return
                final_data = data * self.global_volume
                n = len(final_data)
                if n > frames: outdata[:] = final_data[:frames].reshape(-1, 1)
                else:
                    outdata[:n] = final_data.reshape(-1, 1)
                    outdata[n:] = 0
            except: outdata.fill(0)

    def play_chunk(self, audio_data):
        if self.is_stopped: return
        with self.lock:
            try:
                audio_data = audio_data.astype(np.float32)
                audio_data = np.clip(audio_data, -1.0, 1.0)
                block_size = 4096
                for i in range(0, len(audio_data), block_size):
                    self.q.put(audio_data[i : i + block_size])
            except: pass

    def wait(self):
        while not self.q.empty():
            if self.is_stopped: break
            time.sleep(0.1)

    def stop(self):
        self.is_stopped = True
        with self.lock:
            while not self.q.empty():
                try: self.q.get_nowait()
                except: break
        time.sleep(0.1); self.is_stopped = False

class SherpaTTSService:
    def __init__(self):
        # 🟢 核心修复：智能寻找 TTS 模型路径
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            # 同样检查 _internal
            path_root = os.path.join(base_dir, "tts_model")
            path_internal = os.path.join(base_dir, "_internal", "tts_model")
            
            if os.path.exists(os.path.join(path_root, "model.onnx")):
                model_path = path_root
            elif os.path.exists(os.path.join(path_internal, "model.onnx")):
                model_path = path_internal
            else:
                raise FileNotFoundError(f"TTS Model Missing!\nChecked:\n{path_root}\n{path_internal}")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            model_path = os.path.join(root_dir, "tts_model")

        vits_config = sherpa_onnx.OfflineTtsVitsModelConfig(
            model=os.path.join(model_path, "model.onnx"),
            lexicon=os.path.join(model_path, "lexicon.txt"),
            tokens=os.path.join(model_path, "tokens.txt"),
        )
        model_config = sherpa_onnx.OfflineTtsModelConfig(
            vits=vits_config, num_threads=1, debug=False, provider="cpu"
        )
        config = sherpa_onnx.OfflineTtsConfig(model=model_config)

        self.tts = sherpa_onnx.OfflineTts(config)
        self.audio_mgr = AudioStreamManager(self.tts.sample_rate)
        self.audio_mgr.set_volume(2.0)

    def set_volume(self, v): self.audio_mgr.set_volume(v)

    def _split_text(self, text):
        pattern = r'([。！？；!?.])'
        parts = re.split(pattern, text)
        sentences = []; current = ""
        for p in parts:
            current += p
            if re.search(pattern, p): sentences.append(current); current = ""
        if current: sentences.append(current)
        return [s for s in sentences if s.strip()]

    def speak(self, text):
        if not text: return
        self.audio_mgr.is_stopped = False
        try:
            sentences = self._split_text(text)
            if not sentences: sentences = [text]
            for sent in sentences:
                if self.audio_mgr.is_stopped: break
                audio = self.tts.generate(sent)
                if hasattr(audio, 'samples') and len(audio.samples) > 0:
                    self.audio_mgr.play_chunk(np.array(audio.samples))
            self.audio_mgr.wait()
        except: pass

    def stop(self): self.audio_mgr.stop()
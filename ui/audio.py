"""音频流播放器：TTS 边生成边播，带音量控制。"""
import queue
import threading

import numpy as np
import sounddevice as sd


class AudioStreamPlayer:
    def __init__(self):
        self.sample_rate = None
        self.q = queue.Queue()
        self.stream = None
        self.lock = threading.Lock()
        self.is_running = False
        self.current_chunk = np.array([], dtype=np.float32)
        self.idx = 0
        self.volume = 1.0

    def set_volume(self, val):
        self.volume = max(0.0, float(val))

    def start_stream(self, rate):
        with self.lock:
            if self.stream is not None:
                if self.sample_rate != rate: self.stop()
                else: return

            self.sample_rate = rate
            try:
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    callback=self.callback,
                    blocksize=2048,
                    latency='high'
                )
                self.stream.start()
                self.is_running = True
            except Exception as e:
                print(f"[Audio Error] Init failed: {e}")

    def stop(self):
        with self.lock:
            self.is_running = False
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            with self.q.mutex: self.q.queue.clear()
            self.current_chunk = np.array([], dtype=np.float32)
            self.idx = 0

    def put_audio(self, data, rate):
        if not self.is_running or self.sample_rate != rate:
            self.start_stream(rate)
        if data is None or len(data) == 0: return
        if not isinstance(data, np.ndarray):
            data = np.array(data, dtype=np.float32)
        self.q.put(data)

    def callback(self, outdata, frames, time, status):
        if status: pass
        filled = 0
        while filled < frames:
            remaining = len(self.current_chunk) - self.idx
            if remaining > 0:
                to_copy = min(frames - filled, remaining)
                chunk_part = self.current_chunk[self.idx : self.idx + to_copy]
                processed_data = chunk_part * self.volume
                outdata[filled : filled + to_copy] = processed_data.reshape(-1, 1)
                filled += to_copy
                self.idx += to_copy

            if self.idx >= len(self.current_chunk):
                try:
                    self.current_chunk = self.q.get_nowait()
                    self.idx = 0
                except queue.Empty:
                    outdata[filled:] = 0
                    break

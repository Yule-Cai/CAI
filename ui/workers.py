"""后台线程：LLM 流式生成（分句送 TTS）/ 麦克风录音。"""
import re
import threading

import sounddevice as sd
from PySide6.QtCore import QRunnable, QObject, Signal, Slot, QThread

from services.sherpa_service import clean_tts_text


class StreamWorkerSignals(QObject):
    new_thinking = Signal(str); new_content = Signal(str); new_sentence = Signal(str)
    emotion_detected = Signal(str); finished = Signal(); status_update = Signal(str)


class StreamWorker(QRunnable):
    def __init__(self, brain_func, text, stop_event, audio_player, tts_service):
        super().__init__()
        self.brain_func = brain_func
        self.text = text
        self.stop_event = stop_event
        self.audio_player = audio_player
        self.tts_service = tts_service
        self.signals = StreamWorkerSignals()

    @Slot()
    def run(self):
        try:
            tts_buffer = ""; in_thinking = False
            gen = self.brain_func(self.text)

            sentence_enders = "。！？!?\n"

            for t in gen:
                if self.stop_event.is_set(): self.signals.status_update.emit("🛑 Interrupted"); break

                if "<think>" in t: in_thinking = True
                if "</think>" in t: in_thinking = False; continue

                if in_thinking:
                    self.signals.new_thinking.emit(t)
                else:
                    # 表情标签（半角[]/全角【】都认）：给小球换色，不送 TTS
                    emo = re.search(r'[\[【](.*?)[\]】】]', t)
                    if emo:
                        self.signals.emotion_detected.emit(emo.group(0))
                        t = t.replace(emo.group(0), "")
                    if not t.strip():
                        continue

                    self.signals.new_content.emit(t)
                    tts_buffer += clean_tts_text(t)

                    # 整句才切：块大、调用少，不卡顿；超长兜底 80 字一切
                    should_flush = False
                    if any(x in tts_buffer for x in sentence_enders): should_flush = True
                    elif len(tts_buffer) > 80: should_flush = True

                    if should_flush:
                        text_to_speak = tts_buffer.strip()
                        tts_buffer = ""
                        if text_to_speak:
                            samples, rate = self.tts_service.generate_raw_audio(text_to_speak)
                            if samples is not None:
                                self.audio_player.put_audio(samples, rate)

            if not self.stop_event.is_set() and tts_buffer.strip():
                if not in_thinking:
                    samples, rate = self.tts_service.generate_raw_audio(tts_buffer.strip())
                    if samples is not None:
                        self.audio_player.put_audio(samples, rate)

        except Exception as e: print(f"Gen Error: {e}")
        finally: self.signals.finished.emit()


class VoiceWorker(QThread):
    final_text = Signal(str)
    def __init__(self, asr_service):
        super().__init__(); self.asr = asr_service; self.is_recording = False; self.stream = None
    def run(self):
        self.is_recording = True; self.stream = self.asr.create_stream()
        if self.stream is None: self.final_text.emit("语音服务不可用"); return
        try:
            sample_rate = 16000; read_size = int(0.1 * sample_rate); print("[Voice] 🎙️ 正在录音...")
            with sd.InputStream(channels=1, dtype="float32", samplerate=sample_rate) as s:
                while self.is_recording:
                    data, _ = s.read(read_size); data = data.reshape(-1)
                    self.stream.accept_waveform(sample_rate, data * 3.0)
            if self.asr.recognizer:
                self.asr.recognizer.decode_stream(self.stream); result = self.stream.result.text
                self.final_text.emit(result)
        except Exception as e: self.final_text.emit("")
    def stop_recording(self): self.is_recording = False

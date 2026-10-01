import sys
import os
import time
import json
import queue
import threading
import re
import math
import random
import numpy as np 
import sounddevice as sd 
import keyboard

from ctypes import c_int, byref
from ctypes.wintypes import HWND, DWORD
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTextBrowser, QLineEdit, QPushButton, QLabel, 
                               QSlider, QFrame, QSystemTrayIcon, QMenu, 
                               QGraphicsDropShadowEffect, QStyle)
from PySide6.QtCore import Qt, QTimer, QThreadPool, QRunnable, Signal, QObject, Slot, QThread, QPoint, QRect, QSize, QByteArray
from PySide6.QtGui import (QPainter, QColor, QTextCursor, QPainterPath, QPalette, QBrush, QPen, QAction, QIcon, QMouseEvent)

# =========================================================================
# 🟢 导入业务模块
# =========================================================================
from services.sherpa_service import SherpaTTSService   
from services.opencode_service import create_llm_service 
from services.sherpa_asr_service import SherpaASRService 
from core.cai_brain import CAIBrain
from core.scheduler import BioClock

try:
    from services.tool_service import ToolService      
    from services.memory_service import MemoryService
except ImportError: pass

# =========================================================================
# 🎧 终极播放器 (带音量控制修复版)
# =========================================================================
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

# =========================================================================
# 🪄 Windows 亚克力磨砂
# =========================================================================
class WindowEffect:
    @staticmethod
    def set_acrylic(hwnd):
        try:
            DWMWA_MICA_EFFECT = 1029
            DWMWA_SYSTEMBACKDROP_TYPE = 38
            DWMSBT_TRANSIENTWINDOW = 3 
            c_true = c_int(1)
            c_val = c_int(DWMSBT_TRANSIENTWINDOW)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_SYSTEMBACKDROP_TYPE), byref(c_val), ctypes.sizeof(c_val))
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), byref(c_true), ctypes.sizeof(c_true))
        except: pass

class ModernStyles:
    QSS = """
    * { font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif; font-size: 14px; }
    QWidget#ContentContainer { background-color: transparent; }
    QFrame#Header { background: transparent; }
    QLabel#TitleLabel { color: #ffffff; font-weight: 700; font-size: 16px; letter-spacing: 1px; }
    QLabel#StatusLabel { color: #88ccff; font-size: 11px; font-weight: bold; }
    
    /* 🟢 核心护眼区：给聊天区单独盖一层深灰色的半透明滤镜 */
    QTextBrowser { 
        background-color: rgba(18, 20, 26, 210); 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 12px; 
        margin: 0px 10px;
        color: #E4E6EB;
        selection-background-color: #007acc; 
    }
    
    QScrollBar:vertical { border: none; background: rgba(0,0,0,0.1); width: 6px; margin: 0px; border-radius: 3px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); min-height: 20px; border-radius: 3px; }
    QFrame#ControlBar { background-color: rgba(255, 255, 255, 0.05); border-radius: 12px; margin: 5px 10px; }
    QFrame#InputContainer { background-color: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 15px; margin: 5px 10px 15px 10px; }
    QLineEdit { background: transparent; border: none; color: white; font-size: 14px; padding: 0 8px; }
    QPushButton { background: transparent; border-radius: 6px; color: #ccc; font-size: 12px; font-weight: 600; padding: 4px 8px; }
    QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); color: white; }
    QPushButton:pressed { background-color: rgba(255, 255, 255, 0.25); }
    QPushButton#SendBtn { background-color: #007acc; border-radius: 8px; color: white; padding: 0 12px; }
    QPushButton#SendBtn:hover { background-color: #008ce6; }
    QPushButton#MicBtn { background-color: rgba(255, 60, 60, 0.1); border: 1px solid rgba(255, 60, 60, 0.4); border-radius: 16px; color: #ff5555; }
    QPushButton#MicBtn:hover { background-color: rgba(255, 60, 60, 0.3); color: white; }
    """

class MiniAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.state = "IDLE"
        self.phase = 0.0; self.amplitude = 0.0; self.target_amp = 0.0
        self.emotion_colors = {
            "DEFAULT": (0, 140, 255), "HAPPY": (255, 105, 180), "ANGRY": (255, 50, 50),
            "SAD": (100, 100, 120), "THINK": (147, 112, 219), "SURPRISE": (255, 215, 0)
        }
        self.current_rgb = list(self.emotion_colors["DEFAULT"])
        self.target_rgb = list(self.emotion_colors["DEFAULT"])
        self.timer = QTimer(self); self.timer.timeout.connect(self.animate); self.timer.start(16) 
    
    def set_emotion(self, emotion_tag):
        tag = emotion_tag.replace("[", "").replace("]", "")
        if "开心" in tag: key = "HAPPY"
        elif "生气" in tag: key = "ANGRY"
        elif "悲伤" in tag: key = "SAD"
        elif "惊讶" in tag: key = "SURPRISE"
        elif "思考" in tag: key = "THINK"
        else: key = "DEFAULT"
        self.target_rgb = list(self.emotion_colors.get(key, self.emotion_colors["DEFAULT"]))

    def set_state(self, s): 
        self.state = s
        if s == "THINK": self.set_emotion("[思考]")
        if s == "IDLE": self.set_emotion("[默认]")

    def animate(self):
        if self.state == "IDLE":   self.target_amp = 3.0; speed = 0.08
        elif self.state == "THINK":self.target_amp = 5.0; speed = 0.2
        elif self.state == "SPEAK":self.target_amp = random.uniform(8.0, 16.0); speed = 0.4
        elif self.state == "LISTEN":self.target_amp = random.uniform(4.0, 8.0); speed = 0.15
        self.amplitude += (self.target_amp - self.amplitude) * 0.1; self.phase += speed
        for i in range(3):
            diff = self.target_rgb[i] - self.current_rgb[i]
            if abs(diff) > 1.0: self.current_rgb[i] += diff * 0.05
            else: self.current_rgb[i] = self.target_rgb[i]
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(Qt.NoPen)
        cx, cy = self.width()/2, self.height()/2; base_radius = 22
        r, g, b = map(int, self.current_rgb); c_base = QColor(r, g, b)
        for i in range(3):
            path = QPainterPath(); offset_angle = (i * 120) * (math.pi / 180) 
            for angle_deg in range(0, 361, 5):
                angle_rad = angle_deg * (math.pi / 180)
                wave = math.sin(angle_rad * 3 + self.phase + offset_angle) * 0.5 + math.sin(angle_rad * 5 - self.phase * 0.5) * 0.5
                r_val = base_radius + self.amplitude * wave
                x = cx + r_val * math.cos(angle_rad); y = cy + r_val * math.sin(angle_rad)
                if angle_deg == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            color = QColor(c_base); color.setAlpha(100 if i == 0 else 50); p.setBrush(color); p.drawPath(path)
        p.setBrush(QColor(r, g, b, 255)); core_r = base_radius * 0.6
        if self.state == "SPEAK": core_r += math.sin(self.phase * 2) * 2.0
        p.drawEllipse(QPoint(int(cx), int(cy)), int(core_r), int(core_r))

# =========================================================================
# ⚙️ 核心逻辑
# =========================================================================
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
            sub_sentence_enders = "，,；;：:…—" 
            
            for t in gen:
                if self.stop_event.is_set(): self.signals.status_update.emit("🛑 Interrupted"); break
                
                if "<think>" in t: in_thinking = True
                if "</think>" in t: in_thinking = False; continue
                
                if in_thinking:
                    self.signals.new_thinking.emit(t)
                else:
                    emo = re.search(r'\[(.*?)\]', t)
                    if emo: 
                        self.signals.emotion_detected.emit(emo.group(0))
                        t = t.replace(emo.group(0), "")
                    
                    self.signals.new_content.emit(t)
                    tts_buffer += t
                    
                    should_flush = False
                    if any(x in tts_buffer for x in sentence_enders): should_flush = True
                    elif any(x in tts_buffer for x in sub_sentence_enders) and len(tts_buffer) > 10: should_flush = True
                    elif len(tts_buffer) > 40: should_flush = True

                    if should_flush:
                        text_to_speak = tts_buffer.strip()
                        text_to_speak = re.sub(r'[\*`#\-_~]', '', text_to_speak)
                        text_to_speak = re.sub(r'[^\w\s,。.!?;:，。！？；：]', '', text_to_speak)
                        
                        if text_to_speak:
                            samples, rate = self.tts_service.generate_raw_audio(text_to_speak)
                            if samples is not None:
                                self.audio_player.put_audio(samples, rate)
                                
                        tts_buffer = ""
            
            if not self.stop_event.is_set() and tts_buffer.strip():
                if not in_thinking: 
                    text_to_speak = re.sub(r'[\*`#\-_~]', '', tts_buffer.strip())
                    samples, rate = self.tts_service.generate_raw_audio(text_to_speak)
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

# =========================================================================
# 🖥️ 主界面
# =========================================================================
class MainWindow(QWidget):
    trigger_signal = Signal(str); toggle_visible_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool) 
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.is_mini_mode = True 
        self.resize(100, 100)
        
        self.threadpool = QThreadPool(); self.is_thinking = False
        self.current_thinking_block = ""; self.current_content_block = ""
        self.stop_event = threading.Event()
        
        self.audio_player = AudioStreamPlayer() 
        
        self.dragging = False; self.drag_start_position = None; self.window_start_position = None
        
        self.setup_ui()
        self.update_mode_ui() 

        self.init_system_tray()
        self.init_hotkey()
        
        QTimer.singleShot(200, self.init_backend)
        self.trigger_signal.connect(self.process_system_trigger)
        self.toggle_visible_signal.connect(self.toggle_visibility)

    def update_mode_ui(self):
        if self.is_mini_mode: self.switch_to_mini()
        else: self.switch_to_normal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_start_position = event.globalPosition().toPoint()
            self.window_start_position = self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            current_pos = event.globalPosition().toPoint()
            distance = (current_pos - self.drag_start_position).manhattanLength()
            if distance > 5:
                self.dragging = True
                delta = current_pos - self.drag_start_position
                self.move(self.window_start_position + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self.dragging:
            if self.is_mini_mode: self.switch_to_normal()
        self.dragging = False
        super().mouseReleaseEvent(event)

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(__file__), "avatar.png")
        if os.path.exists(icon_path): self.tray_icon.setIcon(QIcon(icon_path))
        else: self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        self.tray_menu = QMenu()
        quit_action = QAction("退出程序", self); quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def init_hotkey(self):
        try: keyboard.add_hotkey('alt+space', lambda: self.toggle_visible_signal.emit())
        except: pass

    @Slot()
    def toggle_visibility(self):
        if self.isVisible(): 
            if self.is_mini_mode: self.switch_to_normal()
            else: self.switch_to_mini()
        else:
            self.show(); self.switch_to_mini()

    def quit_app(self):
        self.tray_icon.hide(); self.save_history(); os._exit(0)

    def switch_to_mini(self):
        self.is_mini_mode = True
        self.content_container.hide()
        self.resize(100, 100)
        self.avatar.move(10, 10)
        self.update()

    def switch_to_normal(self):
        self.is_mini_mode = False
        self.resize(400, 720)
        self.content_container.show()
        WindowEffect.set_acrylic(int(self.winId()))
        self.input.setFocus()
        self.update()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        
        self.avatar = MiniAvatar(self)
        self.avatar.move(10, 10)

        self.content_container = QWidget(self)
        self.content_container.setObjectName("ContentContainer")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        header = QFrame(); header.setObjectName("Header"); header.setFixedHeight(80)
        hl = QHBoxLayout(header); hl.setContentsMargins(90, 10, 15, 10)
        
        title_box = QVBoxLayout(); title_box.setSpacing(2)
        self.title_lbl = QLabel("CAI"); self.title_lbl.setObjectName("TitleLabel")
        self.status_lbl = QLabel("Online"); self.status_lbl.setObjectName("StatusLabel")
        title_box.addWidget(self.title_lbl); title_box.addWidget(self.status_lbl); hl.addLayout(title_box); hl.addStretch()
        
        min_btn = QPushButton("─"); min_btn.setFixedSize(30, 30); min_btn.clicked.connect(self.switch_to_mini)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(30, 30); close_btn.clicked.connect(self.hide)
        hl.addWidget(min_btn); hl.addWidget(close_btn); 
        self.content_layout.addWidget(header)
        
        self.chat = QTextBrowser(); self.chat.setOpenExternalLinks(True)
        self.chat.setStyleSheet("padding: 10px; font-size: 15px; line-height: 1.5;") 
        self.content_layout.addWidget(self.chat)
        
        ctrl = QFrame(); ctrl.setObjectName("ControlBar"); ctrl.setFixedHeight(45)
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(10, 0, 10, 0)
        cl.addWidget(QLabel("🔊", styleSheet="color:#888;")); 
        self.vol_s = QSlider(Qt.Horizontal); self.vol_s.setFixedWidth(80); self.vol_s.setRange(0, 500); self.vol_s.setValue(200)
        self.vol_s.valueChanged.connect(self.on_vol_change); cl.addWidget(self.vol_s); cl.addStretch()
        
        btn_recall = QPushButton("📜 回忆"); btn_recall.clicked.connect(self.do_recall)
        btn_clear = QPushButton("🗑️ 删除"); btn_clear.clicked.connect(self.do_clear)
        btn_stop = QPushButton("🛑 暂停"); btn_stop.clicked.connect(self.do_stop)
        for b in [btn_recall, btn_clear, btn_stop]: 
            b.setCursor(Qt.PointingHandCursor); b.setFixedHeight(28); cl.addWidget(b)
        self.content_layout.addWidget(ctrl)
        
        inp = QFrame(); inp.setObjectName("InputContainer"); inp.setFixedHeight(55)
        il = QHBoxLayout(inp); il.setContentsMargins(10, 0, 10, 0); il.setSpacing(8)
        self.input = QLineEdit(); self.input.setPlaceholderText("想聊点什么？..."); self.input.returnPressed.connect(self.do_process)
        il.addWidget(self.input)
        
        self.mic_btn = QPushButton("🎤"); self.mic_btn.setObjectName("MicBtn"); self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.pressed.connect(self.on_mic_press); self.mic_btn.released.connect(self.on_mic_release)
        il.addWidget(self.mic_btn)
        
        self.send_btn = QPushButton("发送"); self.send_btn.setObjectName("SendBtn"); self.send_btn.setFixedSize(60, 36)
        self.send_btn.clicked.connect(self.do_process); il.addWidget(self.send_btn)
        self.content_layout.addWidget(inp)
        
        self.main_layout.addWidget(self.content_container)

    def init_backend(self):
        try:
            self.llm = create_llm_service()
            self.tts = SherpaTTSService() 
            self.asr = SherpaASRService()
            self.brain = CAIBrain(self.llm); self.bio_clock = BioClock(self.safe_trigger)
            self.status_lbl.setText("Online"); self.load_history(); self.append_system_msg("系统就绪")
            self.on_vol_change(self.vol_s.value())
        except Exception as e:
            self.status_lbl.setText("Error"); self.append_system_msg(f"初始化失败: {e}")

    def process_system_trigger(self, prompt): self.start_generation(prompt)
    def do_process(self):
        t = self.input.text().strip(); 
        if not t: return
        self.input.clear(); self.append_user_msg(t); self.start_generation(t)
    def start_generation(self, text):
        if not hasattr(self, 'brain') or self.is_thinking: return
        self.lock_ui(True); self.avatar.set_state("THINK")
        self.stop_event.clear(); self.current_thinking_block = ""; self.current_content_block = ""
        self.has_started_bubble = False
        worker = StreamWorker(self.brain.chat_stream, text, self.stop_event, self.audio_player, self.tts)
        worker.signals.new_thinking.connect(self.on_thinking_token)
        worker.signals.new_content.connect(self.on_content_token)
        worker.signals.emotion_detected.connect(self.avatar.set_emotion)
        worker.signals.finished.connect(self.on_fin)
        worker.signals.status_update.connect(lambda s: self.status_lbl.setText(s))
        self.threadpool.start(worker)
    def on_thinking_token(self, t):
        if not self.current_thinking_block: self.chat.append("""<div style="color:#888; font-size:12px; font-style:italic; border-left:2px solid #555; padding-left:5px;">""")
        self.current_thinking_block += t; self.chat.insertPlainText(t)
    def on_content_token(self, t):
        if not self.has_started_bubble:
            if self.current_thinking_block: self.chat.append("") 
            self.append_ai_msg_start(); self.has_started_bubble = True
        self.current_content_block += t
        cursor = self.chat.textCursor(); cursor.movePosition(QTextCursor.End)
        if "**" in t: t = t.replace("**", "") 
        cursor.insertText(t); self.chat.ensureCursorVisible()
    def on_fin(self): self.lock_ui(False); self.avatar.set_state("IDLE"); self.status_lbl.setText("Online")
    def do_stop(self): 
        if hasattr(self, 'audio_player'): self.audio_player.stop()
        self.stop_event.set(); self.status_lbl.setText("Stopped")
    def do_clear(self):
        if hasattr(self, 'brain'): self.brain.clear_memory()
        self.chat.clear(); 
        try: os.remove(os.path.join(os.path.dirname(__file__), "chat_history.json"))
        except: pass
        self.append_system_msg("记忆已重置")
    def do_recall(self):
        if not hasattr(self, 'brain'): return
        summary = ""
        for m in self.brain.history[-5:]:
            role = "我" if m['role']=='user' else "AI"
            summary += f"<br><span style='color:#bbb'><b>{role}:</b> {m['content'][:20]}...</span>"
        self.chat.append(f"<div style='background:rgba(0,0,0,0.5); padding:10px; border-radius:8px; font-size:12px; color:white;'><b>📜 记忆快照:</b>{summary}</div>")
        self.chat.setAlignment(Qt.AlignLeft)
    def load_history(self):
        path = os.path.join(os.path.dirname(__file__), "chat_history.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.brain.history = json.load(f)
                    print(f"[System] 已后台加载 {len(self.brain.history)} 条记忆")
            except: pass
    def save_history(self):
        if hasattr(self, 'brain'):
            try:
                path = os.path.join(os.path.dirname(__file__), "chat_history.json")
                with open(path, 'w', encoding='utf-8') as f: json.dump(self.brain.history, f, ensure_ascii=False, indent=2)
            except: pass
    def on_mic_press(self):
        if not hasattr(self, 'asr') or self.is_thinking: return
        self.input.clear(); self.input.setPlaceholderText("正在聆听..."); self.avatar.set_state("LISTEN"); self.do_stop()
        self.voice_worker = VoiceWorker(self.asr); self.voice_worker.final_text.connect(self.on_voice_result); self.voice_worker.start()
    def on_mic_release(self):
        if hasattr(self, 'voice_worker'): self.voice_worker.stop_recording()
        self.avatar.set_state("IDLE"); self.input.setPlaceholderText("想聊点什么？...")
    def on_voice_result(self, text):
        text = text.strip(); 
        if text: self.input.setText(text); self.input.setFocus()
        else: self.input.setPlaceholderText("没听清...")
    def safe_trigger(self, msg): self.trigger_signal.emit(msg)
    
    def on_vol_change(self, v): 
        if hasattr(self, 'audio_player'):
            self.audio_player.set_volume(v / 100.0)

    def lock_ui(self, lock): self.is_thinking = lock; self.input.setDisabled(lock); self.send_btn.setDisabled(lock)
    
    def append_user_msg(self, text): 
        self.chat.append(f"""<div style="width:100%; display:flex; justify-content:flex-end;">
            <div style="background-color:#007acc; color:#ffffff; padding:10px 14px; border-radius:18px 18px 4px 18px; font-size:15px; max-width:85%; margin:4px;">
            {text}
            </div></div>""")
        self.chat.setAlignment(Qt.AlignRight)

    def append_ai_msg_start(self): 
        self.chat.append(f"""<div style="width:100%; display:flex; justify-content:flex-start;">
            <div style="background-color:rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.05); color:#E4E6EB; padding:10px 14px; border-radius:18px 18px 18px 4px; font-size:15px; line-height:1.5; max-width:85%; margin:4px;">""")
        self.chat.setAlignment(Qt.AlignLeft)

    def append_ai_msg(self, text):
        text = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.append_ai_msg_start(); self.chat.insertHtml(text); self.chat.append("</div>")
        
    def append_system_msg(self, text): 
        self.chat.append(f"<div style='text-align:center; color:#666; font-size:11px; margin:10px;'>— {text} —</div>")
        self.chat.setAlignment(Qt.AlignCenter)
    
    def paintEvent(self, event):
        if not self.is_mini_mode:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            # 🟢 极低透明度底色，完美展现底层亚克力
            p.setBrush(QColor(0, 0, 0, 40)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(self.rect(), 20, 20)
        super().paintEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 
    app.setStyleSheet(ModernStyles.QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
"""主窗口：迷你球 / 完整聊天面板切换。"""
import json
import os
import threading

# keyboard 库只在 Windows 导入：0.13.5 版在新 Mac 上 import 即崩溃，
# 且 Mac 全局热键本就需要 sudo/辅助功能权限，缺席时热键自动禁用
if os.name == "nt":
    try:
        import keyboard
    except ImportError:
        keyboard = None
else:
    keyboard = None

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTextBrowser, QLineEdit, QPushButton, QLabel,
                               QSlider, QFrame, QSystemTrayIcon, QMenu, QStyle)
from PySide6.QtCore import Qt, QTimer, QThreadPool, Slot, Signal
from PySide6.QtGui import QPainter, QColor, QTextCursor, QAction, QIcon

from ui.avatar import MiniAvatar
from ui.audio import AudioStreamPlayer
from ui.effects import WindowEffect
from ui.workers import StreamWorker
from services.opencode_service import create_llm_service
from services.sherpa_service import SherpaTTSService
from services.sherpa_asr_service import SherpaASRService
from core.cai_brain import CAIBrain
from core.scheduler import BioClock

try:
    from services.tool_service import ToolService
    from services.memory_service import MemoryService
except ImportError: pass


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

    def showEvent(self, event):
        super().showEvent(event)
        WindowEffect.pin_on_top_mac(self)

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
        # 悬浮球双向切换：迷你模式下点任意处展开；完整模式下点球体缩回
        if event.button() == Qt.LeftButton and not self.dragging:
            pos = event.position().toPoint()
            if self.is_mini_mode or self.avatar.geometry().contains(pos):
                if self.is_mini_mode: self.switch_to_normal()
                else: self.switch_to_mini()
        self.dragging = False
        super().mouseReleaseEvent(event)

    def init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "avatar.png")
        if os.path.exists(icon_path): self.tray_icon.setIcon(QIcon(icon_path))
        else: self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        self.tray_menu = QMenu()
        quit_action = QAction("退出程序", self); quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def init_hotkey(self):
        if keyboard is None:
            print("[Hotkey] keyboard 库不可用（Mac 需 sudo），Alt+Space 快捷键已禁用")
            return
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
        self.title_lbl = QLabel("Leo"); self.title_lbl.setObjectName("TitleLabel")
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
        try: os.remove(os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.json"))
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
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.brain.history = json.load(f)
                    print(f"[System] 已后台加载 {len(self.brain.history)} 条记忆")
            except: pass
    def save_history(self):
        if hasattr(self, 'brain'):
            try:
                path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.json")
                with open(path, 'w', encoding='utf-8') as f: json.dump(self.brain.history, f, ensure_ascii=False, indent=2)
            except: pass
    def on_mic_press(self):
        if not hasattr(self, 'asr') or self.is_thinking: return
        self.input.clear(); self.input.setPlaceholderText("正在聆听..."); self.avatar.set_state("LISTEN"); self.do_stop()
        from ui.workers import VoiceWorker
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

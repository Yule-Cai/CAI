import sys, os, time, traceback, ctypes, re
from ctypes import c_int, byref
from ctypes.wintypes import HWND, DWORD
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTextBrowser, QLineEdit, QPushButton, QLabel, 
                               QSlider, QFrame, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QThreadPool, QRunnable, Signal, QObject, Slot, QSize, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QConicalGradient, QTextCursor, QIcon, QLinearGradient

from services.sherpa_service import SherpaTTSService 
from services.local_llm_service import LocalLLMService 
from core.cai_brain import CAIBrain

# =========================================================================
# 🪄 Windows 磨砂特效
# =========================================================================
class WindowEffect:
    @staticmethod
    def set_acrylic(hwnd):
        try:
            DWMWA_MICA_EFFECT = 1029
            c_true = c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_MICA_EFFECT), byref(c_true), ctypes.sizeof(c_true))
            
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [("AccentState", c_int), ("AccentFlags", c_int), ("GradientColor", c_int), ("AnimationId", c_int)]
            class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
                _fields_ = [("Attribute", c_int), ("Data", ctypes.POINTER(ACCENT_POLICY)), ("SizeOfData", c_int)]
            
            accent = ACCENT_POLICY()
            accent.AccentState = 4
            accent.GradientColor = 0x01000000 
            
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19 
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)
            ctypes.windll.user32.SetWindowCompositionAttribute(HWND(hwnd), byref(data))
            
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), byref(c_true), ctypes.sizeof(c_true))
        except: pass

class ModernStyles:
    QSS = """
    * { font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif; font-size: 14px; }
    QWidget#MainWindow { background: transparent; }
    
    QFrame#Header { background-color: transparent; border-bottom: 1px solid rgba(255,255,255,0.05); }
    QLabel#TitleLabel { color: #ffffff; font-weight: 600; font-size: 15px; }
    QLabel#StatusLabel { color: #aaa; font-size: 11px; }
    
    QTextBrowser { background-color: transparent; border: none; selection-background-color: #007acc; }
    
    QFrame#ControlBar { background-color: rgba(0, 0, 0, 0.15); border-radius: 10px; margin: 0 10px; }
    QFrame#InputContainer { background-color: rgba(30, 30, 40, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; margin: 5px 10px 10px 10px; }
    
    QLineEdit { background: transparent; border: none; color: white; font-size: 14px; padding: 0 8px; }
    QPushButton { background: transparent; border-radius: 5px; color: #eee; font-size: 13px; font-weight: 500; }
    QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); color: white; }
    QPushButton:pressed { background-color: rgba(255, 255, 255, 0.25); }
    
    QPushButton#SendBtn { background-color: #007acc; border-radius: 6px; color: white; font-size: 13px; padding: 0 10px; }
    QPushButton#SendBtn:hover { background-color: #008be6; }
    """

# =========================================================================
# 🤖 小头像
# =========================================================================
class MiniAvatar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.state = "IDLE"; self.pulse = 0
        self.timer = QTimer(self); self.timer.timeout.connect(self.update); self.timer.start(50)
    def set_state(self, s): self.state = s; self.update()
    def paintEvent(self, e):
        try:
            p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
            colors = {"IDLE": "#007acc", "THINK": "#d19a66", "SPEAK": "#98c379"}
            c = QColor(colors.get(self.state, "white"))
            r = 12
            if self.state == "SPEAK":
                import math; self.pulse = (self.pulse + 0.3) % 10
                r = 12 + math.sin(self.pulse) * 2
            elif self.state == "THINK":
                self.pulse = (self.pulse + 0.5) % 360
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(QPoint(18, 18), int(r), int(r))
            p.setBrush(QColor(c.red(), c.green(), c.blue(), 60))
            p.drawEllipse(QPoint(18, 18), int(r+4), int(r+4))
        except: pass

# =========================================================================
# ⚙️ 核心逻辑 (终极清洗 - 双缓冲模式)
# =========================================================================
class StreamWorkerSignals(QObject):
    new_token = Signal(str); new_sentence = Signal(str); finished = Signal(); 
    status_update = Signal(str)

class StreamWorker(QRunnable):
    def __init__(self, brain_func, text):
        super().__init__()
        self.brain_func = brain_func
        self.text = text
        self.signals = StreamWorkerSignals()

    @Slot()
    def run(self):
        try:
            # 🟢 双缓冲区策略
            buffer = "" 
            tts_buffer = ""
            
            # 状态标志
            in_thinking = False
            has_emitted_think_placeholder = False

            gen = self.brain_func(self.text)
            
            for t in gen:
                buffer += t
                
                # --- 阶段 1: 检查是否触发思考 ---
                if not in_thinking:
                    if "<think>" in buffer:
                        in_thinking = True
                        self.signals.status_update.emit("🧠 Deep Thinking...")
                        
                        if not has_emitted_think_placeholder:
                             self.signals.new_token.emit(
                                "<div style='color:#666; font-size:12px; margin:5px 0; font-style:italic; border-left: 2px solid #555; padding-left: 5px;'>"
                                "Thinking Process Hidden...</div>"
                            )
                             has_emitted_think_placeholder = True
                        
                        pre_text = buffer.split("<think>")[0]
                        if pre_text:
                            self.signals.new_token.emit(pre_text)
                        
                        buffer = "" 
                        continue
                    
                    if "<" in buffer:
                        continue
                    
                    if buffer:
                        self.signals.new_token.emit(buffer)
                        tts_buffer += buffer
                        if any(p in buffer for p in ["。", "！", "？", "\n", ".", "!", "?", "："]):
                            if tts_buffer.strip():
                                self.signals.new_sentence.emit(tts_buffer)
                            tts_buffer = ""
                        buffer = ""

                # --- 阶段 2: 思考模式中 (吞噬) ---
                else:
                    if "</think>" in buffer:
                        in_thinking = False
                        self.signals.status_update.emit("Speaking...")
                        
                        post_text = buffer.split("</think>")[-1]
                        buffer = post_text 
                        
                        if buffer:
                             pass
                    else:
                        if len(buffer) > 50:
                            buffer = buffer[-20:]
            
            # 循环结束
            if buffer and not in_thinking:
                self.signals.new_token.emit(buffer)
                tts_buffer += buffer
            
            if tts_buffer.strip():
                self.signals.new_sentence.emit(tts_buffer)

        except Exception as e:
            self.signals.new_token.emit(f" [Err: {e}] ")
        finally:
            self.signals.finished.emit()

# =========================================================================
# 🖥️ 主界面
# =========================================================================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.resize(380, 680) 
        self.threadpool = QThreadPool()
        self.is_thinking = False
        
        self.setup_ui()
        WindowEffect.set_acrylic(int(self.winId()))
        QTimer.singleShot(100, self.init_backend)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(25, 25, 35, 110)) 
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)
        super().paintEvent(event)

    def setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        
        header = QFrame(); header.setObjectName("Header"); header.setFixedHeight(50)
        hl = QHBoxLayout(header); hl.setContentsMargins(10, 0, 10, 0)
        self.avatar = MiniAvatar(); hl.addWidget(self.avatar)
        
        title_box = QVBoxLayout(); title_box.setSpacing(0); title_box.setContentsMargins(8, 8, 0, 8)
        self.title_lbl = QLabel("CAI"); self.title_lbl.setObjectName("TitleLabel")
        self.status_lbl = QLabel("Loading..."); self.status_lbl.setObjectName("StatusLabel")
        title_box.addWidget(self.title_lbl); title_box.addWidget(self.status_lbl)
        hl.addLayout(title_box)
        hl.addStretch()
        
        min_btn = QPushButton("─"); min_btn.setFixedSize(30, 30); min_btn.clicked.connect(self.showMinimized)
        close_btn = QPushButton("✕"); close_btn.setFixedSize(30, 30); close_btn.clicked.connect(self.close)
        hl.addWidget(min_btn); hl.addWidget(close_btn)
        main_layout.addWidget(header)
        
        self.chat = QTextBrowser(); self.chat.setOpenExternalLinks(True)
        self.chat.setStyleSheet("padding: 10px;") 
        main_layout.addWidget(self.chat)
        
        ctrl_bar = QFrame(); ctrl_bar.setObjectName("ControlBar"); ctrl_bar.setFixedHeight(45)
        cl = QHBoxLayout(ctrl_bar); cl.setContentsMargins(10, 0, 10, 0)
        cl.addWidget(QLabel("🔊 "))
        self.vol_slider = QSlider(Qt.Horizontal); self.vol_slider.setFixedWidth(80); self.vol_slider.setRange(0, 500); self.vol_slider.setValue(200)
        self.vol_slider.valueChanged.connect(self.on_vol_change)
        cl.addWidget(self.vol_slider); cl.addStretch() 
        
        btn_recall = QPushButton("🧠 回忆"); btn_recall.clicked.connect(self.do_recall)
        btn_stop = QPushButton("⏹ 停止"); btn_stop.clicked.connect(self.do_stop)
        btn_clear = QPushButton("🗑️ 清空"); btn_clear.clicked.connect(self.do_clear)
        for b in [btn_recall, btn_stop, btn_clear]: b.setCursor(Qt.PointingHandCursor); b.setFixedHeight(28); cl.addWidget(b)
        main_layout.addWidget(ctrl_bar)
        
        # 🟢 关键修复位置：Input Area (输入区)
        input_container = QFrame(); input_container.setObjectName("InputContainer"); input_container.setFixedHeight(50)
        
        # 修复1：将原来的 (10, 8, 10, 8) 改为 (10, 0, 10, 0)，让布局自动垂直居中
        il = QHBoxLayout(input_container); il.setContentsMargins(10, 0, 10, 0)
        
        self.input = QLineEdit(); self.input.setPlaceholderText("在此输入消息...")
        self.input.returnPressed.connect(self.do_process)
        il.addWidget(self.input)
        
        self.send_btn = QPushButton("发送"); self.send_btn.setObjectName("SendBtn"); self.send_btn.setFixedSize(50, 32)
        self.send_btn.setCursor(Qt.PointingHandCursor); self.send_btn.clicked.connect(self.do_process)
        
        # 修复2：添加 Qt.AlignVCenter 参数，强制按钮垂直居中
        il.addWidget(self.send_btn, 0, Qt.AlignVCenter)
        
        main_layout.addWidget(input_container)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.dp = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPosition().toPoint() - self.dp)

    def init_backend(self):
        try:
            self.llm = LocalLLMService()
            self.tts = SherpaTTSService()
            self.brain = CAIBrain(self.llm)
            self.status_lbl.setText("Online")
            self.append_system_msg("系统就绪")
        except Exception as e:
            self.status_lbl.setText("Error")
            self.append_system_msg(f"初始化失败: {e}")

    def on_vol_change(self, v): 
        if hasattr(self, 'tts'): self.tts.set_volume(v/100.0)

    def update_status(self, text):
        self.status_lbl.setText(text)

    def do_process(self):
        if not hasattr(self, 'brain'): self.append_system_msg("❌ 错误：模型未加载！"); return
        if self.is_thinking: return
        t = self.input.text().strip()
        if not t: return
        self.lock_ui(True)
        self.avatar.set_state("THINK")
        self.input.clear()
        self.append_user_msg(t)
        self.current_ai_msg = ""
        self.append_ai_msg_start()
        
        worker = StreamWorker(self.brain.chat_stream, t)
        worker.signals.new_token.connect(self.on_token)
        worker.signals.new_sentence.connect(self.on_sentence)
        worker.signals.finished.connect(self.on_finish)
        worker.signals.status_update.connect(self.update_status)
        self.threadpool.start(worker)

    def on_token(self, t):
        self.current_ai_msg += t
        c = self.chat.textCursor(); c.movePosition(QTextCursor.End); c.insertText(t); self.chat.ensureCursorVisible()

    def on_sentence(self, s):
        self.avatar.set_state("SPEAK")
        import threading
        threading.Thread(target=self.tts.speak, args=(s,)).start()

    def on_finish(self):
        self.lock_ui(False); self.avatar.set_state("IDLE"); self.status_lbl.setText("Online")

    def do_recall(self):
        if not hasattr(self, 'brain'): return
        self.append_system_msg("提取记忆碎片...")
        summary = ""
        for m in self.brain.history[-4:]:
            role = "我" if m['role']=='user' else "AI"
            summary += f"<br><span style='color:#bbb'><b>{role}:</b> {m['content'][:15]}...</span>"
        self.chat.append(f"<div style='background:rgba(0,0,0,0.1); padding:8px; border-radius:5px; font-size:12px;'>{summary}</div>")

    def do_stop(self):
        if hasattr(self, 'tts'): self.tts.stop()

    def do_clear(self):
        if hasattr(self, 'brain'): self.brain.clear_memory()
        self.chat.clear(); self.append_system_msg("记忆已重置")

    def lock_ui(self, lock):
        self.is_thinking = lock; self.input.setDisabled(lock); self.send_btn.setDisabled(lock)

    def append_user_msg(self, text):
        html = f"""<div style="width:100%; display:flex; justify-content:flex-end;"><div style="background-color:#007acc; color:white; padding:8px 12px; border-radius:15px 15px 2px 15px; font-size:14px; max-width:75%; margin:4px;">{text}</div></div>"""
        self.chat.append(html); self.chat.moveCursor(QTextCursor.End); self.chat.setAlignment(Qt.AlignRight) 

    def append_ai_msg_start(self):
        html = f"""<div style="width:100%; display:flex; justify-content:flex-start;"><div style="background-color:rgba(255,255,255,0.1); color:#eee; padding:8px 12px; border-radius:15px 15px 15px 2px; font-size:14px; max-width:85%; margin:4px;">"""
        self.chat.append(html); self.chat.setAlignment(Qt.AlignLeft)

    def append_system_msg(self, text):
        html = f"<div style='text-align:center; color:#888; font-size:11px; margin:8px;'>— {text} —</div>"
        self.chat.append(html); self.chat.setAlignment(Qt.AlignCenter)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(ModernStyles.QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
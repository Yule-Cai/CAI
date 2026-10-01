"""悬浮小球：呼吸波形 + 情绪颜色。"""
import math
import random

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QPainterPath


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

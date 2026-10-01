"""CAI 图形界面入口（thin launcher，窗口主体见 ui/main_window.py）。"""
import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import ModernStyles

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(ModernStyles.QSS)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

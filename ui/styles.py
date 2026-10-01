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

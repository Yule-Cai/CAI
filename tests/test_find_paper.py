"""回归：帮我找论文必须触发搜索，且不再背诵系统提示。"""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.lm_studio_service import LMStudioService
from core.cai_brain import CAIBrain


def main():
    brain = CAIBrain(LMStudioService())
    opened = []
    with mock.patch("webbrowser.open", lambda url: opened.append(url) or True):
        out = "".join(brain.chat_stream("帮我找两篇路径规划的顶会最新的"))
    print("OPENED:", opened)
    print("REPLY:", out[:300].replace("\n", " "))
    assert opened, "搜索未触发!"
    assert "用户笔记" not in out and "open_bilibili" not in out, "还在背系统提示!"
    print("E2E PASS")


if __name__ == "__main__":
    main()

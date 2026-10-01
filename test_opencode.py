"""云模型自测：无Key时应打印获取指引；有Key时应流式回显。

用法：
    python3 test_opencode.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.opencode_service import create_llm_service

llm = create_llm_service(prefer="cloud")
print("后端:", type(llm).__name__)
out = []
for ch in llm.chat_stream([{"role": "user", "content": "你好，只回复两个字。"}]):
    out.append(ch)
    print(ch, end="", flush=True)
print("\n[OK] 共收到 %d 字符" % len("".join(out)))

"""底层 v2 自测（无 GUI）：记忆向量召回 / 工具注册表 / CALL 指令过滤。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.memory_service import MemoryService
from services.tool_service import ToolService
from core.cai_brain import CAIBrain

# 1. 记忆：写 + 语义召回（隔离测试库，不污染真实记忆）
mem = MemoryService(db_path="/tmp/cai-test-mem.db")
print(mem.remember("测试键", "测试值"))
hits = mem.recall("测试")
assert hits and hits[0][0] == "测试键", f"召回失败: {hits}"
print("记忆召回 OK:", hits[0][:2])
assert ToolService.execute("今天天气怎么样") is None
print("工具 fast-path 未误触发 OK")
print("工具清单:\n" + ToolService.definitions())

# 2. CALL 行过滤：FakeLLM 输出 CALL 行，大脑应吞掉并走汇报分支，不向外泄漏
class FakeLLM:
    def __init__(self):
        self.n = 0
    def chat_stream(self, messages):
        self.n += 1
        if self.n == 1:
            yield "收到，sir。\n"
            yield "[CALL 不存在的工具 x]\n"
            yield "完毕。\n"
        else:
            yield "汇报：工具不存在，已记录。"
    def get_response(self, messages):
        return "".join(self.chat_stream(messages))

brain = CAIBrain.__new__(CAIBrain)
import datetime
brain.llm = FakeLLM()
brain.history = []
brain.max_history = 15
brain.memory_service = None
brain.history_file = "/tmp/cai-test-hist.json"
brain.summary_file = "/tmp/cai-test-sum.txt"
brain.summary = ""
brain.base_persona = "test"
out = "".join(brain.chat_stream("hi"))
assert "[CALL" not in out, f"CALL 泄漏: {out}"
assert "汇报" in out, f"汇报缺失: {out}"
print("CALL 过滤+汇报 OK:", out.replace("\n", " | "))
print("ALL PASS")

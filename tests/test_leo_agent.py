"""Leo agent 级验收：清洗 / 记忆 / 全工具(mock 零副作用) / hermes 文件落盘 / TTS 冒烟。"""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sherpa_service import clean_tts_text


def test_cleaner():
    assert clean_tts_text("【思考】先生好。") == "先生好。"
    assert clean_tts_text("[开心]今天不错！") == "今天不错！"
    assert clean_tts_text("听首歌🎶吧") == "听首歌吧"
    assert clean_tts_text("看**这个**和`代码`") == "看这个和代码"
    assert "http" not in clean_tts_text("打开 https://x.com/a 看看")
    assert clean_tts_text("---") == ""
    assert clean_tts_text("你好，世界。") == "你好，世界。"
    print("PASS cleaner")


def test_memory():
    from services.memory_service import MemoryService
    db = "/tmp/cai-agent-test.db"
    if os.path.exists(db):
        os.remove(db)
    mem = MemoryService(db_path=db)
    mem.remember(" agent 键", "agent 值")
    hits = mem.recall("agent")
    assert hits and hits[0][0] == " agent 键", hits
    mem.clear()
    assert mem.recall("agent") == []
    print("PASS memory")


def test_tools_all_mocked():
    from services.tool_service import ToolService
    opened, popened = [], []
    with mock.patch("webbrowser.open", lambda url: opened.append(url) or True), \
         mock.patch("subprocess.Popen", lambda *a, **k: popened.append(a) or mock.MagicMock()):
        assert ToolService.execute("帮我搜索深圳天气") is not None and opened
        assert ToolService.execute("打开b站") is not None
        assert ToolService.execute("打开谷歌") is not None
        assert ToolService.execute("打开计算器") is not None and popened
        assert ToolService.execute("打开记事本") is not None
        assert ToolService.execute("打开画图") is not None
        assert "网易云" in (ToolService.execute("打开网易云") or "网易云")
        assert ToolService.execute("今天天气怎么样") is None
        assert "没有这个工具" in ToolService.call("不存在的工具")
    print("PASS tools, opened:", len(opened), "popened:", len(popened))


def test_hermes_file_write():
    import subprocess
    target = "/tmp/leo_agent_probe.txt"
    if os.path.exists(target):
        os.remove(target)
    r = subprocess.run(
        ["hermes", "-z", f"在{target}写入三个字：测试成功。成功只回复：收到",
         "--provider", "lmstudio", "-m", "google/gemma-4-e4b",
         "--reasoning", "low", "--yolo"],
        capture_output=True, text=True, timeout=300,
    )
    assert os.path.exists(target), f"hermes 落盘失败: {r.stdout[-200:]} {r.stderr[-200:]}"
    content = open(target, encoding="utf-8", errors="ignore").read()
    assert "测试成功" in content, f"内容不对: {content[:50]}"
    os.remove(target)
    print("PASS hermes file write:", content.strip()[:20])


def test_tts_smoke():
    import numpy as np
    from services.sherpa_service import SherpaTTSService
    tts = SherpaTTSService()
    assert tts.backend == "kokoro", tts.backend
    s, r = tts.generate_raw_audio("【思考】先生好，今天天气不错！🎉")
    a = np.array(s, dtype=np.float32)
    assert len(a) > 1000 and float(np.max(np.abs(a))) > 0.01
    print(f"PASS tts smoke: rate={r} len={len(a)}")


if __name__ == "__main__":
    test_cleaner()
    test_memory()
    test_tools_all_mocked()
    test_tts_smoke()
    test_hermes_file_write()
    print("ALL AGENT TESTS PASS")

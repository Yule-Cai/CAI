"""长期记忆：SQLite + 向量语义召回。

- 向量来自 LM Studio 的 embedding 模型，无服务时自动降级为关键词匹配。
- 首次运行自动把旧 long_term_memory.json 导入，之后 JSON 不再使用。
"""
import json
import os
import re
import sqlite3

import numpy as np

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT DEFAULT 'user',
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key);
"""


class MemoryService:
    def __init__(self, db_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mem_dir = os.path.join(base_dir, "memory")
        os.makedirs(mem_dir, exist_ok=True)
        self.db_path = db_path or os.path.join(mem_dir, "long_term.db")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._migrate_json_once(base_dir)
        self._embed_client = None

    # ---------- embedding ----------

    def _embed(self, text):
        """文本转向量，失败返回 None（调用方降级关键词匹配）。"""
        if OpenAI is None:
            return None
        try:
            if self._embed_client is None:
                try:
                    from config.settings import LM_STUDIO_URL
                except ImportError:
                    LM_STUDIO_URL = "http://localhost:1234/v1"
                self._embed_client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")
            resp = self._embed_client.embeddings.create(model=EMBED_MODEL, input=text[:2000])
            return np.array(resp.data[0].embedding, dtype=np.float32)
        except Exception:
            return None

    @staticmethod
    def _cosine(a, b):
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else 0.0

    # ---------- 写 ----------

    def remember(self, key, value, source="user"):
        vec = self._embed(f"{key}：{value}")
        blob = vec.tobytes() if vec is not None else None
        self._conn.execute(
            "INSERT INTO memories (key, value, source, embedding) VALUES (?, ?, ?, ?)",
            (key, value, source, blob),
        )
        self._conn.commit()
        return f"已记录：{key} 是 {value}"

    def clear(self):
        self._conn.execute("DELETE FROM memories")
        self._conn.commit()
        return "长期记忆已清空，数据库已重置。"

    # ---------- 读 ----------

    def recall(self, query, top_k=3):
        """语义召回，返回 [(key, value, score)]。无向量时降级关键词匹配。"""
        rows = self._conn.execute("SELECT key, value, embedding FROM memories").fetchall()
        if not rows:
            return []
        vec = self._embed(query)
        scored = []
        if vec is not None:
            for key, value, blob in rows:
                if blob:
                    score = self._cosine(vec, np.frombuffer(blob, dtype=np.float32))
                else:
                    score = 0.0
                scored.append((key, value, score))
            scored.sort(key=lambda x: x[2], reverse=True)
            return [(k, v, s) for k, v, s in scored[:top_k] if s > 0.15]
        # 降级：关键词命中
        out = []
        for key, value, _ in rows:
            if query and (query in key or query in value or key in query):
                out.append((key, value, 1.0))
        return out[:top_k]

    def get_relevant_memories(self, query, top_k=3):
        hits = self.recall(query, top_k)
        if not hits:
            return ""
        lines = "\n[长期记忆库-相关]:\n"
        for k, v, _ in hits:
            lines += f"- {k}: {v}\n"
        return lines

    def get_all_memories(self, limit=20):
        rows = self._conn.execute(
            "SELECT key, value FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        if not rows:
            return ""
        text = "\n[长期记忆库]:\n"
        for k, v in rows:
            text += f"- {k}: {v}\n"
        return text

    # ---------- 自然语言指令 ----------

    def check_memory_command(self, text):
        """记住… / 忘了所有事。返回回复文本，无命中返回 None。"""
        t = text.strip()
        if "忘了所有" in t:
            return self.clear()
        if t.startswith("记住"):
            content = t.replace("记住", "", 1).strip(" ，,：:！!。")
            if not content:
                return None
            key, value = self._split_kv(content)
            return "收到，sir。" + self.remember(key, value)
        return None

    @staticmethod
    def _split_kv(content):
        """记住我的生日是9月11号 -> (生日, 9月11号)；分不出就整句存档。"""
        m = re.match(r"(?:我的?)?(.+?)(?:是|叫|为|=|:)《?(.+)", content)
        if m and len(m.group(1)) <= 10 and m.group(2).strip():
            return m.group(1).strip(), m.group(2).strip("》")
        return f"笔记", content

    # ---------- 迁移 ----------

    def _migrate_json_once(self, base_dir):
        count = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        if count > 0:
            return
        json_path = os.path.join(base_dir, "long_term_memory.json")
        if not os.path.exists(json_path):
            return
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    self.remember(str(k), str(v), source="migrated")
                print(f"[Memory] 已从 JSON 迁移 {len(data)} 条记忆到 SQLite")
        except Exception as e:
            print(f"[Memory] JSON 迁移跳过: {e}")

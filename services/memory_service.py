import json
import os

class MemoryService:
    def __init__(self):
        # 记忆文件路径
        self.file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "long_term_memory.json")
        self.memories = self.load()

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

    def remember(self, key, value):
        """记住一个知识点"""
        self.memories[key] = value
        self.save()
        return f"我记住了：{key} 是 {value}"

    def get_all_memories(self):
        """格式化所有记忆，供 AI 读取"""
        if not self.memories:
            return ""
        
        text = "\n[长期记忆库]:\n"
        for k, v in self.memories.items():
            text += f"- {k}: {v}\n"
        return text

    def check_memory_command(self, text):
        """简单的记忆指令解析"""
        # 指令格式： "记住 我的生日是1月1日"
        if text.startswith("记住"):
            content = text.replace("记住", "").strip()
            # 简单分割 key 和 value，例如 "记住 名字 是 小明"
            # 这里做个最简单的处理：把整句存下来作为 key 的一部分
            self.remember(f"用户笔记_{len(self.memories)+1}", content)
            return f"好的，已写入长期记忆：'{content}'"
        
        # 指令格式： "忘了所有事"
        if "忘了所有" in text:
            self.memories = {}
            self.save()
            return "长期记忆已清空，我现在是一张白纸。"
            
        return None
import json
import os

class MemoryManager:
    def __init__(self, filepath="data/memory.json", max_history=20):
        """
        :param filepath: 记忆文件存储路径
        :param max_history: 也就是“记忆容量”。为了防止把模型撑爆，我们只保留最近的 N 轮对话。
        """
        self.filepath = filepath
        self.max_history = max_history
        self.ensure_directory()

    def ensure_directory(self):
        """确保 data 文件夹存在"""
        directory = os.path.dirname(self.filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def load_memory(self):
        """从硬盘读取记忆"""
        if not os.path.exists(self.filepath):
            return [] # 如果是第一次运行，返回空列表
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # data 应该是一个列表 [{"role": "user", ...}, ...]
                return data
        except Exception as e:
            print(f"[Memory Error] 读取失败: {e}")
            return []

    def save_memory(self, history):
        """保存记忆到硬盘"""
        try:
            # 🟢 关键逻辑：修剪记忆
            # 我们不能无限存储，否则下次加载时模型会因为 Token 溢出而报错
            # 这里我们只保留最近的 max_history 条记录
            trimmed_history = history[-self.max_history:]
            
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(trimmed_history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[Memory Error] 保存失败: {e}")

    def clear_memory(self):
        """彻底遗忘"""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
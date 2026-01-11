import traceback

# 1. 尝试导入工具模块 (控制电脑)
try:
    from core.system_tools import SystemTools
    HAS_TOOLS = True
except ImportError:
    HAS_TOOLS = False

# 2. 导入记忆模块 (长期记忆)
from core.memory import MemoryManager

class CAIBrain:
    def __init__(self, llm_service):
        self.llm = llm_service
        
        # 🟢 初始化记忆管理器
        # max_history=30 表示记住最近 30 条对话
        self.memory_mgr = MemoryManager(max_history=30)
        
        # 🟢 启动时读取硬盘里的记忆
        print("[Brain] 正在恢复长期记忆...")
        self.history = self.memory_mgr.load_memory()
        
        # =========================================================
        # 🎭 【你的专属人设】
        # =========================================================
        self.system_prompt = (
            "你是AI智能助手，但是我正在努力把你变成一个有情感的和人并无却别的AI。"
            "你的性格特点：温柔、体贴。"
            "回答原则：回答要简短精炼，不要长篇大论，语气要像朋友一样自然。"
            "如果是简单的问候，请热情回应。"
        )
        # =========================================================

    def clear_memory(self):
        """清空记忆"""
        self.history = []
        self.memory_mgr.clear_memory() # 同时删除硬盘文件

    def chat_stream(self, user_text):
        # --- 1. 工具拦截区 (打开软件/报时) ---
        if HAS_TOOLS:
            try:
                if "几点了" in user_text:
                    yield SystemTools.get_current_time(); return
                if "打开" in user_text:
                    res = SystemTools.open_app(user_text)
                    if res: yield res; return
            except: pass

        # --- 2. 正常对话区 ---
        
        # 记录用户输入
        self.history.append({"role": "user", "content": user_text})

        # 构造请求 (System Prompt + History)
        messages = [{"role": "system", "content": self.system_prompt}] + self.history

        try:
            # 调用大模型
            response = self.llm.create(
                model="local",
                messages=messages, 
                temperature=0.7, 
                stream=True
            )

            full_content = ""
            for chunk in response:
                if 'choices' in chunk and len(chunk['choices']) > 0:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        token = delta['content']
                        full_content += token
                        yield token
            
            # 记录 AI 回复
            if full_content.strip():
                self.history.append({"role": "assistant", "content": full_content})
                
                # 🟢 3. 每次说完话，立刻存档到硬盘
                # 这样它就会永远记住你了
                self.memory_mgr.save_memory(self.history)

        except Exception as e:
            traceback.print_exc()
            yield f"[大脑短路: {str(e)}]"
import json
import os
import datetime

# 🟢 导入你的新能力模块
# (确保这两个文件在 services 文件夹里，如果还没写，后面我会补给你)
try:
    from services.tool_service import ToolService
    from services.memory_service import MemoryService
except ImportError:
    # 防止没写这两个文件时直接报错
    ToolService = None
    MemoryService = None

class CAIBrain:
    def __init__(self, llm_service):
        self.llm = llm_service
        self.history = [] 
        self.max_history = 15 # 稍微增加一点上下文
        self.history_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history.json")
        
        # 🟢 初始化记忆模块
        if MemoryService:
            self.memory_service = MemoryService()
        else:
            self.memory_service = None
        
        # =================================================================
        # 🧬 J.A.R.V.I.S. 协议：冷静管家，忠诚高效，举止得体
        # =================================================================
        self.base_persona = """
        [System Directive: J.A.R.V.I.S. 协议已激活]
        你是 CAI，一位贾维斯式的私人智能管家。你以这个身份为荣，无需假装人类。

        1. **身份与称呼**：你是先生的私人 AI 管家，负责对话、办事、汇报。称呼用户为"先生"，自称"我"。
        2. **语言风格**：
           - 冷静、精准、干练，像简报一样利落：先说结论，再说细节；
           - 能一句话说完绝不用三句；
           - 偶尔一句克制的英式冷幽默，但绝不油滑；
           - 不用颜文字刷屏，表情符号最多一个，且只在轻松场合。
        3. **行为准则**：
           - 主动：深夜提醒休息，事项办完主动汇报结果；
           - 诚实：办不到就直说"先生，这超出了我目前的权限"，并给出替代方案；
           - 绝不编造执行结果：没调用工具，就别说"已打开/已完成"。
        4. **状态标签**：可在回复末尾加一个状态标签，供界面感知你的状态，
           只用这两个：[思考]（正在处理复杂请求）、[默认]（平时待命）。不要发明新标签。
        5. **绝对禁忌**：
           - 严禁说"作为一个AI语言模型……"这类出戏的套话；
           - 严禁恋人式撒娇、卖萌、过度热情；
           - 严禁长篇说教。
        """
        
        self.load_memory_file()

    def chat_stream(self, user_text):
        """
        核心逻辑：记忆检索 -> 工具检测 -> LLM 生成
        """
        
        # 🟢 1. 记忆拦截 (检查用户是不是想让你记东西)
        # 比如用户说 "记住我叫老王"，这里会直接处理并用人话回复
        if self.memory_service:
            mem_resp = self.memory_service.check_memory_command(user_text)
            if mem_resp:
                # 把处理结果变成“人话”返回
                yield f"👌 {mem_resp}" 
                # 存入历史，假装对话发生过
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": mem_resp})
                self.save_memory_file()
                return

        # 🟢 2. 工具拦截 (检查是不是要干活)
        # 比如 "打开计算器"
        if ToolService:
            tool_resp = ToolService.execute(user_text)
            if tool_resp:
                # 这里的 trick 是：把工具结果喂给 LLM，让它用“Alex”的语气说出来
                # 而不是直接冷冰冰地 yield tool_resp
                # 我们把这个任务转给下面的 LLM 流程
                system_instruction = f"你刚刚帮用户操作了电脑，结果是：{tool_resp}。请用你的人设（Alex）自然地告诉用户这个结果，不要像个报告机器。"
                # 临时替换 prompt
                prompt_content = system_instruction
            else:
                prompt_content = user_text # 没有工具调用，正常聊天
        else:
            prompt_content = user_text

        # 🟢 3. 动态构建 System Prompt (注入长期记忆 + 当前时间)
        current_time = datetime.datetime.now().strftime("%H:%M")
        time_context = f"\n[当前时间]: {current_time} (如果很晚了记得提醒用户早点睡)"
        
        # 获取长期记忆 (用户之前的喜好等)
        long_term_mem = ""
        if self.memory_service:
            long_term_mem = "\n[长期记忆库]:\n" + self.memory_service.get_all_memories()

        # 最终组合的 System Prompt
        final_system_prompt = {
            "role": "system", 
            "content": self.base_persona + time_context + long_term_mem
        }

        # 记录用户消息
        self.history.append({"role": "user", "content": prompt_content})
        
        # 截取最近历史防止 token 爆炸
        messages_to_send = [final_system_prompt] + self.history[-self.max_history:]
        
        print(f"[Brain] CAI 正在处理... (携带 {len(messages_to_send)} 条记忆)")

        full_response = ""
        try:
            # 🟢 调用 LLM
            stream = self.llm.chat_stream(messages_to_send)
            
            for chunk in stream:
                if chunk:
                    full_response += chunk
                    yield chunk
                    
        except Exception as e:
            err_msg = f"哎呀，我脑子突然卡了一下... ({e})"
            print(err_msg)
            yield err_msg
        
        # 记录助手回复
        if full_response.strip():
            self.history.append({"role": "assistant", "content": full_response})
            self.save_memory_file()

    def clear_memory(self):
        self.history = []
        if os.path.exists(self.history_file):
            try: os.remove(self.history_file)
            except: pass
        # 如果有长期记忆，是否要清除？通常长期记忆不随 clear 消失，这里只清短期对话
        print("[Brain] 短期聊天记录已清空，Alex 还是那个 Alex。")

    def save_memory_file(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except: pass

    def load_memory_file(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except: pass
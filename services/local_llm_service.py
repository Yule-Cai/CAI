import os
import sys
from llama_cpp import Llama

from interfaces.llm_base import LLMBase


class LocalLLMService(LLMBase):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalLLMService, cls).__new__(cls)
            cls._instance.init_model()
        return cls._instance

    def init_model(self):
        # 1. 自动定位模型路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "models", "model.gguf")
        
        print(f"[Core] Loading model from: {model_path}")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ 模型文件未找到: {model_path}\n请把 GGUF 模型文件放入 models 文件夹并重命名为 model.gguf")

        # 2. 加载模型 (根据显存调整 n_gpu_layers)
        try:
            self.model = Llama(
                model_path=model_path,
                n_ctx=4096,        # 上下文长度，设大一点以支持长对话
                n_threads=4,       # CPU 线程数
                n_gpu_layers=-1,   # -1 表示尽可能把层加载到 GPU，如果没有显卡会自动忽略
                flash_attn=True,
                verbose=False      # 关闭啰嗦的底层日志
            )
            print("[Core] Model Ready.")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise e

    # 🟢 关键修复：确保这个方法名叫 chat_stream，并且逻辑正确
    def chat_stream(self, messages):
        """
        流式对话接口
        :param messages: [{"role": "user", "content": "..."}, ...]
        """
        try:
            stream = self.model.create_chat_completion(
                messages=messages,
                stream=True,       # 开启流式输出
                temperature=0.7,   # 创造力参数
                max_tokens=2000    # 最大生成长度
            )

            for chunk in stream:
                # 提取 delta 内容
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                        
        except Exception as e:
            print(f"[LLM Error] 生成中断: {e}")
            yield f"[Error: {e}]"

    def get_response(self, messages):
        return "".join(self.chat_stream(messages))
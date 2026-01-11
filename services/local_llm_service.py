import os
import sys
import json
import gc

# 1. 修复 DLL 路径
def fix_llama_dll_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        possible_paths = [
            os.path.join(base_path, "_internal", "llama_cpp"),
            os.path.join(base_path, "_internal", "llama_cpp", "lib"),
            os.path.join(base_path, "llama_cpp", "lib"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try: os.add_dll_directory(p)
                except: pass
fix_llama_dll_path()

from llama_cpp import Llama

class LocalLLMService:
    def __init__(self):
        # 🟢 2. 核心修复：智能寻找模型路径 (支持 _internal)
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            
            # 可能性A: 用户手动复制到了 EXE 旁边
            path_root = os.path.join(base_dir, "models", "model.gguf")
            # 可能性B: PyInstaller 自动打包进了 _internal
            path_internal = os.path.join(base_dir, "_internal", "models", "model.gguf")
            
            if os.path.exists(path_root):
                model_path = path_root
            elif os.path.exists(path_internal):
                model_path = path_internal
            else:
                # 两个都找不到，报错提示路径
                raise FileNotFoundError(
                    f"Model Missing!\nChecked:\n1. {path_root}\n2. {path_internal}"
                )
        else:
            # 开发环境
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            model_path = os.path.join(root_dir, "models", "model.gguf")

        print(f"[Core] Loading model from: {model_path}")
        
        try:
            self.CTX_LIMIT = 2048
            self.BATCH_SIZE = 1024 
            self.llm = Llama(
                model_path=model_path,
                n_gpu_layers=-1, 
                n_ctx=self.CTX_LIMIT,   
                n_batch=self.BATCH_SIZE, 
                verbose=False
            )
            print(f"[Core] Model Ready.")
        except Exception as e:
            print(f"[Core] Load Failed: {e}"); raise e

        self.client = self 
        self.chat = self
        self.completions = self

    def get_model_id(self): return "Embedded-Stream"

    def _count_tokens(self, text): return int(len(text) * 2.0)

    def _prune(self, messages, max_response_tokens=500):
        safe_input_limit = self.CTX_LIMIT - max_response_tokens - 100
        def get_total(msgs): return sum(self._count_tokens(m['content']) for m in msgs)
        temp_msgs = list(messages)
        while get_total(temp_msgs) > safe_input_limit and len(temp_msgs) > 2:
            temp_msgs.pop(1)
        return temp_msgs

    def create(self, model, messages, temperature=0.7, max_tokens=600, timeout=None, stream=False):
        try:
            self.llm.reset()
            gc.collect()
            safe_messages = self._prune(messages, max_response_tokens=max_tokens)
            output = self.llm.create_chat_completion(
                messages=safe_messages, temperature=temperature, max_tokens=max_tokens, stream=True 
            )
            return output 
        except Exception as e:
            print(f"[LLM Error] {e}")
            def empty_gen(): yield {"choices":[{"delta":{"content": " (Error) "}}]}
            return empty_gen()
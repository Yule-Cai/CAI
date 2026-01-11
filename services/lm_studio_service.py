import os
from openai import OpenAI

class LMStudioService:
    def __init__(self):
        # 默认连接本地 LM Studio
        self.base_url = "http://localhost:1234/v1"
        self.api_key = "lm-studio" # 本地服务通常不需要真实 Key
        
        try:
            self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            # 🟢 自动获取当前加载的模型 ID
            self.model_id = self._fetch_current_model()
            print(f"[LLM] Connected. Target Model: {self.model_id}")
        except Exception as e:
            print(f"[LLM] Connection Failed: {e}")
            self.model_id = "local-model" # 降级方案

    def _fetch_current_model(self):
        """ 向 LM Studio 询问当前加载了什么模型 """
        try:
            models = self.client.models.list()
            if models.data:
                # 返回第一个加载的模型 ID
                return models.data[0].id
        except:
            pass
        return "local-model"

    def get_model_id(self):
        return self.model_id
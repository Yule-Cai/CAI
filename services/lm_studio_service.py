import os
from openai import OpenAI

from interfaces.llm_base import LLMBase


class LMStudioService(LLMBase):
    """本地 LM Studio（OpenAI 兼容接口），Mac 主力后端。

    地址从 config.settings.LM_STUDIO_URL 读取，可用环境变量 LM_STUDIO_URL 覆盖。
    模型自动取 LM Studio 当前加载的第一个，需要先在 LM Studio 里 Load 模型并 Start Server。
    """

    def __init__(self, base_url=None, model=None):
        try:
            from config.settings import LM_STUDIO_URL, MODEL_NAME
        except ImportError:
            LM_STUDIO_URL = "http://localhost:1234/v1"
            MODEL_NAME = "local-model"
        self.base_url = base_url or os.getenv("LM_STUDIO_URL", LM_STUDIO_URL)
        self.api_key = "lm-studio"  # 本地服务不需要真实 Key
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        self.model_id = model or self._fetch_current_model()
        print(f"[LLM] LM Studio ready. Server: {self.base_url} Model: {self.model_id}")

    def _fetch_current_model(self):
        """优先用配置指定的模型（在 Server 列表里才有效），否则取第一个已加载的"""
        try:
            from config.settings import MODEL_NAME as preferred
        except ImportError:
            preferred = ""
        try:
            models = self.client.models.list()
            ids = [m.id for m in models.data] if models.data else []
            if preferred and preferred in ids:
                return preferred
            if ids:
                return ids[0]
        except Exception as e:
            print(f"[LLM] LM Studio 未响应 {self.base_url}：{e}")
        return "local-model"

    def get_model_id(self):
        return self.model_id

    def chat_stream(self, messages):
        try:
            stream = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=2000,
            )
            for chunk in stream:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            print(f"[LLM Error] LM Studio 调用失败: {e}")
            yield f"[LM Studio 出错：{e}，请确认 LM Studio 已启动 Server 并加载了模型]"

    def get_response(self, messages):
        return "".join(self.chat_stream(messages))

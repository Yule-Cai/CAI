from abc import ABC, abstractmethod

class LLMBase(ABC):
    """
    这是一个抽象基类（规则书）。
    所有接入 CAI 的大模型服务必须遵守这个规则。
    """
    
    @abstractmethod
    def get_response(self, messages: list) -> str:
        """
        输入对话历史 (messages)，返回 AI 的回复字符串。
        """
        pass
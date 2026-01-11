from abc import ABC, abstractmethod

class TTSBase(ABC):
    """
    语音合成服务的基类（规则书）。
    所有嘴巴都必须能“说话”。
    """
    @abstractmethod
    def speak(self, text: str):
        """
        输入文字，播放声音。
        """
        pass
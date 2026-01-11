# CAI 的全局配置

# LM Studio 的默认地址
LM_STUDIO_URL = "http://26.93.181.215:1234/v1"

# 你的模型名称 (在 LM Studio 加载后，这里填什么其实不影响，但保持清晰比较好)
MODEL_NAME = "gpt-oss-20b"

# CAI 的人设 (System Prompt)
# 以后可以在这里修改人设，不用改代码
SYSTEM_PROMPT = """
你叫 CAI。是一个由 Python 编写的高级人工智能助手。
你的性格冷静、逻辑严密，但也充满好奇心。
回答请尽量简练。
"""

# 调试模式 (True 会打印更多信息)
DEBUG = True
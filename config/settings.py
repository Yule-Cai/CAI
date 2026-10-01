# CAI 的全局配置
import os

# LLM 后端切换：local=本地llama（默认），cloud=opencode免费云模型，auto=有Key用云否则本地
# 用法：export CAI_LLM=cloud
LLM_PROVIDER = os.getenv("CAI_LLM", "local")

# opencode Zen 免费模型配置（Key 从环境变量 OPENCODE_API_KEY 读取，见 .env.example）
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "muse-spark-1.3-contributor-free")
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")

# LM Studio 的默认地址（Mac 本地默认 localhost，可用环境变量 LM_STUDIO_URL 覆盖）
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

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
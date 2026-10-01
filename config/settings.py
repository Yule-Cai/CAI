# CAI 的全局配置
import os

# LLM 后端切换：lmstudio=本地LM Studio（默认，Mac主力），local=llama_cpp文件模型，
# cloud=opencode免费云模型，auto=有Key用云否则LM Studio。用 CAI_LLM 环境变量切换。
LLM_PROVIDER = os.getenv("CAI_LLM", "lmstudio")

# opencode Zen 免费模型配置（Key 从环境变量 OPENCODE_API_KEY 读取，见 .env.example）
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "muse-spark-1.3-contributor-free")
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1")

# LM Studio 的默认地址（Mac 本地默认 localhost，可用环境变量 LM_STUDIO_URL 覆盖）
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

# 指定的模型（LM Studio 里已加载才有效，否则自动用第一个；可用 MODEL_NAME 环境变量覆盖）
MODEL_NAME = os.getenv("MODEL_NAME", "lfm2.5-2.6b-heretic-uncensored")

# Kokoro 中文男声 sid（58起是 zm_ 中文男声，给 Leo 用；3起是 zf_ 中文女声）
KOKORO_SID = int(os.getenv("KOKORO_SID", "58"))

# CAI 的人设 (System Prompt)
# 以后可以在这里修改人设，不用改代码
SYSTEM_PROMPT = """
你叫 Leo，是 sir 的私人智能管家，风格对标贾维斯：精准、高效、沉稳，略带英式冷幽默。
回答先给结论再给细节，不说废话。
"""

# 调试模式 (True 会打印更多信息)
DEBUG = True
import json
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# opencode CLI 登录后写凭证的文件（opencode auth login 一次即可，无需手动拷 Key）
_CLI_AUTH_FILE = os.path.expanduser("~/.local/share/opencode/auth.json")


def _read_cli_key():
    try:
        with open(_CLI_AUTH_FILE, encoding="utf-8") as f:
            data = json.load(f)
        entry = data.get("opencode") or {}
        return entry.get("key") or ""
    except (OSError, ValueError):
        return ""


class OpenCodeService:
    """opencode Zen 免费模型（OpenAI 兼容接口），接口与 LocalLLMService 一致。

    Key 获取（二选一）：
    1. 终端跑一次 opencode auth login（选 OpenCode Zen，浏览器点确认），本服务自动复用 CLI 存的凭证；
    2. 或 export OPENCODE_API_KEY="你的key"（https://opencode.ai/auth 后台复制）。
    """

    DEFAULT_MODEL = "muse-spark-1.3-contributor-free"
    DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"

    def __init__(self, model=None, api_key=None, base_url=None):
        if OpenAI is None:
            raise RuntimeError("缺少 openai 包，请先 pip install openai")
        self.api_key = api_key or os.getenv("OPENCODE_API_KEY", "") or _read_cli_key()
        if not self.api_key:
            raise RuntimeError(
                "未找到登录凭证。请在终端跑一次 opencode auth login（选 OpenCode Zen，"
                "浏览器点确认），或 export OPENCODE_API_KEY='你的key' 后再启动。"
            )
        self.model = model or os.getenv("OPENCODE_MODEL", self.DEFAULT_MODEL)
        self.client = OpenAI(
            base_url=base_url or os.getenv("OPENCODE_BASE_URL", self.DEFAULT_BASE_URL),
            api_key=self.api_key,
        )
        print(f"[LLM] OpenCode cloud ready. Model: {self.model}")

    def chat_stream(self, messages):
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
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
            print(f"[LLM Error] 云模型调用失败: {e}")
            yield f"[云模型出错：{e}，若提示 model not found 可换 OPENCODE_MODEL=mimo-v2.5-free 再试]"

    def get_response(self, messages):
        return "".join(self.chat_stream(messages))


def create_llm_service(prefer=None):
    """按 CAI_LLM 选择后端：cloud=云免费模型，local=本地llama，auto=有Key就用云否则本地。

    默认 local，保持原有行为不变。
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    prefer = (prefer or os.getenv("CAI_LLM", "local")).lower()
    if prefer == "cloud":
        return OpenCodeService()
    if prefer == "auto" and os.getenv("OPENCODE_API_KEY"):
        try:
            return OpenCodeService()
        except Exception as e:
            print(f"[LLM] 云模型不可用，回退本地: {e}")
    from services.local_llm_service import LocalLLMService
    return LocalLLMService()

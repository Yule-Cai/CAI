import PyInstaller.__main__
import os
import sys

# ================= 配置区域 =================
# 1. 获取当前脚本所在的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 定义绝对路径
MODEL_PATH = os.path.join(BASE_DIR, "models")
TTS_PATH = os.path.join(BASE_DIR, "tts_model")

# 3. 你的 llama_cpp 库路径 (保持之前查到的)
LLAMA_LIB_PATH = r"C:\Users\caiyule\AppData\Roaming\Python\Python313\site-packages\llama_cpp"

APP_NAME = "AI_Companion"
ENTRY_POINT = "ui_module.py"
# ===========================================

print(f"🔍 正在检查资源文件...")

# 🔴 1. 严防死守：打包前先检查文件在不在
if not os.path.exists(MODEL_PATH):
    print(f"❌ 严重错误：在 {MODEL_PATH} 没找到模型文件夹！")
    print("请把 models 文件夹放到和 build_exe.py 同一级目录！")
    sys.exit(1)

if not os.path.exists(TTS_PATH):
    print(f"❌ 严重错误：在 {TTS_PATH} 没找到语音文件夹！")
    print("请把 tts_model 文件夹放到和 build_exe.py 同一级目录！")
    sys.exit(1)

if not os.path.exists(LLAMA_LIB_PATH):
    print(f"❌ 严重错误：无法找到 llama_cpp 库: {LLAMA_LIB_PATH}")
    sys.exit(1)

print("✅ 所有资源已就绪，开始准备搬运...")

# 🔴 2. 构造数据指令 (源绝对路径;目标相对路径)
# 意思是：把 C:\...\models 复制到 exe内部的 models/ 文件夹下
datas_to_add = [
    f'{LLAMA_LIB_PATH};llama_cpp', 
    f'{MODEL_PATH};models',
    f'{TTS_PATH};tts_model'
]

# 转换参数
add_data_args = []
for item in datas_to_add:
    add_data_args.append(f'--add-data={item}')

print(f"🚀 开始打包 {APP_NAME}...")
print("☕ 这次因为要复制几个GB的模型，速度会比较慢，请耐心等待...")

args = [
    ENTRY_POINT,
    f'--name={APP_NAME}',
    '--onedir',          # 生成文件夹 (推荐)
    '--windowed',        # 无黑框
    '--clean',           # 清理缓存
    '--noconfirm',       # 覆盖不询问
    
    # 注入数据
    *add_data_args,
    
    # 强制收集依赖
    '--collect-all=llama_cpp',
    
    # 隐藏导入
    '--hidden-import=services',
    '--hidden-import=services.local_llm_service',
    '--hidden-import=services.sherpa_service',
    '--hidden-import=core.cai_brain',
    '--hidden-import=llama_cpp',
    '--hidden-import=sherpa_onnx',
    '--hidden-import=sounddevice',
]

try:
    PyInstaller.__main__.run(args)
    print("\n" + "="*50)
    print(f"🎉 打包大功告成！")
    print(f"📂 输出位置: {os.path.join(BASE_DIR, 'dist', APP_NAME)}")
    print("✅ 模型已自动集成，直接把整个文件夹发给别人就能用！")
    print("="*50)
except Exception as e:
    print(f"\n❌ 打包出错: {e}")
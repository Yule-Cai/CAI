import os
import sys
import numpy as np
import sounddevice as sd
import time

# 强制添加路径
sys.path.append(os.path.dirname(__file__))

print("=== 1. 声卡设备检测 ===")
try:
    devices = sd.query_devices()
    print(devices)
    default_device = sd.query_devices(kind='output')
    print(f"\n[当前默认输出设备]: {default_device['name']}")
    print(f"[支持的采样率]: {default_device['default_samplerate']}")
except Exception as e:
    print(f"❌ 声卡驱动异常: {e}")
    sys.exit(1)

print("\n=== 2. 模型生成测试 ===")
try:
    from services.sherpa_service import SherpaTTSService
    tts_service = SherpaTTSService()
    
    if not tts_service.tts:
        print("❌ 模型未加载，无法继续测试。")
        sys.exit(1)
        
    text = "测试一二三，听到请回答。"
    print(f"正在生成: '{text}' ...")
    
    # 调用我们在 service 里新写的 generate_raw_audio
    start = time.time()
    samples, rate = tts_service.generate_raw_audio(text)
    end = time.time()
    
    print(f"✅ 生成耗时: {end - start:.3f}s")
    print(f"✅ 模型采样率: {rate} Hz")
    
    if samples is None or len(samples) == 0:
        print("❌ 致命错误：生成的音频数据为空！")
        sys.exit(1)
        
    # 检查数据类型
    print(f"✅ 数据类型: {type(samples)}")
    if isinstance(samples, list):
        print(f"   (检测到 list，自动转换为 numpy)")
        samples = np.array(samples, dtype=np.float32)
    
    print(f"✅ 数据形状: {samples.shape}")
    print(f"✅ 最大振幅: {np.max(np.abs(samples)):.4f}")
    
    if np.max(np.abs(samples)) < 0.0001:
        print("❌ 警告：生成的是全是 0 的静音！模型可能不兼容或损坏。")
    else:
        print("✅ 数据正常，包含有效波形。")

except Exception as e:
    print(f"❌ 生成过程报错: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== 3. 强制播放测试 ===")
try:
    print(f"正在以 {rate} Hz 播放...")
    sd.play(samples, rate)
    sd.wait() # 阻塞直到播完
    print("✅ 播放指令执行完毕。")
    print("👉 如果你看到了这行字但没听到声音，请检查电脑音量或默认输出设备。")
except Exception as e:
    print(f"❌ 播放失败: {e}")
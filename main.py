from services.opencode_service import create_llm_service
from services.sherpa_service import SherpaTTSService 
from services.sherpa_asr_service import SherpaASRService 
from core.cai_brain import CAIBrain
import sys
import os
if os.name == "nt":
    try:
        import keyboard  # Windows 全局按键监听；Mac 无 keyboard 时自动降级纯打字模式
    except ImportError:
        keyboard = None
else:
    keyboard = None
import time

def main():
    print("========================================")
    print("   CAI: 混合交互版 (Hybrid Mode)   ")
    print("========================================")
    
    # 1. 初始化
    try:
        llm_service = create_llm_service()
        tts_service = SherpaTTSService() 
        asr_service = SherpaASRService() 
        cai = CAIBrain(llm_service)
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        sys.exit(1)
    
    print("\n✅ 系统就绪！操作说明：")
    print("🎤 [空格键] : 按一下松开 -> 开始语音识别 (说完自动识别)")
    print("⌨️ [ T 键 ] : 按一下 -> 进入打字模式")
    print("❌ [ Esc ] : 退出程序")
    print("----------------------------------------")
    
    tts_service.speak("系统就绪，你可以按空格键跟我说话，或者按 T 键打字。")

    if keyboard is None:
        print("\n⚠️ keyboard 库不可用，已进入纯打字模式（回车发送，输入 退出 离开）。")
        while True:
            try:
                user_text = input("你: ").strip()
                if user_text:
                    process_response(user_text, cai, tts_service)
            except (KeyboardInterrupt, EOFError):
                break
        return

    while True:
        try:
            # 监听按键 (不会阻塞 CPU)
            # 0.1 秒检测一次，防止 CPU 占用过高
            time.sleep(0.05) 
            
            # --- 模式 A: 语音 (按下空格) ---
            if keyboard.is_pressed('space'):
                # 防止按一下触发多次，先等待按键释放（可选，这里直接进监听）
                while keyboard.is_pressed('space'): pass 
                
                print("\n\n[🎤] 语音模式启动...")
                # 调用耳朵去听 (这时会阻塞，直到你说完)
                user_text = asr_service.listen()
                
                if user_text:
                    process_response(user_text, cai, tts_service)
                
                print("\n--- 等待指令 (空格:语音 | T:打字) ---")

            # --- 模式 B: 打字 (按下 T) ---
            elif keyboard.is_pressed('t'):
                while keyboard.is_pressed('t'): pass 
                
                print("\n\n[⌨️] 请输入文字 (回车发送):")
                # 这里使用 input，会暂停程序等待你打字
                user_text = input("你: ")
                
                if user_text.strip():
                    process_response(user_text, cai, tts_service)
                
                print("\n--- 等待指令 (空格:语音 | T:打字) ---")

            # --- 退出 ---
            elif keyboard.is_pressed('esc'):
                print("\n退出系统。")
                sys.exit(0)
                
        except KeyboardInterrupt:
            break

def process_response(user_input, cai_brain, tts):
    """
    统一处理：思考 -> 回答 -> 朗读
    """
    if not user_input: return
    
    # 打印用户的话
    print(f"你: {user_input}")
    
    if "退出" in user_input:
        print("CAI: 再见。")
        tts.speak("再见。")
        sys.exit(0)

    # 思考
    print("(思考中...)")
    reply = "".join(cai_brain.chat_stream(user_input))
    print(f"CAI: {reply}")
    
    # 朗读
    tts.speak(reply)

if __name__ == "__main__":
    main()
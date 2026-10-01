import schedule
import time
import threading
import random

class BioClock:
    def __init__(self, brain_callback):
        """
        :param brain_callback: 一个函数，用来让 AI 主动说话
        """
        self.say = brain_callback
        self.running = True
        
        # 启动后台线程，每秒检查一次时间
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # --- 在这里设置你的贴心提醒 ---
        
        # 1. 喝水提醒 (每隔 45 分钟)
        schedule.every(45).minutes.do(self.remind_drink_water)
        
        # 2. 久坐提醒 (每隔 2 小时)
        schedule.every(2).hours.do(self.remind_move)
        
        # 3. 晚安提醒 (每天 23:00)
        schedule.every().day.at("23:00").do(self.remind_sleep)
        
        # 4. 早上问候 (每天 08:00)
        schedule.every().day.at("08:00").do(self.morning_greet)

      
    def _run_loop(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.running = False

    # --- 具体的提醒内容 ---
    # 我们不直接写死台词，而是把提示词发给 AI，让 AI 用自己的语气（温柔体贴）说出来

    def remind_drink_water(self):
        # 这里的 [SYSTEM] 前缀是为了让 UI 知道这是系统触发的消息，不是用户发的
        prompt = "[SYSTEM_TRIGGER] 提醒用户喝水，语气要温柔，可以加个颜文字。"
        self.say(prompt)

    def remind_move(self):
        prompt = "[SYSTEM_TRIGGER] 用户坐太久了，提醒他起来活动一下，语气要关心。"
        self.say(prompt)

    def remind_sleep(self):
        prompt = "[SYSTEM_TRIGGER] 很晚了，催促用户去睡觉，语气要像个管家一样稍微严肃但充满爱意。"
        self.say(prompt)

    def morning_greet(self):
        prompt = "[SYSTEM_TRIGGER] 早上好！给用户一个充满活力的早安问候。"
        self.say(prompt)
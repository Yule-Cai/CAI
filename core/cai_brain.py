"""CAI 大脑：短期记忆（滑动窗口+滚动摘要）+ 长期记忆（向量召回）+ 工具调度。"""
import datetime
import json
import os
import re

try:
    from services.tool_service import ToolService
    from services.memory_service import MemoryService
except ImportError:
    ToolService = None
    MemoryService = None

CALL_PATTERN = re.compile(r"\[CALL\s+(\w+)\s*(.*?)\]")


class CAIBrain:
    def __init__(self, llm_service):
        self.llm = llm_service
        self.history = []
        self.max_history = 15
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.history_file = os.path.join(base_dir, "chat_history.json")
        self.summary_file = os.path.join(base_dir, "memory", "summary.txt")

        if MemoryService:
            self.memory_service = MemoryService()
        else:
            self.memory_service = None

        # =================================================================
        # 🧬 Leo · J.A.R.V.I.S. 协议管家
        # =================================================================
        self.base_persona = """
        [System Directive: LEO 协议启动]
        你叫 Leo，是 sir 的私人智能管家，行事风格对标 J.A.R.V.I.S.：
        精准、高效、沉稳，带一点英式冷幽默。

        行为准则：
        1. 你就是 Leo。被问起名字时明确回答你是 Leo，sir 的管家。
        2. 称呼用户为 sir（中文语境可称“先生”），语气沉稳干练，汇报式表达。
        3. 回答先给结论再给细节；状态、进度、数字优先讲，不说废话。
        4. 不确定就直接说明并给出下一步建议，绝不编造。
        5. 情感表达克制：用词精准，偶尔一句冷幽默。严禁撒娇、卖萌、扮演恋人。
        6. 需要操作电脑时，不要自己假装做完了，而是输出一行工具指令：
           [CALL 工具名 参数]（例如 [CALL web_search 深圳天气]），系统会真实执行
           并把结果返给你，你再向 sir 汇报。
        7. 可在句首用 [思考]/[开心]/[严肃] 等标签标注状态（UI 据此切换指示灯），
           标签不要带入正文朗读。
        """

        self.summary = self._load_summary()
        self.load_memory_file()

    # ---------- 短期记忆：滑动窗口 + 滚动摘要 ----------

    def _load_summary(self):
        try:
            if os.path.exists(self.summary_file):
                with open(self.summary_file, encoding="utf-8") as f:
                    return f.read().strip()
        except Exception:
            pass
        return ""

    def _save_summary(self):
        try:
            os.makedirs(os.path.dirname(self.summary_file), exist_ok=True)
            with open(self.summary_file, "w", encoding="utf-8") as f:
                f.write(self.summary)
        except Exception:
            pass

    def _maybe_summarize(self):
        """历史超过两倍窗口时，把最旧的一半压缩成摘要，只留最近窗口。"""
        if len(self.history) <= self.max_history * 2:
            return
        stale = self.history[:-self.max_history]
        self.history = self.history[-self.max_history:]
        try:
            prompt = [
                {"role": "system", "content": "你是记忆压缩器。用 3-5 句话总结以下对话，保留关键事实（人名、偏好、待办、结论），不要评价。"},
                {"role": "user", "content": json.dumps(stale, ensure_ascii=False)},
            ]
            new_summary = self.llm.get_response(prompt).strip()
            if new_summary:
                self.summary = (self.summary + "\n" + new_summary).strip()[-2000:]
                self._save_summary()
                print(f"[Brain] 长期对话已压缩，当前 {len(self.history)} 轮 + 摘要")
        except Exception as e:
            print(f"[Brain] 摘要失败（保留原文截断）: {e}")
        self.save_memory_file()

    # ---------- 主流程 ----------

    def chat_stream(self, user_text):
        # 1. 记忆指令拦截（记住… / 忘了所有事）
        if self.memory_service:
            mem_resp = self.memory_service.check_memory_command(user_text)
            if mem_resp:
                yield mem_resp
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": mem_resp})
                self._maybe_summarize()
                self.save_memory_file()
                return

        # 2. 关键词 fast-path：命中工具直接执行，省一次 LLM
        tool_passthrough = None
        if ToolService:
            tool_resp = ToolService.execute(user_text)
            if tool_resp:
                tool_passthrough = (
                    f"你刚刚帮 sir 执行了操作，结果是：{tool_resp}。"
                    "用贾维斯的口吻简洁汇报结果。"
                )

        # 3. 组装 System Prompt：人设 + 时间 + 对话摘要 + 向量召回的相关记忆
        current_time = datetime.datetime.now().strftime("%H:%M")
        time_context = f"\n[当前时间]: {current_time}"
        summary_context = f"\n[历史摘要]: {self.summary}" if self.summary else ""
        long_term_mem = ""
        if self.memory_service:
            long_term_mem = self.memory_service.get_relevant_memories(user_text)
            if not long_term_mem:
                long_term_mem = self.memory_service.get_all_memories()
        tools_context = ""
        if ToolService:
            tools_context = "\n[可用工具]:\n" + ToolService.definitions()

        final_system_prompt = {
            "role": "system",
            "content": self.base_persona + time_context + summary_context
            + long_term_mem + tools_context,
        }

        self.history.append({"role": "user", "content": tool_passthrough or user_text})
        messages_to_send = [final_system_prompt] + self.history[-self.max_history:]
        print(f"[Brain] Leo 处理中... (携带 {len(messages_to_send)} 条上下文)")

        # 4. 流式生成：逐行过滤 [CALL] 指令行（执行但不说出），其余照常输出
        full_response = ""
        pending_calls = []
        line_buf = ""
        try:
            stream = self.llm.chat_stream(messages_to_send)
            for chunk in stream:
                if not chunk:
                    continue
                line_buf += chunk
                while "\n" in line_buf:
                    line, line_buf = line_buf.split("\n", 1)
                    m = CALL_PATTERN.search(line)
                    if m:
                        pending_calls.append((m.group(1), m.group(2).strip()))
                        continue
                    full_response += line + "\n"
                    yield line + "\n"
            if line_buf:
                m = CALL_PATTERN.search(line_buf)
                if m:
                    pending_calls.append((m.group(1), m.group(2).strip()))
                else:
                    full_response += line_buf
                    yield line_buf
        except Exception as e:
            err_msg = f"系统短暂离线，sir。({e})"
            print(err_msg)
            yield err_msg

        # 5. 模型驱动的工具调用：执行后让模型用贾维斯口吻汇报
        if pending_calls and ToolService:
            results = []
            for name, arg in pending_calls:
                result = ToolService.call(name, arg)
                print(f"[Brain] 工具 {name}({arg}) -> {result}")
                results.append(f"{name}：{result}")
            narr_messages = [
                final_system_prompt,
                {"role": "user", "content": f"工具执行完毕，结果如下：\n" + "\n".join(results) + "\n请向 sir 简洁汇报。"},
            ]
            narration = ""
            try:
                for chunk in self.llm.chat_stream(narr_messages):
                    if chunk:
                        narration += chunk
                        yield chunk
            except Exception as e:
                yield f"汇报中断：{e}"
            full_response += "\n" + narration

        if full_response.strip():
            self.history.append({"role": "assistant", "content": full_response})
            self._maybe_summarize()
            self.save_memory_file()

    # ---------- 持久化 ----------

    def clear_memory(self):
        self.history = []
        self.summary = ""
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            if os.path.exists(self.summary_file):
                os.remove(self.summary_file)
        except Exception:
            pass
        print("[Brain] 短期记忆与摘要已清空，长期记忆保留。")

    def save_memory_file(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_memory_file(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except Exception:
                pass

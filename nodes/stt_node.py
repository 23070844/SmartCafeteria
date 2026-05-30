#!/usr/bin/env python3
"""
Node 1: Speech-to-Text (STT)
============================================================
功能：
  - 用真实麦克风收音
  - 转化成文字
  - 发布到 /speech_text topic
  - 同时检测关键词 "Done"，发布 /robot_state = COUNTING

发布 Topics:
  /speech_text   (std_msgs/String)  — 识别到的完整文字
  /robot_state   (std_msgs/String)  — IDLE / LISTENING / COUNTING

订阅 Topics:
  无（纯输入节点）
"""

import rospy
import speech_recognition as sr
from std_msgs.msg import String


# ── Robot State 常量 ────────────────────────────────────────────────────────
STATE_IDLE      = "IDLE"
STATE_LISTENING = "LISTENING"
STATE_COUNTING  = "COUNTING"


class STTNode:
    def __init__(self):
        rospy.init_node("stt_node", anonymous=True)

        # Publishers
        self.speech_pub = rospy.Publisher("/speech_text", String, queue_size=10)
        self.state_pub  = rospy.Publisher("/robot_state", String, queue_size=10)

        # Speech recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold        = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold          = 0.8   # 0.8s 静音 = 一句话结束

        rospy.loginfo("✅ STT Node ready. Listening via microphone...")
        self.publish_state(STATE_IDLE)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def publish_state(self, state: str):
        msg = String(); msg.data = state
        self.state_pub.publish(msg)
        rospy.loginfo(f"[STATE] {state}")

    def publish_text(self, text: str):
        msg = String(); msg.data = text
        self.speech_pub.publish(msg)
        rospy.loginfo(f"[STT OUTPUT] '{text}'")

    # ── Core: one listening cycle ────────────────────────────────────────────

    def listen_once(self):
        """
        阻塞式：等待一句话，返回识别文字字符串，失败返回 None。
        """
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                self.publish_state(STATE_LISTENING)
                rospy.loginfo("[MIC] 🎙️  Listening...")

                audio = self.recognizer.listen(
                    source,
                    timeout=15,           # 最多等 15s 才有声音
                    phrase_time_limit=8   # 一句话最长 8s
                )

            text = self.recognizer.recognize_google(audio, language="en-US")
            return text.strip()

        except sr.WaitTimeoutError:
            rospy.logwarn("[STT] Timeout — no speech detected.")
            return None
        except sr.UnknownValueError:
            rospy.logwarn("[STT] Could not understand audio.")
            return None
        except sr.RequestError as e:
            rospy.logerr(f"[STT] Google API error: {e}")
            return None

    # ── Keyword handler ──────────────────────────────────────────────────────

    def handle_keywords(self, text: str):
        t = text.lower()

        if any(kw in t for kw in ["done", "finish", "finished"]):
            rospy.loginfo("🔔 Keyword 'Done' detected → triggering COUNTING")
            self.publish_state(STATE_COUNTING)

        elif any(kw in t for kw in ["cancel", "reset", "restart"]):
            rospy.loginfo("🔄 Reset keyword detected")
            self.publish_state(STATE_IDLE)

    # ── Main loop ────────────────────────────────────────────────────────────

    def run(self):
        rospy.loginfo("🎙️  STT Node running. Speak into the microphone.")

        while not rospy.is_shutdown():
            text = self.listen_once()

            if text:
                self.publish_text(text)
                self.handle_keywords(text)
            else:
                self.publish_state(STATE_IDLE)


if __name__ == "__main__":
    try:
        STTNode().run()
    except rospy.ROSInterruptException:
        rospy.loginfo("STT Node shut down.")

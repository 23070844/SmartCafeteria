#!/usr/bin/env python3
"""
Node 2: Text-to-Speech (TTS)
============================================================
功能：
  - 订阅 /tts_say topic
  - 收到文字就朗读出来（机器人说话）
  - 朗读时发布 /robot_state = SPEAKING
  - 朗读完发布 /robot_state = IDLE

订阅 Topics:
  /tts_say       (std_msgs/String)  — 要朗读的文字

发布 Topics:
  /robot_state   (std_msgs/String)  — SPEAKING / IDLE

使用方法（命令行测试）:
  rostopic pub /tts_say std_msgs/String "Processing payment, total is 5 ringgit"
"""

import rospy
import pyttsx3
import threading
from std_msgs.msg import String


STATE_IDLE     = "IDLE"
STATE_SPEAKING = "SPEAKING"


class TTSNode:
    def __init__(self):
        rospy.init_node("tts_node", anonymous=True)

        # Publisher
        self.state_pub = rospy.Publisher("/robot_state", String, queue_size=10)

        # Subscriber — 其他节点发文字到这里，机器人就开口说
        rospy.Subscriber("/tts_say", String, self.tts_callback)

        # TTS engine
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 155)    # 语速 (words per minute)
        self.engine.setProperty("volume", 1.0)  # 音量 0.0 ~ 1.0

        # 选择声音（可选）
        voices = self.engine.getProperty("voices")
        if voices:
            # 优先选英语女声，找不到就用默认
            for v in voices:
                if "english" in v.name.lower() or "en" in v.id.lower():
                    self.engine.setProperty("voice", v.id)
                    break

        # 防止多线程同时说话
        self.speak_lock = threading.Lock()

        rospy.loginfo("✅ TTS Node ready. Publish text to /tts_say to make the robot speak.")
        self.publish_state(STATE_IDLE)

        # 开机提示音
        self._speak_now("Text to speech system ready.")

    # ── Helpers ─────────────────────────────────────────────────────────────

    def publish_state(self, state: str):
        msg = String(); msg.data = state
        self.state_pub.publish(msg)
        rospy.loginfo(f"[STATE] {state}")

    def _speak_now(self, text: str):
        """实际调用 TTS 引擎（线程安全）。"""
        with self.speak_lock:
            rospy.loginfo(f"[TTS SPEAKING] 🔊 '{text}'")
            self.publish_state(STATE_SPEAKING)

            self.engine.say(text)
            self.engine.runAndWait()

            self.publish_state(STATE_IDLE)

    # ── Subscriber callback ──────────────────────────────────────────────────

    def tts_callback(self, msg: String):
        """
        收到 /tts_say 消息 → 在独立线程里朗读，不阻塞 ROS spin。
        """
        text = msg.data.strip()
        if not text:
            return

        # 用独立线程朗读，避免阻塞 ROS callbacks
        t = threading.Thread(target=self._speak_now, args=(text,), daemon=True)
        t.start()

    # ── Run ──────────────────────────────────────────────────────────────────

    def run(self):
        rospy.loginfo("🔊 TTS Node running. Waiting for /tts_say messages...")
        rospy.spin()  # TTS 节点是纯回调驱动，spin 就够了


if __name__ == "__main__":
    try:
        TTSNode().run()
    except rospy.ROSInterruptException:
        rospy.loginfo("TTS Node shut down.")

#!/usr/bin/env python3
"""
Task 2 - Text-to-Speech Node for Smart Cafeteria

Main input topic:
- /smart_cafeteria/kiosk_response

The node speaks the received text using pyttsx3 when audio output is available.
If audio output is unavailable, the ROS topic test still succeeds through log output.
"""

import threading
import rospy
from std_msgs.msg import String

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


KIOSK_RESPONSE_TOPIC = "/smart_cafeteria/kiosk_response"
TTS_STATUS_TOPIC = "/smart_cafeteria/tts_status"


class TTSNode:
    def __init__(self):
        rospy.init_node("tts_node", anonymous=False)

        self.status_pub = rospy.Publisher(TTS_STATUS_TOPIC, String, queue_size=10)

        rospy.Subscriber(
            KIOSK_RESPONSE_TOPIC,
            String,
            self.tts_callback,
            queue_size=10
        )

        self.lock = threading.Lock()
        self.engine = None

        rospy.loginfo("TTS Node started.")
        rospy.loginfo("Subscribed to: %s", KIOSK_RESPONSE_TOPIC)

        if pyttsx3 is None:
            rospy.logwarn("pyttsx3 is not installed. Run: pip3 install pyttsx3")
            self.publish_status("TTS_LIBRARY_MISSING")
        else:
            self.init_engine()

    def publish_status(self, status):
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)
        rospy.loginfo("[TTS STATUS] %s", status)

    def init_engine(self):
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", rospy.get_param("~speech_rate", 155))
            self.engine.setProperty("volume", rospy.get_param("~volume", 1.0))

            voices = self.engine.getProperty("voices")
            if voices:
                for voice in voices:
                    voice_name = getattr(voice, "name", "").lower()
                    voice_id = getattr(voice, "id", "").lower()
                    if "english" in voice_name or "en" in voice_id:
                        self.engine.setProperty("voice", voice.id)
                        break

            self.publish_status("READY")
            rospy.loginfo("TTS engine initialized successfully.")
        except Exception as e:
            self.engine = None
            self.publish_status("TTS_ENGINE_ERROR")
            rospy.logwarn("Could not initialize TTS engine: %s", str(e))
            rospy.logwarn("ROS topic subscription can still be tested by checking log output.")

    def speak(self, text):
        text = text.strip()
        if not text:
            return

        with self.lock:
            rospy.loginfo("Received kiosk response: %s", text)

            if self.engine is None:
                rospy.logwarn("TTS engine is unavailable. Message received but not spoken.")
                self.publish_status("MESSAGE_RECEIVED_NO_AUDIO")
                return

            try:
                self.publish_status("SPEAKING")
                rospy.loginfo("Speaking: %s", text)
                self.engine.say(text)
                self.engine.runAndWait()
                self.publish_status("IDLE")
            except Exception as e:
                self.publish_status("SPEAK_ERROR")
                rospy.logerr("TTS speaking error: %s", str(e))

    def tts_callback(self, msg):
        text = msg.data.strip()
        if not text:
            return

        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()

    def run(self):
        rospy.loginfo("TTS Node running. Waiting for kiosk responses...")
        rospy.spin()


if __name__ == "__main__":
    try:
        TTSNode().run()
    except rospy.ROSInterruptException:
        pass

#!/usr/bin/env python3
"""
Text-to-Speech Node for Smart Cafeteria.

Function:
- Subscribe to /tts_message.
- Speak the text through the system speaker.
- Publish /tts_status for debugging.

ROS Topics:
- Subscribe: /tts_message       std_msgs/String
- Publish:   /tts_status        std_msgs/String
"""

import threading
import rospy
from std_msgs.msg import String

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class TextToSpeechNode:
    def __init__(self):
        rospy.init_node("tts_node")

        self.status_pub = rospy.Publisher("/tts_status", String, queue_size=10)
        rospy.Subscriber("/tts_message", String, self.tts_callback)

        if pyttsx3 is None:
            rospy.logerr("pyttsx3 is not installed. Run: pip3 install -r requirements.txt")
            raise RuntimeError("Missing pyttsx3 package")

        self.engine = pyttsx3.init()

        rate = rospy.get_param("~speech_rate", 160)
        volume = rospy.get_param("~volume", 1.0)

        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

        self.lock = threading.Lock()

        rospy.loginfo("TTS node started. rate=%s volume=%s", rate, volume)

    def tts_callback(self, msg):
        text = msg.data.strip()
        if not text:
            return

        rospy.loginfo("Speaking: %s", text)
        self.status_pub.publish("SPEAKING")

        with self.lock:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                self.status_pub.publish("DONE")
            except Exception as exc:
                self.status_pub.publish("ERROR")
                rospy.logerr("TTS error: %s", exc)


if __name__ == "__main__":
    try:
        TextToSpeechNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

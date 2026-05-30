#!/usr/bin/env python3
"""
Task 2 - Text-to-Speech Node
Subscribe to /smart_cafeteria/kiosk_response and speak the received text.
Place this file in the existing ROS package scripts/ folder.
"""

import rospy
from std_msgs.msg import String

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class TTSNode:
    def __init__(self):
        rospy.init_node("tts_node", anonymous=False)

        self.topic = "/smart_cafeteria/kiosk_response"

        if pyttsx3 is None:
            rospy.logerr("pyttsx3 is not installed. Run: pip3 install pyttsx3")
            raise RuntimeError("Missing pyttsx3")

        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rospy.get_param("~speech_rate", 160))
        self.engine.setProperty("volume", rospy.get_param("~volume", 1.0))

        rospy.Subscriber(self.topic, String, self.callback, queue_size=10)

        rospy.loginfo("TTS node started.")
        rospy.loginfo("Subscribed to %s", self.topic)

    def callback(self, msg):
        text = msg.data.strip()
        if not text:
            return

        rospy.loginfo("Speaking kiosk response: %s", text)

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            rospy.logerr("TTS error: %s", e)


if __name__ == "__main__":
    try:
        TTSNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

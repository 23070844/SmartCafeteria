#!/usr/bin/env python3
"""
Task 2 - Speech-to-Text Node
Publish recognized speech to /smart_cafeteria/user_speech.
Place this file in the existing ROS package scripts/ folder.
"""

import rospy
from std_msgs.msg import String

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class STTNode:
    def __init__(self):
        rospy.init_node("stt_node", anonymous=False)

        self.pub = rospy.Publisher(
            "/smart_cafeteria/user_speech",
            String,
            queue_size=10
        )

        self.language = rospy.get_param("~language", "en-US")
        self.listen_timeout = rospy.get_param("~listen_timeout", 5)
        self.phrase_time_limit = rospy.get_param("~phrase_time_limit", 4)
        self.keyboard_fallback = rospy.get_param("~keyboard_fallback", True)

        if sr is None:
            rospy.logerr("SpeechRecognition is not installed. Run: pip3 install SpeechRecognition")
            if self.keyboard_fallback:
                self.run_keyboard_mode()
                return
            raise RuntimeError("Missing SpeechRecognition")

        self.recognizer = sr.Recognizer()

        try:
            self.microphone = sr.Microphone()
            rospy.loginfo("STT node started with microphone.")
        except Exception as e:
            rospy.logerr("Microphone/PyAudio error: %s", e)
            rospy.logerr("Try: sudo apt install portaudio19-dev python3-pyaudio")
            if self.keyboard_fallback:
                self.run_keyboard_mode()
                return
            raise

        self.run_microphone_mode()

    def publish_text(self, text):
        text = text.strip()
        if text:
            msg = String()
            msg.data = text
            self.pub.publish(msg)
            rospy.loginfo("Published /smart_cafeteria/user_speech: %s", text)

    def run_keyboard_mode(self):
        rospy.logwarn("Using keyboard fallback mode.")
        while not rospy.is_shutdown():
            try:
                text = input("user_speech> ")
            except (EOFError, KeyboardInterrupt):
                break
            self.publish_text(text)

    def run_microphone_mode(self):
        while not rospy.is_shutdown():
            try:
                with self.microphone as source:
                    rospy.loginfo("Listening...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.listen_timeout,
                        phrase_time_limit=self.phrase_time_limit
                    )

                text = self.recognizer.recognize_google(audio, language=self.language)
                self.publish_text(text)

            except sr.WaitTimeoutError:
                rospy.loginfo("No speech detected.")
            except sr.UnknownValueError:
                rospy.logwarn("Could not understand audio.")
            except sr.RequestError as e:
                rospy.logerr("Speech recognition service error: %s", e)
            except Exception as e:
                rospy.logerr("STT error: %s", e)


if __name__ == "__main__":
    try:
        STTNode()
    except rospy.ROSInterruptException:
        pass

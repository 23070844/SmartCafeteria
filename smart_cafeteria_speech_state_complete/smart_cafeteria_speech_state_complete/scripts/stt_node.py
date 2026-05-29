#!/usr/bin/env python3
"""
Speech-to-Text Node for Smart Cafeteria.

Function:
- Listen to the microphone.
- Convert speech to text.
- Publish the recognized command to /voice_command.
- The state manager node will decide whether to trigger YOLO detection.

ROS Topics:
- Publish: /voice_command      std_msgs/String
- Publish: /stt_status         std_msgs/String
"""

import rospy
from std_msgs.msg import String

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class SpeechToTextNode:
    def __init__(self):
        rospy.init_node("stt_node")

        self.language = rospy.get_param("~language", rospy.get_param("/language", "en-US"))
        self.listen_timeout = float(rospy.get_param("~listen_timeout", rospy.get_param("/listen_timeout", 5)))
        self.phrase_time_limit = float(rospy.get_param("~phrase_time_limit", rospy.get_param("/phrase_time_limit", 4)))
        self.ambient_adjust_duration = float(
            rospy.get_param("~ambient_adjust_duration", rospy.get_param("/ambient_adjust_duration", 0.6))
        )

        self.voice_pub = rospy.Publisher("/voice_command", String, queue_size=10)
        self.status_pub = rospy.Publisher("/stt_status", String, queue_size=10)

        if sr is None:
            rospy.logerr("speech_recognition is not installed. Run: pip3 install -r requirements.txt")
            raise RuntimeError("Missing speech_recognition package")

        self.recognizer = sr.Recognizer()

        try:
            self.microphone = sr.Microphone()
        except Exception as exc:
            rospy.logerr("Cannot access microphone: %s", exc)
            rospy.logerr("If PyAudio is missing, try: sudo apt install portaudio19-dev python3-pyaudio")
            raise

        rospy.loginfo("STT node started. Language=%s", self.language)

    def run(self):
        while not rospy.is_shutdown():
            try:
                with self.microphone as source:
                    self.status_pub.publish("LISTENING")
                    rospy.loginfo("Listening for voice command...")
                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=self.ambient_adjust_duration
                    )
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.listen_timeout,
                        phrase_time_limit=self.phrase_time_limit
                    )

                self.status_pub.publish("RECOGNIZING")
                text = self.recognizer.recognize_google(audio, language=self.language)
                text = text.strip().lower()

                if text:
                    rospy.loginfo("Recognized voice command: %s", text)
                    self.voice_pub.publish(text)

            except sr.WaitTimeoutError:
                self.status_pub.publish("TIMEOUT")
                rospy.loginfo("No speech detected within timeout.")
            except sr.UnknownValueError:
                self.status_pub.publish("UNKNOWN_SPEECH")
                rospy.logwarn("Could not understand the audio.")
            except sr.RequestError as exc:
                self.status_pub.publish("RECOGNITION_SERVICE_ERROR")
                rospy.logerr("Google speech recognition service error: %s", exc)
                rospy.sleep(2.0)
            except Exception as exc:
                self.status_pub.publish("ERROR")
                rospy.logerr("Unexpected STT error: %s", exc)
                rospy.sleep(1.0)


if __name__ == "__main__":
    try:
        SpeechToTextNode().run()
    except rospy.ROSInterruptException:
        pass

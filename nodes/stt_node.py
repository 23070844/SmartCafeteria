#!/usr/bin/env python3
"""
Task 2 - Speech-to-Text Node for Smart Cafeteria

Real microphone mode:
- Uses SpeechRecognition + PyAudio when available.

Fallback mode:
- Uses keyboard input when SpeechRecognition/PyAudio/microphone is unavailable.

Main output topic:
- /smart_cafeteria/user_speech
"""

import rospy
from std_msgs.msg import String

try:
    import speech_recognition as sr
    # Suppress ALSA warnings/errors on Linux systems
    try:
        from ctypes import CFUNCTYPE, c_char_p, c_int, cdll

        ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        def py_error_handler(filename, line, function, err, fmt):
            pass
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

        asound = cdll.LoadLibrary("libasound.so.2")
        asound.snd_lib_error_set_handler(c_error_handler)
    except Exception:
        pass
except ImportError:
    sr = None


USER_SPEECH_TOPIC = "/smart_cafeteria/user_speech"
STT_STATUS_TOPIC = "/smart_cafeteria/stt_status"


class STTNode:
    def __init__(self):
        rospy.init_node("stt_node", anonymous=False)

        self.user_speech_pub = rospy.Publisher(USER_SPEECH_TOPIC, String, queue_size=10)
        self.status_pub = rospy.Publisher(STT_STATUS_TOPIC, String, queue_size=10)

        self.language = rospy.get_param("~language", "en-US")
        self.listen_timeout = rospy.get_param("~listen_timeout", 10)
        self.phrase_time_limit = rospy.get_param("~phrase_time_limit", 6)
        self.keyboard_fallback = rospy.get_param("~keyboard_fallback", True)

        rospy.loginfo("STT Node started.")
        rospy.loginfo("Publishing recognized speech to: %s", USER_SPEECH_TOPIC)

        if sr is None:
            rospy.logwarn("SpeechRecognition is not installed. Run: pip3 install SpeechRecognition")
            self.publish_status("FALLBACK_KEYBOARD")
            self.run_keyboard_mode()
            return

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

        try:
            self.microphone = sr.Microphone()
            rospy.loginfo("Microphone detected. Running real microphone STT mode.")
            self.publish_status("MICROPHONE_MODE")
            self.run_microphone_mode()
        except Exception as e:
            rospy.logwarn("Cannot access microphone or PyAudio: %s", str(e))
            if self.keyboard_fallback:
                rospy.logwarn("Using keyboard fallback mode.")
                self.publish_status("FALLBACK_KEYBOARD")
                self.run_keyboard_mode()
            else:
                raise

    def publish_status(self, status):
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)
        rospy.loginfo("[STT STATUS] %s", status)

    def publish_user_speech(self, text):
        text = text.strip()
        if not text:
            return

        msg = String()
        msg.data = text
        self.user_speech_pub.publish(msg)
        rospy.loginfo("Published %s: %s", USER_SPEECH_TOPIC, text)

    def run_keyboard_mode(self):
        rospy.loginfo("Keyboard fallback mode enabled.")
        rospy.loginfo("Type a sentence such as 'done', then press Enter.")

        while not rospy.is_shutdown():
            try:
                text = input("user_speech> ")
            except (EOFError, KeyboardInterrupt):
                break

            self.publish_user_speech(text)

    def run_microphone_mode(self):
        rospy.loginfo("Speak into the microphone. Example: 'done'.")

        with self.microphone as source:
            rospy.loginfo("Calibrating microphone for ambient noise...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            rospy.loginfo("Calibration finished. Energy threshold: %f", self.recognizer.energy_threshold)

            while not rospy.is_shutdown():
                try:
                    self.publish_status("LISTENING")
                    rospy.loginfo("Listening...")
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.listen_timeout,
                        phrase_time_limit=self.phrase_time_limit
                    )

                    self.publish_status("RECOGNIZING")
                    text = self.recognizer.recognize_google(audio, language=self.language)
                    text = text.strip()

                    rospy.loginfo("Recognized speech: %s", text)
                    self.publish_user_speech(text)
                    self.publish_status("IDLE")

                except sr.WaitTimeoutError:
                    rospy.logwarn("No speech detected within timeout.")
                    self.publish_status("TIMEOUT")
                except sr.UnknownValueError:
                    rospy.logwarn("Could not understand audio.")
                    self.publish_status("UNKNOWN_SPEECH")
                except sr.RequestError as e:
                    rospy.logerr("Google SpeechRecognition request error: %s", str(e))
                    self.publish_status("RECOGNITION_SERVICE_ERROR")
                except Exception as e:
                    rospy.logerr("Unexpected STT error: %s", str(e))
                    self.publish_status("ERROR")


if __name__ == "__main__":
    try:
        STTNode()
    except rospy.ROSInterruptException:
        pass

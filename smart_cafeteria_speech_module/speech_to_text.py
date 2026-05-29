import speech_recognition as sr
import rospy
from std_msgs.msg import String, Bool

def listen():
    rospy.init_node('speech_to_text_node')

    voice_pub = rospy.Publisher('/voice_command', String, queue_size=10)
    trigger_pub = rospy.Publisher('/trigger_detection', Bool, queue_size=10)

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    rospy.loginfo("Speech node started...")

    while not rospy.is_shutdown():
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            rospy.loginfo("Listening for user command...")
            audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            text = text.lower()

            rospy.loginfo(f"User said: {text}")

            voice_pub.publish(text)

            if "done" in text:
                rospy.loginfo("Triggering object detection...")
                trigger_pub.publish(True)

        except Exception as e:
            rospy.logwarn(f"Could not understand audio: {e}")

if __name__ == '__main__':
    listen()

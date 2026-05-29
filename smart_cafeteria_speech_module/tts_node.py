import rospy
from std_msgs.msg import String
import pyttsx3

engine = pyttsx3.init()

def speak_callback(msg):
    text = msg.data

    rospy.loginfo(f"Speaking: {text}")

    engine.say(text)
    engine.runAndWait()

def main():
    rospy.init_node('tts_node')

    rospy.Subscriber('/tts_message', String, speak_callback)

    rospy.loginfo("TTS Node Started")

    rospy.spin()

if __name__ == '__main__':
    main()

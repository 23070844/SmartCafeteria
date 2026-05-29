import rospy
from std_msgs.msg import String, Bool

state_pub = None
current_state = "IDLE"

def trigger_callback(msg):
    global current_state

    if msg.data:
        current_state = "PROCESSING"
        rospy.loginfo(f"Robot State: {current_state}")
        state_pub.publish(current_state)

def main():
    global state_pub

    rospy.init_node('robot_state_manager')

    state_pub = rospy.Publisher('/robot_state', String, queue_size=10)

    rospy.Subscriber('/trigger_detection', Bool, trigger_callback)

    rospy.loginfo("Robot State Manager Started")

    rospy.spin()

if __name__ == '__main__':
    main()

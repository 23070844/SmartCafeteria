#!/usr/bin/env python3
"""
Keyboard Command Node for testing without microphone.

Type commands in terminal:
- done
- yes
- no
- cancel

ROS Topics:
- Publish: /voice_command    std_msgs/String
"""

import sys
import rospy
from std_msgs.msg import String


def main():
    rospy.init_node("keyboard_command_node")
    pub = rospy.Publisher("/voice_command", String, queue_size=10)

    rospy.loginfo("Keyboard command node started.")
    rospy.loginfo("Type: done / yes / no / cancel")

    while not rospy.is_shutdown():
        try:
            command = input("voice_command> ").strip().lower()
        except EOFError:
            break
        except KeyboardInterrupt:
            break

        if command:
            pub.publish(command)
            rospy.loginfo("Published /voice_command: %s", command)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Mock YOLO Detection Node for integration testing.

This node is only for demo/testing.
It simulates the Object Detection team's YOLO node.

ROS Topics:
- Subscribe: /trigger_detection    std_msgs/Bool
- Publish:   /detected_objects     std_msgs/String
"""

import rospy
from std_msgs.msg import Bool, String


class MockYoloNode:
    def __init__(self):
        rospy.init_node("mock_yolo_node")

        self.mock_detection_json = rospy.get_param("/mock_detection_json", '{"sandwich": 1, "cola": 1}')
        self.delay = float(rospy.get_param("/mock_detection_delay", 2.0))

        self.detected_pub = rospy.Publisher("/detected_objects", String, queue_size=10)
        rospy.Subscriber("/trigger_detection", Bool, self.trigger_callback)

        rospy.loginfo("Mock YOLO node started.")

    def trigger_callback(self, msg):
        if not msg.data:
            return

        rospy.loginfo("Mock YOLO received trigger. Simulating detection...")
        rospy.sleep(self.delay)

        self.detected_pub.publish(self.mock_detection_json)
        rospy.loginfo("Mock YOLO published /detected_objects: %s", self.mock_detection_json)


if __name__ == "__main__":
    try:
        MockYoloNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

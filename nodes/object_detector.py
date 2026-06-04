#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import json
import rospy
from collections import Counter
from std_msgs.msg import String
from ultralytics import YOLO


class CafeteriaVisionNode:
    """YOLO vision + billing node for the Smart Cafeteria ROS1 system.

    Responsibilities:
    1. Listen to /smart_cafeteria/intent.
    2. When intent == "detect_object", scan the current camera frame.
    3. Count detected cafeteria items.
    4. Match prices and calculate subtotals / total.
    5. Publish the receipt as a JSON string to /smart_cafeteria/yolo_detections.
    """

    INTENT_TOPIC = "/smart_cafeteria/intent"
    YOLO_OUTPUT_TOPIC = "/smart_cafeteria/yolo_detections"

    def _load_menu(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            rospy.logerr(f"CafeteriaVisionNode: Failed to load menu JSON from {path}: {e}")
            return []

    def __init__(self):
        rospy.loginfo("Initializing Smart Cafeteria YOLO vision + billing node...")

        # ROS params make the node easier to run on different robots/laptops.
        self.camera_index = rospy.get_param("~camera_index", 2)
        self.conf_threshold = rospy.get_param("~conf_threshold", 0.25)
        self.show_window = rospy.get_param("~show_window", True)

        # The scan is triggered by a ROS intent message. Space key is kept only
        # as a manual test shortcut when a screen/keyboard is available.
        self.scan_requested = False
        self.last_receipt = None

        # YOLO-World model.
        rospy.loginfo("Loading YOLO-World model...")
        self.model = YOLO("yolov8s-world.pt")

        # Load Menu Database JSON
        menu_path = rospy.get_param('~menu_path', '')
        if not menu_path:
            try:
                import rospkg
                r = rospkg.RosPack()
                menu_path = os.path.join(r.get_path('smart_cafeteria'), 'src', 'config', 'menu.json')
            except Exception:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                menu_path = os.path.join(script_dir, '..', 'src', 'config', 'menu.json')

        rospy.loginfo(f"CafeteriaVisionNode: Loading menu database from: {menu_path}")
        menu_data = self._load_menu(menu_path)

        # Build custom classes and price mappings from the menu JSON
        self.custom_classes = [item["name"] for item in menu_data]
        self.menu_prices = {item["name"]: item["price"] for item in menu_data}

        self.model.set_classes(self.custom_classes)
        rospy.loginfo("YOLO custom classes loaded from menu: %s", self.custom_classes)

        # Publish JSON string receipt to the LLM / downstream node.
        self.yolo_pub = rospy.Publisher(
            self.YOLO_OUTPUT_TOPIC,
            String,
            queue_size=10,
        )

        # Listen to the LLM brain's intent topic. STT should feed the LLM first;
        # this node should receive the stable control keyword "detect_object".
        self.intent_sub = rospy.Subscriber(
            self.INTENT_TOPIC,
            String,
            self.intent_callback,
            queue_size=10,
        )

    def intent_callback(self, msg):
        """React to control commands from the LLM brain node."""
        intent = msg.data.strip().lower()
        rospy.loginfo("Received intent: %s", intent)

        if intent == "detect_object":
            self.scan_requested = True
        elif intent == "cancel_transaction":
            self.scan_requested = False
            self.last_receipt = None
            rospy.loginfo("Transaction cancelled; cached receipt cleared.")

    def extract_detected_classes(self, results):
        """Convert YOLO result boxes into a list of class names."""
        detected_classes = []

        for box in results[0].boxes:
            confidence = float(box.conf[0].item()) if box.conf is not None else 0.0
            if confidence < self.conf_threshold:
                continue

            class_id = int(box.cls[0].item())
            class_name = self.model.names[class_id]
            detected_classes.append(class_name)

        return detected_classes

    def calculate_bill(self, item_counts):
        """Match detected items to prices and calculate the final bill."""
        total_price = 0.0
        order_details = []
        unknown_items = []

        for item, count in item_counts.items():
            if item not in self.menu_prices:
                unknown_items.append({"name": item, "count": count})
                continue

            unit_price = self.menu_prices[item]
            subtotal = unit_price * count
            total_price += subtotal

            order_details.append({
                "name": item,
                "count": count,
                "unit_price_RM": round(unit_price, 2),
                "subtotal_RM": round(subtotal, 2),
            })

        return {
            "source": "yolo_vision_node",
            "currency": "RM",
            "total_bill_RM": round(total_price, 2),
            "order_details": order_details,
            "unknown_items": unknown_items,
        }

    def publish_receipt(self, receipt_dict):
        """Publish receipt as std_msgs/String containing valid JSON."""
        json_output = json.dumps(receipt_dict, ensure_ascii=False)
        self.yolo_pub.publish(String(data=json_output))

        rospy.loginfo("Published receipt JSON to %s", self.YOLO_OUTPUT_TOPIC)
        print("\n" + "=" * 45)
        print("[Billing System] Receipt Generated:")
        print(json.dumps(receipt_dict, ensure_ascii=False, indent=4))
        print("=" * 45 + "\n")

    def scan_and_publish(self, results):
        """Count the latest YOLO detections, calculate bill, and publish."""
        detected_classes = self.extract_detected_classes(results)
        item_counts = dict(Counter(detected_classes))
        receipt_dict = self.calculate_bill(item_counts)
        self.last_receipt = receipt_dict
        self.publish_receipt(receipt_dict)

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            rospy.logerr("Cannot open camera index %s", self.camera_index)
            return

        rospy.loginfo(
            "Node ready. Waiting for intent '%s' on %s. Press SPACE to test, q to quit.",
            "detect_object",
            self.INTENT_TOPIC,
        )

        try:
            while not rospy.is_shutdown():
                success, frame = cap.read()
                if not success:
                    rospy.logwarn("Failed to read camera frame.")
                    continue

                results = self.model(frame, verbose=False)

                if self.show_window:
                    annotated_frame = results[0].plot()
                    cv2.imshow("Juno Smart Cafeteria - YOLO World", annotated_frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break
                    elif key == 32:  # SPACE, manual local test
                        self.scan_requested = True

                if self.scan_requested:
                    self.scan_requested = False
                    self.scan_and_publish(results)

        finally:
            cap.release()
            cv2.destroyAllWindows()
            rospy.loginfo("YOLO vision + billing node closed safely.")


if __name__ == "__main__":
    rospy.init_node("object_detection_node", anonymous=False)
    node = CafeteriaVisionNode()
    node.run()

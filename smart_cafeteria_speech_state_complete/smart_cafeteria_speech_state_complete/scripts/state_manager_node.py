#!/usr/bin/env python3
"""
Robot State Manager Node for Smart Cafeteria.

This is the main integration node for Task 2:
Speech-to-Text & Robot State Indicators.

Responsibilities:
1. Receive recognized voice commands from /voice_command.
2. Detect user intent such as "done", "yes", "no", and "cancel".
3. Publish /trigger_detection=True when the user says "done".
4. Publish robot status to /robot_state.
5. Publish TTS messages to /tts_message.
6. Receive YOLO object detection result from /detected_objects.
7. Ask the user for confirmation.
8. Forward the confirmed item list to /checkout_confirmed for the LLM / payment team.

ROS Topics:
- Subscribe: /voice_command        std_msgs/String
- Subscribe: /detected_objects     std_msgs/String
- Subscribe: /payment_status       std_msgs/String

- Publish:   /trigger_detection    std_msgs/Bool
- Publish:   /robot_state          std_msgs/String
- Publish:   /tts_message          std_msgs/String
- Publish:   /checkout_confirmed   std_msgs/String
- Publish:   /recount_request      std_msgs/Bool
"""

import json
import rospy
from std_msgs.msg import String, Bool


class RobotState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    COUNTING = "COUNTING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class StateManagerNode:
    def __init__(self):
        rospy.init_node("state_manager_node")

        self.done_phrases = self._load_phrase_list("/done_phrases", ["done", "finish", "finished", "start counting"])
        self.yes_phrases = self._load_phrase_list("/yes_phrases", ["yes", "correct", "confirm", "ok", "okay"])
        self.no_phrases = self._load_phrase_list("/no_phrases", ["no", "wrong", "incorrect", "recount", "again"])
        self.cancel_phrases = self._load_phrase_list("/cancel_phrases", ["cancel", "stop", "reset"])

        self.state = RobotState.IDLE
        self.last_detected_objects_raw = ""
        self.last_detected_objects = None

        self.trigger_pub = rospy.Publisher("/trigger_detection", Bool, queue_size=10)
        self.state_pub = rospy.Publisher("/robot_state", String, queue_size=10, latch=True)
        self.tts_pub = rospy.Publisher("/tts_message", String, queue_size=10)
        self.checkout_pub = rospy.Publisher("/checkout_confirmed", String, queue_size=10)
        self.recount_pub = rospy.Publisher("/recount_request", Bool, queue_size=10)

        rospy.Subscriber("/voice_command", String, self.voice_callback)
        rospy.Subscriber("/detected_objects", String, self.detected_objects_callback)
        rospy.Subscriber("/payment_status", String, self.payment_status_callback)

        rospy.sleep(0.5)
        self.set_state(RobotState.LISTENING)
        self.say("Speech module is ready. Please say done when all items are on the tray.")

        rospy.loginfo("State manager node started.")

    @staticmethod
    def _load_phrase_list(param_name, default_value):
        value = rospy.get_param(param_name, default_value)
        if isinstance(value, list):
            return [str(x).lower() for x in value]
        return default_value

    @staticmethod
    def _contains_any(text, phrases):
        return any(phrase in text for phrase in phrases)

    def set_state(self, new_state):
        self.state = new_state
        self.state_pub.publish(new_state)
        rospy.loginfo("Robot state changed to: %s", new_state)

    def say(self, text):
        rospy.loginfo("TTS message: %s", text)
        self.tts_pub.publish(text)

    def voice_callback(self, msg):
        command = msg.data.strip().lower()
        rospy.loginfo("Voice command received by state manager: %s", command)

        if not command:
            return

        if self._contains_any(command, self.cancel_phrases):
            self.reset_session()
            return

        if self._contains_any(command, self.done_phrases):
            self.start_counting()
            return

        if self.state == RobotState.WAITING_CONFIRMATION:
            if self._contains_any(command, self.yes_phrases):
                self.confirm_items()
                return

            if self._contains_any(command, self.no_phrases):
                self.request_recount()
                return

            self.say("Please say yes to confirm, or no to recount.")
            return

        rospy.loginfo("Command ignored in current state: %s", self.state)

    def start_counting(self):
        self.last_detected_objects_raw = ""
        self.last_detected_objects = None

        self.set_state(RobotState.COUNTING)
        self.say("Start counting. Please wait.")
        self.trigger_pub.publish(True)

        rospy.loginfo("Published /trigger_detection = True")

    def detected_objects_callback(self, msg):
        raw = msg.data.strip()

        if not raw:
            rospy.logwarn("Received empty detected object message.")
            return

        self.last_detected_objects_raw = raw
        self.last_detected_objects = self._parse_detected_objects(raw)

        rospy.loginfo("Detected objects received: %s", raw)

        summary = self._build_object_summary(self.last_detected_objects)
        self.set_state(RobotState.WAITING_CONFIRMATION)

        if summary:
            self.say("I detected " + summary + ". Is this correct? Please say yes or no.")
        else:
            self.say("I received the detection result. Is this correct? Please say yes or no.")

    def confirm_items(self):
        if not self.last_detected_objects_raw:
            self.say("No detected item list is available. Please say done to count again.")
            self.set_state(RobotState.LISTENING)
            return

        self.checkout_pub.publish(self.last_detected_objects_raw)
        self.set_state(RobotState.PAYMENT_PROCESSING)
        self.say("Confirmed. Processing payment.")

        rospy.loginfo("Published confirmed items to /checkout_confirmed: %s", self.last_detected_objects_raw)

    def request_recount(self):
        self.set_state(RobotState.COUNTING)
        self.say("Okay. Recounting the tray now.")
        self.recount_pub.publish(True)
        self.trigger_pub.publish(True)

        rospy.loginfo("Published recount request and /trigger_detection = True")

    def reset_session(self):
        self.last_detected_objects_raw = ""
        self.last_detected_objects = None
        self.set_state(RobotState.LISTENING)
        self.say("Session reset. Please say done when you are ready.")

    def payment_status_callback(self, msg):
        status = msg.data.strip().lower()
        rospy.loginfo("Payment status received: %s", status)

        if status in ["paid", "complete", "completed", "success", "successful"]:
            self.set_state(RobotState.COMPLETE)
            self.say("Payment complete. Thank you.")
        elif status in ["failed", "error", "cancelled", "canceled"]:
            self.set_state(RobotState.ERROR)
            self.say("Payment failed. Please try again or ask for assistance.")

    @staticmethod
    def _parse_detected_objects(raw):
        try:
            return json.loads(raw)
        except Exception:
            return raw

    @staticmethod
    def _build_object_summary(objects):
        if isinstance(objects, dict):
            parts = []
            for name, count in objects.items():
                try:
                    count_int = int(count)
                except Exception:
                    count_int = count
                parts.append(f"{count_int} {name}")
            return ", ".join(parts)

        if isinstance(objects, list):
            if not objects:
                return "no items"
            return ", ".join(str(x) for x in objects)

        if isinstance(objects, str):
            return objects

        return ""


if __name__ == "__main__":
    try:
        StateManagerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

# ROS Topic Unit Testing & Integration Guide

This guide details how to unit test the publishing and subscribing functionality of the core communication topics in the **Smart Cafeteria Self-Checkout Kiosk** system on Linux.

---

## 1. ROS Communication Reference

| Topic Name | Message Type | Publisher Node | Subscriber Node(s) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/smart_cafeteria/user_speech` | `std_msgs/String` | `stt_node` | `llm_brain_node` | Recognized speech text from the user. |
| `/smart_cafeteria/intent` | `std_msgs/String` | `llm_brain_node` | `object_detector_node`, `llm_brain_node` | Control intent classified from user speech. |
| `/smart_cafeteria/yolo_detections` | `std_msgs/String` | `object_detector_node` | `llm_brain_node` | JSON string representing items detected on the tray. |
| `/smart_cafeteria/kiosk_response` | `std_msgs/String` | `llm_brain_node` | `tts_node` | Spoken response text for wellness tips and transaction details. |

---

## 2. Test Setup (Linux)

Before running these tests, ensure your workspace is sourced and the main launcher is running:

```bash
# Source Catkin workspace
source ~/Desktop/WQF7010-SMARTCAFETERIA/catkin_ws/devel/setup.bash

roslaunch smart_cafeteria smart_cafeteria.launch
```

---

## 3. Core Topic Tests

### 1. Topic: `/smart_cafeteria/user_speech`

#### A. Test Publishing (Mocking Speech-to-Text Input)
* **Goal:** Verify that a node publishing user speech causes the system to react.
* **Publish Command:**
  ```bash
  rostopic pub -1 /smart_cafeteria/user_speech std_msgs/String "data: 'start checking out'"
  ```
* **Expected Output/Reaction:**
  * The `llm_brain_node` log should output:
    ```
    LLMBrainNode [STT Callback]: User said: 'start checking out'
    LLMBrainNode [STT Callback]: Parsed intent keyword: 'detect_object'
    ```

#### B. Test Subscribing (Monitoring Speech-to-Text Stream)
* **Goal:** Verify that the Speech-to-Text node successfully publishes speech text when the user speaks or types.
* **Subscribe Command:**
  ```bash
  rostopic echo /smart_cafeteria/user_speech
  ```
* **Expected Output/Reaction:**
  * When you speak into the microphone (or type into the terminal in STT fallback mode), you should see the raw transcript appear in real time:
    ```yaml
    data: "is the burger healthy"
    ---
    ```

---

### 2. Topic: `/smart_cafeteria/intent`

#### A. Test Publishing (Mocking Intent Commands)
* **Goal:** Verify that subscribers react correctly to different control intents.
* **Publish Command (Trigger YOLO scanning):**
  ```bash
  rostopic pub -1 /smart_cafeteria/intent std_msgs/String "data: 'detect_object'"
  ```
* **Expected Output/Reaction:**
  * The `object_detector_node` log will show that a scan has been requested:
    ```
    Received intent: detect_object
    ```
  * If a camera is connected, it will capture the current frame, run YOLO detection, and publish the results to `/smart_cafeteria/yolo_detections`.

* **Publish Command (Trigger conversation reply):**
  ```bash
  rostopic pub -1 /smart_cafeteria/intent std_msgs/String "data: 'chatting'"
  ```
* **Expected Output/Reaction:**
  * The `llm_brain_node` log will show:
    ```
    LLMBrainNode [Intent Callback]: Received intent: 'chatting'
    ```

#### B. Test Subscribing (Monitoring Intent Logic)
* **Goal:** Verify that the system publishes the correct intent classification based on user speech.
* **Subscribe Command:**
  ```bash
  rostopic echo /smart_cafeteria/intent
  ```
* **Expected Output/Reaction:**
  * When speech is published, you should see the matching intent:
    * For *"start checking out"* $\rightarrow$ `data: "detect_object"`
    * For *"is the milk box healthy"* $\rightarrow$ `data: "chatting"`
    * For *"proceed to pay"* $\rightarrow$ `data: "proceed_payment"`
    * For *"cancel this transaction"* $\rightarrow$ `data: "cancel_transaction"`

---

### 3. Topic: `/smart_cafeteria/yolo_detections`

#### A. Test Publishing (Mocking Object Detections)
* **Goal:** Verify that publishing detection data triggers price/calorie calculation and generates wellness advice.
* **Publish Command:**
  ```bash
  rostopic pub -1 /smart_cafeteria/yolo_detections std_msgs/String "data: '{\"source\": \"yolo_vision_node\", \"currency\": \"RM\", \"total_bill_RM\": 4.70, \"order_details\": [{\"name\": \"Coca Cola\", \"count\": 1, \"unit_price_RM\": 3.50, \"subtotal_RM\": 3.50}, {\"name\": \"water bottle\", \"count\": 1, \"unit_price_RM\": 1.20, \"subtotal_RM\": 1.20}], \"unknown_items\": []}'"
  ```
* **Expected Output/Reaction:**
  * The `llm_brain_node` log should show the parsed items and subtotal:
    ```
    LLMBrainNode [Vision Callback]: Received detections: ...
    LLMBrainNode: Processing 2 order_details and 0 unknown_items.
    LLMBrainNode: Final Calculated Subtotal (Python): RM 4.70
    LLMBrainNode: Publishing checkout response: ...
    ```

#### B. Test Subscribing (Monitoring YOLO Output)
* **Goal:** Verify that the vision subsystem publishes the detected objects correctly.
* **Subscribe Command:**
  ```bash
  rostopic echo /smart_cafeteria/yolo_detections
  ```
* **Expected Output/Reaction:**
  * When YOLO is triggered by `detect_object` (or when spacebar is pressed in the YOLO window), a JSON receipt string should appear:
    ```yaml
    data: "{\"source\": \"yolo_vision_node\", \"currency\": \"RM\", \"total_bill_RM\": 15.0, \"order_details\": [{\"name\": \"burger\", \"count\": 1, \"unit_price_RM\": 15.0, \"subtotal_RM\": 15.0}], \"unknown_items\": []}"
    ---
    ```

---

### 4. Topic: `/smart_cafeteria/kiosk_response`

#### A. Test Publishing (Mocking Kiosk Audio/Text Output)
* **Goal:** Verify that publishing a raw response causes the Text-to-Speech system to speak the text.
* **Publish Command:**
  ```bash
  rostopic pub -1 /smart_cafeteria/kiosk_response std_msgs/String "data: 'Welcome to the Smart Cafeteria'"
  ```
* **Expected Output/Reaction:**
  * The `tts_node` will log:
    ```
    Received kiosk response: Welcome to the Smart Cafeteria
    Speaking: Welcome to the Smart Cafeteria
    ```
  * The computer speakers will play the audio readout of the text.

#### B. Test Subscribing (Monitoring Kiosk Output text)
* **Goal:** Verify that the LLM Brain publishes generated wellness responses and transaction prompts.
* **Subscribe Command:**
  ```bash
  rostopic echo /smart_cafeteria/kiosk_response
  ```
* **Expected Output/Reaction:**
  * You should receive the generated conversational replies or total cost statements. For example, after mocking a YOLO scan:
    ```yaml
    data: "Your total comes to fifteen ringgit. You might want to add some green vegetables to balance out the calorie intake. How would you like to pay?"
    ---
    ```

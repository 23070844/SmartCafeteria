# Smart Cafeteria - Speech-to-Text & Robot State Indicators

## Contributor

**Duan Bowen**  
Task 2: **Speech-to-Text & Robot State Indicators**

---

## 1. Module Overview

This package implements the full Task 2 module for the Smart Cafeteria Self-Checkout Kiosk System.

The module manages:

1. Microphone-based Speech-to-Text
2. Voice command detection
3. Robot state indicators
4. YOLO detection trigger
5. Text-to-Speech voice feedback
6. Confirmation flow after object detection
7. Integration with LLM / payment module

---

## 2. Main Workflow

```text
User places food on tray
        ↓
User says "Done"
        ↓
STT Node publishes /voice_command
        ↓
State Manager publishes /trigger_detection = True
        ↓
YOLO Node detects food and publishes /detected_objects
        ↓
State Manager asks user to confirm result
        ↓
User says "Yes"
        ↓
State Manager publishes /checkout_confirmed
        ↓
LLM / payment module continues transaction
```

---

## 3. ROS Nodes

| Node | File | Function |
|---|---|---|
| STT Node | `scripts/stt_node.py` | Converts microphone audio to text |
| State Manager Node | `scripts/state_manager_node.py` | Controls robot state and system flow |
| TTS Node | `scripts/tts_node.py` | Speaks robot messages |
| Keyboard Test Node | `scripts/keyboard_command_node.py` | Allows testing without microphone |
| Mock YOLO Node | `scripts/mock_yolo_node.py` | Simulates YOLO detection for testing |

---

## 4. ROS Topics

| Topic | Type | Description |
|---|---|---|
| `/voice_command` | `std_msgs/String` | Recognized speech command |
| `/trigger_detection` | `std_msgs/Bool` | Trigger signal for YOLO detection |
| `/robot_state` | `std_msgs/String` | Current robot state |
| `/tts_message` | `std_msgs/String` | Text to be spoken by the robot |
| `/detected_objects` | `std_msgs/String` | Detection result from YOLO |
| `/checkout_confirmed` | `std_msgs/String` | Confirmed item list for LLM / payment |
| `/payment_status` | `std_msgs/String` | Payment status from payment module |
| `/recount_request` | `std_msgs/Bool` | Request object detection team to recount |

---

## 5. Robot States

| State | Meaning |
|---|---|
| `LISTENING` | Waiting for user voice command |
| `COUNTING` | Object detection is triggered |
| `WAITING_CONFIRMATION` | Waiting for user to say yes or no |
| `PAYMENT_PROCESSING` | Confirmed items sent to payment / LLM module |
| `COMPLETE` | Payment completed |
| `ERROR` | Payment or system error |

---

## 6. Installation

Put this package inside your catkin workspace:

```bash
cd ~/catkin_ws/src
git clone <your-repository-url>
```

Or copy the folder directly:

```bash
cp -r smart_cafeteria_speech_state ~/catkin_ws/src/
```

Install Python dependencies:

```bash
cd ~/catkin_ws/src/smart_cafeteria_speech_state
pip3 install -r requirements.txt
```

If PyAudio fails to install:

```bash
sudo apt update
sudo apt install portaudio19-dev python3-pyaudio
pip3 install SpeechRecognition pyttsx3 PyYAML
```

Build workspace:

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

Make scripts executable if needed:

```bash
chmod +x ~/catkin_ws/src/smart_cafeteria_speech_state/scripts/*.py
```

---

## 7. Run Full System with Real Microphone

```bash
roslaunch smart_cafeteria_speech_state speech_system.launch
```

Then say:

```text
done
```

The module will publish:

```text
/trigger_detection = True
```

---

## 8. Run Demo Test without Microphone

This is useful for classroom demo and GitHub verification.

```bash
roslaunch smart_cafeteria_speech_state demo_test.launch
```

Then type in the terminal:

```text
done
```

The mock YOLO node will publish:

```json
{"sandwich": 1, "cola": 1}
```

Then type:

```text
yes
```

The state manager will publish the confirmed item list to:

```text
/checkout_confirmed
```

---

## 9. Integration Notes for YOLO Team

The YOLO node should subscribe to:

```text
/trigger_detection
```

When it receives:

```text
True
```

it should freeze the camera frame and perform object detection.

After detection, YOLO should publish the result to:

```text
/detected_objects
```

Recommended format:

```json
{"sandwich": 1, "cola": 1}
```

---

## 10. Integration Notes for LLM / Payment Team

The LLM / payment module should subscribe to:

```text
/checkout_confirmed
```

Example message:

```json
{"sandwich": 1, "cola": 1}
```

After payment is completed, it can publish:

```text
/payment_status = paid
```

Then this module will announce:

```text
Payment complete. Thank you.
```

---

## 11. Quick Topic Test Commands

Manually trigger detection:

```bash
rostopic pub /voice_command std_msgs/String "data: 'done'"
```

Mock YOLO publishes detection result:

```bash
rostopic pub /detected_objects std_msgs/String "data: '{\"sandwich\": 1, \"cola\": 1}'"
```

Confirm result:

```bash
rostopic pub /voice_command std_msgs/String "data: 'yes'"
```

Check robot state:

```bash
rostopic echo /robot_state
```

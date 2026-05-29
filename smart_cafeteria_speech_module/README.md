# Smart Cafeteria - Speech & Robot State Module

## Overview

This module handles:

- Speech-to-Text (STT)
- Robot State Management
- Voice Command Detection
- Text-to-Speech (TTS)

The node listens for user commands such as "Done" and triggers the object detection module.

---

## ROS Topics

| Topic | Type | Description |
|---|---|---|
| /voice_command | String | Detected speech command |
| /trigger_detection | Bool | Trigger YOLO detection |
| /robot_state | String | Robot current state |
| /tts_message | String | Text for robot speech |

---

## Dependencies

```bash
pip install -r requirements.txt
```

---

## Run

```bash
python speech_to_text.py
python robot_state_manager.py
python tts_node.py
```

---

## Responsibilities

- Implemented Speech-to-Text node using Python SpeechRecognition
- Developed robot state management node using ROS topics
- Integrated trigger mechanism for YOLO object detection
- Added Text-to-Speech feedback system

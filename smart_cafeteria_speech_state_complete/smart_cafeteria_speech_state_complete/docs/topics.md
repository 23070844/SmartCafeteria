# ROS Integration Topics

## Provided by Speech & Robot State Module

| Topic | Type | Direction | Description |
|---|---|---|---|
| `/voice_command` | `std_msgs/String` | Publish | Raw recognized speech text |
| `/robot_state` | `std_msgs/String` | Publish | Current robot state |
| `/tts_message` | `std_msgs/String` | Publish / Subscribe | Text that should be spoken by robot |
| `/trigger_detection` | `std_msgs/Bool` | Publish | Trigger YOLO object detection |
| `/checkout_confirmed` | `std_msgs/String` | Publish | Confirmed detected items for LLM / payment team |
| `/recount_request` | `std_msgs/Bool` | Publish | Request to recount tray items |

## Required from Object Detection Team

| Topic | Type | Description |
|---|---|---|
| `/detected_objects` | `std_msgs/String` | JSON string, e.g. `{"sandwich": 1, "cola": 1}` |

## Optional from Payment / LLM Team

| Topic | Type | Description |
|---|---|---|
| `/payment_status` | `std_msgs/String` | Example: `paid`, `complete`, `failed` |

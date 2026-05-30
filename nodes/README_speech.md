# Task 2 — Speech to Text (STT) + Text to Speech (TTS)

两个独立 ROS 节点，分别负责「听」和「说」。

---

## 节点总览

```
麦克风 ──► [ stt_node ] ──► /speech_text  (文字)
                        ──► /robot_state  (状态)

/tts_say (文字) ──► [ tts_node ] ──► 🔊 喇叭
                               ──► /robot_state  (状态)
```

---

## Node 1: stt_node.py — 语音转文字

| 项目 | 内容 |
|------|------|
| **输入** | 真实麦克风 |
| **输出 Topic** | `/speech_text` — 识别到的文字 |
| **输出 Topic** | `/robot_state` — `IDLE` / `LISTENING` / `COUNTING` |
| **关键词** | 说 "Done" → 自动发布 `COUNTING` 状态给 Object Detection 团队 |

---

## Node 2: tts_node.py — 文字转语音

| 项目 | 内容 |
|------|------|
| **输入 Topic** | `/tts_say` — 发文字过来，机器人就说出来 |
| **输出** | 🔊 喇叭朗读 |
| **输出 Topic** | `/robot_state` — `SPEAKING` / `IDLE` |

---

## 安装依赖

```bash
# Python 库
pip install SpeechRecognition pyttsx3 pyaudio

# 如果 Ubuntu 上 pyaudio 报错：
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio

# 如果 pyttsx3 没声音（Linux）：
sudo apt-get install espeak
```

---

## 运行方法

```bash
# 方法 1：同时启动两个节点
roslaunch speech_ros speech_ros.launch

# 方法 2：分开启动
rosrun speech_ros stt_node.py   # 终端 1
rosrun speech_ros tts_node.py   # 终端 2
```

---

## 测试命令

```bash
# 看麦克风识别结果
rostopic echo /speech_text

# 看机器人状态变化
rostopic echo /robot_state

# 手动让机器人说话（测试 TTS）
rostopic pub /tts_say std_msgs/String "data: 'Start Counting'"
rostopic pub /tts_say std_msgs/String "data: 'Processing payment, total is 5 ringgit'"
rostopic pub /tts_say std_msgs/String "data: 'Please eat more vegetables'"
```

---

## 与其他队友的接口

### Yean Yee & Xiao Jin（Object Detection）
订阅 `/robot_state`，收到 `COUNTING` 才开始拍照：
```python
rospy.Subscriber("/robot_state", String, state_cb)
def state_cb(msg):
    if msg.data == "COUNTING":
        trigger_detection()
```

### LLM Calculation 团队
订阅 `/speech_text` 获取用户说的话（yes/no 意图）：
```python
rospy.Subscriber("/speech_text", String, speech_cb)
```
让机器人报价格，直接发布到 `/tts_say`：
```python
pub = rospy.Publisher("/tts_say", String, queue_size=10)
pub.publish("Your total is 8 ringgit 50 sen. Confirm payment?")
```

### Kai Wen（Nutrition）
营养建议直接发布到 `/tts_say`，机器人就会朗读：
```python
pub.publish("Warning: high calorie meal detected. Consider reducing sugar intake.")
```

---

## 文件结构

```
speech_ros/
├── scripts/
│   ├── stt_node.py          ← Node 1: 麦克风 → 文字
│   └── tts_node.py          ← Node 2: 文字 → 声音
├── launch/
│   └── speech_ros.launch    ← 同时启动两个节点
├── CMakeLists.txt
└── package.xml
```

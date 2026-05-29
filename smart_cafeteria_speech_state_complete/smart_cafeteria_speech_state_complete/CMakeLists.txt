cmake_minimum_required(VERSION 3.0.2)
project(smart_cafeteria_speech_state)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
)

catkin_package()

catkin_install_python(PROGRAMS
  scripts/stt_node.py
  scripts/state_manager_node.py
  scripts/tts_node.py
  scripts/keyboard_command_node.py
  scripts/mock_yolo_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config docs
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

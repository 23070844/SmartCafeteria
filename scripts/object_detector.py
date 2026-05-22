import cv2
import json
from collections import Counter
from ultralytics import YOLO


class CafeteriaVisionNode:
    def __init__(self):
        print("初始化智慧食堂视觉与计费节点...")
        # 1. 加载模型
        self.model = YOLO('yolov8n.pt')

        # 2. 食堂本地固定价格表 (可以随便改)
        # 注意：这里用的是 YOLOv8n 能认出来的英文名
        self.menu_prices = {
            "cup": 2.5,  # 杯子（假装是咖啡）
            "bottle": 3.0,  # 瓶子（矿泉水）
            "apple": 5.0,  # 苹果
            "sandwich": 8.0,  # 三明治
            "hot dog": 6.0,  # 热狗
            "pizza": 12.0,  # 披萨
            "donut": 4.0,  # 甜甜圈
            "cell phone": 99.0,  # 如果识别到手机，卖99块哈哈！
            "chair": 8.0
        }

    def calculate_bill(self, item_counts):
        """计算总价的专属函数"""
        total_price = 0.0
        calculated_items = {}

        for item, count in item_counts.items():
            # 如果识别出来的东西在我们的价格表里
            if item in self.menu_prices:
                unit_price = self.menu_prices[item]
                subtotal = unit_price * count
                total_price += subtotal

                # 记录详细信息
                calculated_items[item] = {
                    "count": count,
                    "unit_price": unit_price,
                    "subtotal": subtotal
                }
            else:
                # 识别到了价格表里没有的东西，记录下来但价格为 0
                calculated_items[item] = {
                    "count": count,
                    "unit_price": 0.0,
                    "subtotal": 0.0,
                    "note": "不在菜单中"
                }

        # 构建最终要发给 LLM 组的 JSON 格式
        final_receipt = {
            "order_details": calculated_items,
            "total_bill": total_price
        }
        return final_receipt

    def run(self):
        """启动摄像头主循环"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 找不到摄像头！")
            return

        print("✅ 节点就绪！")
        print("👉 按 '空格键' 生成账单，按 'q' 键退出程序。")

        while True:
            success, frame = cap.read()
            if not success:
                break

            # 推理并显示画面
            results = self.model(frame, verbose=False)
            annotated_frame = results[0].plot()
            cv2.imshow("Smart Cafeteria - Vision & Billing", annotated_frame)

            key = cv2.waitKey(1) & 0xFF

            # 按 'q' 退出
            if key == ord('q'):
                break

            # 按 '空格键' 触发计算
            elif key == 32:
                detected_classes = []
                for box in results[0].boxes:
                    class_id = int(box.cls[0].item())
                    detected_classes.append(self.model.names[class_id])

                # 1. 统计数量
                item_counts = dict(Counter(detected_classes))

                # 2. 计算价格并生成小票格式字典
                receipt_dict = self.calculate_bill(item_counts)

                # 3. 转换成漂亮的 JSON 字符串
                json_output = json.dumps(receipt_dict, ensure_ascii=False, indent=4)

                print("\n" + "=" * 40)
                print("🎤 收到语音组 'Done' 信号！")
                print("🧾 结账单生成完毕，发送给 LLM 营养组：")
                print(json_output)
                print("=" * 40 + "\n")

        cap.release()
        cv2.destroyAllWindows()
        print("节点已关闭。")


if __name__ == '__main__':
    # 实例化我们的类，并运行！
    node = CafeteriaVisionNode()
    node.run()
import cv2
import json
from collections import Counter
from ultralytics import YOLO


class CafeteriaVisionNode:
    def __init__(self):
        print("初始化【智慧食堂-大马超市版】视觉与计费节点...")
        # 加载模型（目前先用标准模型，后续换成我们自己训练的 juno_food.pt）
        self.model = YOLO('yolov8n.pt')

        # 马来西亚超市常见食品/饮料价格表 (单位：马币 RM)
        self.menu_prices = {
            # --- 以下是 YOLO 默认自带就能识别的类别 ---
            "apple": 2.00,  # 苹果 (单粒)
            "banana": 1.50,  # 香蕉 (单条)
            "orange": 2.20,  # 橙子 (单粒)
            "sandwich": 6.50,  # 三明治 (便利店三角包)
            "donut": 3.50,  # 甜甜圈
            "cake": 5.50,  # 切片蛋糕
            "bottle": 1.20,  # 矿泉水 (默认模型通常把所有瓶子认成 bottle)

            # --- 以下是咱们接下来通过 A 路线要教会它认识的专属超市单品 ---
            "cola": 2.50,  # 可口可乐听装
            "sprite": 2.50,  # 雪碧听装
            "milk": 3.80,  # 盒装全脂牛奶 (如 Goodday/Marigold)
            "potato_chips": 4.80,  # 薯片 (如 Lay's 或 Mamee 筒装)
            "biscuit": 3.90,  # 奥利奥饼干
            "bread": 4.50  # Gardenia 白面包
        }

    def calculate_bill(self, item_counts):
        """核心计费逻辑：计算马币总价"""
        total_price = 0.0
        calculated_items = {}

        for item, count in item_counts.items():
            if item in self.menu_prices:
                unit_price = self.menu_prices[item]
                subtotal = unit_price * count
                total_price += subtotal

                calculated_items[item] = {
                    "count": count,
                    "unit_price_RM": round(unit_price, 2),
                    "subtotal_RM": round(subtotal, 2)
                }
            else:
                # 识别到菜单外的物品（比如暂时把人或椅子算进来）
                calculated_items[item] = {
                    "count": count,
                    "unit_price_RM": 0.0,
                    "subtotal_RM": 0.0,
                    "note": "Not a food item"
                }

        # 生成完美对接大模型营养组的 JSON 报文
        final_receipt = {
            "currency": "RM",
            "total_bill_RM": round(total_price, 2),
            "order_details": calculated_items
        }
        return final_receipt

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 找不到摄像头！")
            return

        print("✅ 节点就绪！")
        print("👉 镜头前放好食物，按 '空格键' 生成马币账单")
        print("👉 按 'q' 键退出")

        while True:
            success, frame = cap.read()
            if not success:
                break

            results = self.model(frame, verbose=False)
            annotated_frame = results[0].plot()
            cv2.imshow("Juno Smart Cafeteria - MYR Edition", annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

            elif key == 32:  # 空格触发
                detected_classes = []
                for box in results[0].boxes:
                    class_id = int(box.cls[0].item())
                    class_name = self.model.names[class_id]
                    detected_classes.append(class_name)

                item_counts = dict(Counter(detected_classes))
                receipt_dict = self.calculate_bill(item_counts)

                # 打印漂亮的格式化 JSON
                json_output = json.dumps(receipt_dict, ensure_ascii=False, indent=4)
                print("\n" + "=" * 45)
                print("🧾 [Billing System] Receipt Generated:")
                print(json_output)
                print("=" * 45 + "\n")

        cap.release()
        cv2.destroyAllWindows()
        print("节点已安全关闭。")


if __name__ == '__main__':
    node = CafeteriaVisionNode()
    node.run()
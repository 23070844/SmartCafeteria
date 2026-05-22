import cv2
import json
from collections import Counter
from ultralytics import YOLO


class CafeteriaVisionNode:
    def __init__(self):
        print("初始化【智慧食堂-魔法逃课版】视觉与计费节点...")

        # 1. 加载支持“看词识物”的 YOLO-World 预训练模型
        print("正在下载并加载 YOLO-World 模型，请稍候...")
        self.model = YOLO('yolov8s-world.pt')

        # 2. 【核心魔法】在这里用英文写下你们食堂具体要卖的商品！
        # 哪怕是具体的牌子，只要特征明显，它都能强行认出来！
        custom_classes = [
            "Coca Cola can",  # 可口可乐易拉罐
            "milk box",  # 盒装牛奶
            "potato chips bag",  # 袋装薯片
            "sliced bread",  # 切片面包
            "green apple",  # 青苹果
            "mineral water bottle"  # 矿泉水瓶
        ]
        self.model.set_classes(custom_classes)
        print(f"✅ 模型已被赋予看懂以下物品的能力：{custom_classes}")

        # 3. 对应的马币价格表 (名字必须和上面 custom_classes 里的严格一致)
        self.menu_prices = {
            "Coca Cola can": 2.50,
            "milk box": 3.80,
            "potato chips bag": 4.80,
            "sliced bread": 4.50,
            "green apple": 2.00,
            "mineral water bottle": 1.20
        }

    def calculate_bill(self, item_counts):
        """核心计费逻辑"""
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

        print("✅ 节点就绪！按 '空格键' 结账，按 'q' 键退出。")

        while True:
            success, frame = cap.read()
            if not success:
                break

            # 运行推理：它现在只会框出 custom_classes 里定义的那些东西！
            results = self.model(frame, verbose=False)
            annotated_frame = results[0].plot()
            cv2.imshow("Juno Smart Cafeteria - YOLO World", annotated_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == 32:
                detected_classes = []
                for box in results[0].boxes:
                    class_id = int(box.cls[0].item())
                    # 获取模型看出来的物品名字
                    class_name = self.model.names[class_id]
                    detected_classes.append(class_name)

                item_counts = dict(Counter(detected_classes))
                receipt_dict = self.calculate_bill(item_counts)

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
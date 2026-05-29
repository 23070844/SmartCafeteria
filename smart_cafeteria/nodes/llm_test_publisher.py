#!/usr/bin/env python3
import sys
import os
import json
import time
import argparse

# Load .env file automatically if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Helper to find package files locally
def get_local_paths():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    menu_path = os.path.join(script_dir, '..', 'config', 'menu.json')
    return menu_path

def run_local_test(endpoint, key, model, offline_mode):
    """
    Runs the full conversational checkout sequence locally in Python.
    """
    print("\n" + "="*60)
    print("RUNNING LOCAL CONVERSATIONAL CLIENT TEST (NO ROS)")
    print("="*60)
    
    from azure_ai_client import AzureAIFoundryClient
    
    menu_path = get_local_paths()
    try:
        with open(menu_path, 'r') as f:
            menu_data = json.load(f)
    except Exception as e:
        print(f"Error loading menu: {e}")
        return

    # Initialize client
    client = AzureAIFoundryClient(
        endpoint=endpoint,
        api_key=key,
        model_name=model,
        offline_mode=offline_mode
    )

    # 1. Start Checkout
    print("\n[Step 1] User speech: 'start checking out'")
    intent = client.parse_speech_intent("start checking out")
    print(f"  -> Parsed Intent: '{intent}' (Expect: 'detect_object')")

    # 2. Simulate Detections & Billing
    print("\n[Step 2] YOLO detects items: Fried Chicken (1x) and Coca-Cola (1x)")
    yolo_detections = [{"id": "fried_chicken", "quantity": 1}, {"id": "coke", "quantity": 1}]
    
    # Python-based price matching and subtotal calculation
    matched_items = []
    subtotal = 0.0
    for detect in yolo_detections:
        item_id = detect["id"]
        qty = detect["quantity"]
        for item in menu_data:
            if item["id"] == item_id:
                matched_items.append({
                    "name": item["name"],
                    "quantity": qty,
                    "price": item["price"],
                    "total_price": item["price"] * qty,
                    "calories": item["calories"]
                })
                subtotal += item["price"] * qty
                break
    
    print(f"  -> Matched Items: {[item['name'] for item in matched_items]}")
    print(f"  -> Calculated Subtotal (Python): RM {subtotal:.2f}")

    # Generate Advice
    advice = client.get_nutritional_advice(matched_items, subtotal)
    combined_response = f"Your total is RM {subtotal:.2f}. {advice}"
    print(f"  -> Combined Response (Advice + Price):\n     '{combined_response}'")

    # Initialize history
    chat_history = [
        {"role": "user", "content": "start checking out"},
        {"role": "assistant", "content": combined_response}
    ]

    # 3. Follow-up Question
    user_q = "What is the benefit of changing milk to oatmilk?"
    print(f"\n[Step 3] User speech: '{user_q}'")
    intent = client.parse_speech_intent(user_q)
    print(f"  -> Parsed Intent: '{intent}' (Expect: 'chatting')")
    
    chat_history.append({"role": "user", "content": user_q})
    
    # Generate conversational Q&A response
    # We build the dynamic system prompt containing the menu and tray state
    system_prompt = (
        "You are a helpful, friendly wellness self-checkout kiosk assistant.\n"
        f"The menu is:\n{json.dumps(menu_data, indent=2)}\n"
        f"The user has these items on their tray:\n{json.dumps(matched_items, indent=2)}\n"
        f"Subtotal: RM {subtotal:.2f}\n"
    )
    full_history = [{"role": "system", "content": system_prompt}] + chat_history
    reply = client.generate_conversational_reply(full_history)
    print(f"  -> LLM Chat Reply:\n     '{reply}'")
    chat_history.append({"role": "assistant", "content": reply})

    # 4. Proceed to payment
    user_confirm = "proceed with payment"
    print(f"\n[Step 4] User speech: '{user_confirm}'")
    intent = client.parse_speech_intent(user_confirm)
    print(f"  -> Parsed Intent: '{intent}' (Expect: 'proceed_payment')")
    
    print("\n[Step 5] Resetting session states.")
    chat_history = []
    print("  -> Session cleared successfully!")
    print("="*60 + "\n")

def run_ros_test():
    """
    Runs the test by publishing and subscribing to the ROS topics.
    """
    import rospy
    from std_msgs.msg import String

    rospy.init_node('llm_test_publisher', anonymous=True)
    print("\n" + "="*60)
    print("RUNNING ROS TOPIC INTEGRATION TEST")
    print("="*60)
    print("Subscribing to response topics. Press Ctrl+C to exit.")

    # Callbacks to print received messages
    def intent_cb(msg):
        print(f"\n[TOPIC OUTPUT] /smart_cafeteria/intent: '{msg.data}'")
        # Automatically act as the simulated YOLO node
        if msg.data == "detect_object":
            print("  [Simulated Vision Node]: 'detect_object' keyword received! Publishing detections...")
            time.sleep(1.0)
            detections = [{"id": "fried_chicken", "quantity": 1}, {"id": "coke", "quantity": 1}]
            yolo_msg = String()
            yolo_msg.data = json.dumps(detections)
            yolo_pub.publish(yolo_msg)
        
    def bill_cb(msg):
        print(f"\n[TOPIC OUTPUT] /smart_cafeteria/matched_bill:\n{json.dumps(json.loads(msg.data), indent=2)}")
        
    def response_cb(msg):
        print(f"\n[TOPIC OUTPUT] /smart_cafeteria/kiosk_response:\n  '{msg.data}'")

    # Set up subscribers
    rospy.Subscriber('/smart_cafeteria/intent', String, intent_cb)
    rospy.Subscriber('/smart_cafeteria/matched_bill', String, bill_cb)
    rospy.Subscriber('/smart_cafeteria/kiosk_response', String, response_cb)

    # Set up publishers
    speech_pub = rospy.Publisher('/smart_cafeteria/user_speech', String, queue_size=10)
    yolo_pub = rospy.Publisher('/smart_cafeteria/yolo_detections', String, queue_size=10)

    # Wait a bit for connections to register
    time.sleep(2.0)

    while not rospy.is_shutdown():
        print("\nTrigger an event in the flow:")
        print("1. Publish speech: 'start checking out' -> (Triggers scan -> bill -> advice)")
        print("2. Publish speech: 'What is the benefit of changing milk to oatmilk' -> (Triggers Q&A)")
        print("3. Publish speech: 'proceed with payment' -> (Triggers payment success & session clear)")
        print("4. Publish speech: 'cancel that' -> (Triggers cancellation & session clear)")
        print("5. Exit")
        
        try:
            choice = input("Enter choice (1-5): ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == '1':
            msg = String()
            msg.data = "start checking out"
            print(f"Publishing to /smart_cafeteria/user_speech: '{msg.data}'")
            speech_pub.publish(msg)
        elif choice == '2':
            msg = String()
            msg.data = "What is the benefit of changing milk to oatmilk"
            print(f"Publishing to /smart_cafeteria/user_speech: '{msg.data}'")
            speech_pub.publish(msg)
        elif choice == '3':
            msg = String()
            msg.data = "proceed with payment"
            print(f"Publishing to /smart_cafeteria/user_speech: '{msg.data}'")
            speech_pub.publish(msg)
        elif choice == '4':
            msg = String()
            msg.data = "cancel that"
            print(f"Publishing to /smart_cafeteria/user_speech: '{msg.data}'")
            speech_pub.publish(msg)
        elif choice == '5':
            break
        else:
            print("Invalid selection.")

        # Give it a moment to receive response callback printouts
        time.sleep(2.5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Test Script for cafeteria LLM node.")
    parser.add_argument('--local', action='store_true', help="Run local python-only tests (bypasses ROS)")
    parser.add_argument('--offline', action='store_true', help="Force local testing to use offline mock client")
    parser.add_argument('--endpoint', default="", help="Azure AI base URL endpoint")
    parser.add_argument('--key', default="", help="Azure AI key")
    parser.add_argument('--model', default="", help="Azure AI model deployment name")
    
    args, unknown = parser.parse_known_args()
    
    if args.local:
        # Load credentials from env if not passed
        endpoint = args.endpoint or os.environ.get('AZURE_OPENAI_ENDPOINT', '')
        key = args.key or os.environ.get('AZURE_OPENAI_API_KEY', '')
        model = args.model or os.environ.get('AZURE_OPENAI_MODEL', '')
        
        offline = args.offline or not bool(endpoint and key)
        run_local_test(endpoint, key, model, offline)
    else:
        try:
            run_ros_test()
        except ImportError:
            print("Error: 'rospy' module not found. To run without ROS, use: python llm_test_publisher.py --local")

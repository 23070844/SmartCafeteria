#!/usr/bin/env python3
import os
import json
import rospy
from std_msgs.msg import String

# Import the Azure client helper from the same package
try:
    from azure_ai_client import AzureAIFoundryClient
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from azure_ai_client import AzureAIFoundryClient

# Load .env file automatically if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class LLMBrainNode:
    def __init__(self):
        rospy.init_node('llm_brain_node', anonymous=False)
        rospy.loginfo("LLMBrainNode: Initializing...")

        # Load ROS parameters or system environment variables
        endpoint = rospy.get_param('~azure_endpoint', os.environ.get('AZURE_OPENAI_ENDPOINT', ''))
        api_key = rospy.get_param('~azure_key', os.environ.get('AZURE_OPENAI_API_KEY', ''))
        model_name = rospy.get_param('~azure_model', os.environ.get('AZURE_OPENAI_MODEL', ''))
        
        # If credentials are empty, default to offline simulator
        default_offline = not bool(endpoint and api_key)
        self.offline_mode = rospy.get_param('~offline_mode', default_offline)

        # Load Menu Database JSON
        menu_path = rospy.get_param('~menu_path', '')
        if not menu_path:
            try:
                import rospkg
                r = rospkg.RosPack()
                menu_path = os.path.join(r.get_path('smart_cafeteria'), 'src', 'config', 'menu.json')
            except Exception:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                menu_path = os.path.join(script_dir, '..', 'src', 'config', 'menu.json')

        rospy.loginfo(f"LLMBrainNode: Loading menu database from: {menu_path}")
        self.menu_data = self._load_menu(menu_path)

        # Initialize the Azure client
        rospy.loginfo(f"LLMBrainNode: Mode -> {'OFFLINE (SIMULATION)' if self.offline_mode else 'ONLINE'}")
        self.client = AzureAIFoundryClient(
            endpoint=endpoint,
            api_key=api_key,
            model_name=model_name,
            offline_mode=self.offline_mode
        )

        # State Variables
        self.chat_history = []
        self.current_bill_items = []
        self.current_subtotal = 0.0

        # Setup Publishers
        self.intent_pub = rospy.Publisher('/smart_cafeteria/intent', String, queue_size=10)
        self.response_pub = rospy.Publisher('/smart_cafeteria/kiosk_response', String, queue_size=10)
        # self.bill_pub = rospy.Publisher('/smart_cafeteria/matched_bill', String, queue_size=10)  # Commented out: For visual UI receipt rendering

        # Setup Subscribers
        rospy.Subscriber('/smart_cafeteria/user_speech', String, self.speech_callback)
        rospy.Subscriber('/smart_cafeteria/intent', String, self.intent_callback)
        rospy.Subscriber('/smart_cafeteria/yolo_detections', String, self.yolo_callback)

        rospy.loginfo("LLMBrainNode: Setup complete. Waiting for user speech...")

    def _load_menu(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            rospy.logerr(f"LLMBrainNode: Failed to load menu JSON from {path}: {e}")
            return [
                {"id": "fried_chicken", "name": "Fried Chicken", "price": 8.50, "calories": 320, "sugar": "0g", "sodium": "600mg"},
                {"id": "coke", "name": "Coca-Cola", "price": 3.50, "calories": 140, "sugar": "39g", "sodium": "45mg"}
            ]

    def get_system_prompt(self):
        """
        Dynamically constructs the system instructions for conversational Q&A,
        incorporating the current checkout tray status and subtotal.
        """
        prompt = (
            "You are a helpful, friendly corporate wellness self-checkout kiosk assistant.\n"
            f"The cafeteria menu database in JSON is:\n{json.dumps(self.menu_data, indent=2)}\n\n"
        )
        if self.current_bill_items:
            prompt += (
                "The user is in the middle of checking out. They have placed these items on the tray:\n"
                f"{json.dumps(self.current_bill_items, indent=2)}\n"
                f"The calculated subtotal is: RM {self.current_subtotal:.2f}.\n\n"
            )
        else:
            prompt += "The user has no items on the tray yet.\n\n"

        prompt += (
            "Answer their question concisely (1-3 sentences maximum) in a supportive, friendly tone. "
            "If they ask to pay or cancel, instruct them that they can say 'proceed' or 'cancel'. "
            "Keep replies suitable for Text-to-Speech (TTS)."
        )
        return prompt

    def speech_callback(self, msg):
        """
        Triggers when the STT node publishes what the user said.
        Classifies speech into an intent keyword and publishes it.
        """
        user_speech = msg.data.strip()
        if not user_speech:
            return

        rospy.loginfo(f"LLMBrainNode [STT Callback]: User said: '{user_speech}'")
        
        # Call LLM classifier to determine the keyword intent
        intent = self.client.parse_speech_intent(user_speech)
        if not intent:
            rospy.logerr("LLMBrainNode [STT Callback]: Intent classification failed (API or network error).")
            # Notify user of the failure instead of passing wrong/unparsed data
            err_msg = String()
            err_msg.data = "I am sorry, but I am experiencing connection issues. Please try again in a moment."
            self.response_pub.publish(err_msg)
            return

        rospy.loginfo(f"LLMBrainNode [STT Callback]: Parsed intent keyword: '{intent}'")

        # For queries, we append the question to history before publishing intent
        if intent == "chatting":
            self.chat_history.append({"role": "user", "content": user_speech})

        # Publish the intent keyword to trigger the appropriate system flow
        out_msg = String()
        out_msg.data = intent
        self.intent_pub.publish(out_msg)

    def intent_callback(self, msg):
        """
        Triggers when an intent keyword is published.
        """
        intent = msg.data.strip()
        rospy.loginfo(f"LLMBrainNode [Intent Callback]: Received intent: '{intent}'")

        if intent == "chatting":
            # Check if there is anything to answer
            if not self.chat_history or self.chat_history[-1]["role"] != "user":
                rospy.logwarn("LLMBrainNode: Chat intent received but no user message found.")
                return

            # Combine system prompt with chat history and get reply
            full_history = [{"role": "system", "content": self.get_system_prompt()}] + self.chat_history
            reply = self.client.generate_conversational_reply(full_history)
            
            if not reply:
                rospy.logerr("LLMBrainNode [Intent Callback]: Failed to generate conversational response due to API error.")
                # Notify the user of the connection failure instead of responding with empty content
                err_msg = String()
                err_msg.data = "I am sorry, but I am unable to answer questions right now due to a network connection error."
                self.response_pub.publish(err_msg)
                # Rollback the last user speech message so history stays in sync
                if self.chat_history and self.chat_history[-1]["role"] == "user":
                    self.chat_history.pop()
                return

            # Save assistant reply in history
            self.chat_history.append({"role": "assistant", "content": reply})

            # Publish reply to TTS
            out_msg = String()
            out_msg.data = reply
            self.response_pub.publish(out_msg)

        elif intent == "proceed_payment":
            rospy.loginfo("LLMBrainNode: Resetting session due to completed payment.")
            self._reset_session()
            
            out_msg = String()
            out_msg.data = "Payment successful! Thank you for choosing our Smart Cafeteria. Have a wonderful day!"
            self.response_pub.publish(out_msg)

        elif intent == "cancel_transaction":
            rospy.loginfo("LLMBrainNode: Resetting session due to cancellation.")
            self._reset_session()

            out_msg = String()
            out_msg.data = "Checkout cancelled. Your tray has been cleared and reset."
            self.response_pub.publish(out_msg)

    def yolo_callback(self, msg):
        """
        Triggers when the object detection node publishes detected items.
        Expected format: {
            "source": "yolo_vision_node",
            "currency": "RM",
            "total_bill_RM": 2.5,
            "order_details": [{"name": "...", "count": 1, "unit_price_RM": 2.5, "subtotal_RM": 2.5}],
            "unknown_items": [{"name": "...", "count": 1}]
        }
        """
        rospy.loginfo(f"LLMBrainNode [Vision Callback]: Received detections: {msg.data}")
        # --- OLD CODE COMMENTED OFF START ---
        # try:
        #     detections = json.loads(msg.data)
        #     if not isinstance(detections, list):
        #         raise ValueError("YOLO payload must be a JSON array")
        # except Exception as e:
        #     rospy.logwarn(f"LLMBrainNode: Failed to parse YOLO detections: {e}")
        #     return
        # 
        # # Initialize lists for hybrid matching
        # exact_matched_items = []
        # unmatched_raw_detections = []
        # 
        # # Helper maps of menu items for quick exact lookup
        # menu_by_id = {}
        # menu_by_name = {}
        # for item in self.menu_data:
        #     menu_by_id[item["id"].lower()] = item
        #     menu_by_name[item["name"].lower()] = item
        # 
        # # Step 1: Perform exact matching in Python first
        # for detect in detections:
        #     if isinstance(detect, dict):
        #         raw_id = detect.get("id") or detect.get("name") or ""
        #         qty = detect.get("quantity", 1)
        #     else:
        #         raw_id = detect
        #         qty = 1
        #     
        #     raw_id_str = str(raw_id).strip()
        #     raw_id_lower = raw_id_str.lower()
        #     raw_clean = raw_id_lower.replace("_", " ").replace("-", " ")
        #     
        #     # Check for exact ID match or exact Name match
        #     matched_item = None
        #     if raw_id_lower in menu_by_id:
        #         matched_item = menu_by_id[raw_id_lower]
        #     elif raw_clean in menu_by_name:
        #         matched_item = menu_by_name[raw_clean]
        #     
        #     if matched_item:
        #         rospy.loginfo(f"LLMBrainNode: Exact match found in Python for '{raw_id_str}' -> '{matched_item['name']}'")
        #         exact_matched_items.append({
        #             "name": matched_item["name"],
        #             "quantity": qty,
        #             "price": matched_item["price"],
        #             "calories": matched_item["calories"],
        #             "sugar": matched_item["sugar"],
        #             "sodium": matched_item["sodium"]
        #         })
        #     else:
        #         rospy.loginfo(f"LLMBrainNode: No exact match for '{raw_id_str}'. Sending to LLM.")
        #         unmatched_raw_detections.append(detect)
        # 
        # # Step 2: Use LLM ONLY for items that didn't match exactly
        # llm_matched_items = []
        # if unmatched_raw_detections:
        #     rospy.loginfo(f"LLMBrainNode: Requesting LLM matching for {len(unmatched_raw_detections)} items...")
        #     matched_result = self.client.match_price_list(self.menu_data, unmatched_raw_detections)
        #     
        #     # If the matching API returned an error (due to connectivity, auth, or rate limit), we abort!
        #     if "error" in matched_result:
        #         rospy.logerr(f"LLMBrainNode [Vision Callback]: Price matching failed: {matched_result['error']}.")
        #         # Notify user and abort checkout state rather than putting bad / empty matching data in
        #         err_msg = String()
        #         err_msg.data = "Checkout system error: Unable to match items on the tray. Please try again."
        #         self.response_pub.publish(err_msg)
        #         
        #         # Publish cancellation intent to reset other nodes and clear session
        #         self.intent_pub.publish("cancel_transaction")
        #         return
        # 
        #     llm_matched_items = matched_result.get("matched_items", [])
        #     
        #     # Handle any unmatched items reported by the LLM
        #     unmatched_list = matched_result.get("unmatched_items", [])
        #     if unmatched_list:
        #         rospy.logwarn(f"LLMBrainNode: LLM failed to match these items: {unmatched_list}")
        #         for raw_item in unmatched_list:
        #             name = raw_item.get("id") if isinstance(raw_item, dict) else raw_item
        #             llm_matched_items.append({
        #                 "name": f"Unrecognized: {name}",
        #                 "quantity": 1,
        #                 "price": 0.0,
        #                 "calories": 0,
        #                 "sugar": "N/A",
        #                 "sodium": "N/A"
        #             })
        # 
        # # Step 3: Combine exact Python matches with LLM fuzzy matches
        # self.current_bill_items = exact_matched_items + llm_matched_items
        # --- OLD CODE COMMENTED OFF END ---

        try:
            detections = json.loads(msg.data)
            if not isinstance(detections, dict):
                raise ValueError("YOLO payload must be a JSON object")
        except Exception as e:
            rospy.logwarn(f"LLMBrainNode: Failed to parse YOLO detections: {e}")
            return

        order_details = detections.get("order_details", [])
        unknown_items = detections.get("unknown_items", [])

        # Helper to find a matching menu item in self.menu_data
        def find_menu_item(name):
            name_lower = name.lower()
            # Try exact name match
            for item in self.menu_data:
                if item["name"].lower() == name_lower:
                    return item
            # Try fuzzy match (e.g., if one contains the other after normalization)
            for item in self.menu_data:
                menu_name_lower = item["name"].lower()
                menu_id_lower = item["id"].lower()
                norm_name = name_lower.replace(" ", "").replace("-", "").replace("_", "")
                norm_menu_name = menu_name_lower.replace(" ", "").replace("-", "").replace("_", "")
                norm_menu_id = menu_id_lower.replace(" ", "").replace("-", "").replace("_", "")
                if norm_menu_name in norm_name or norm_name in norm_menu_name or norm_menu_id in norm_name:
                    return item
            return None

        # Build current_bill_items
        self.current_bill_items = []

        # Process order_details (known/matched items from YOLO vision node)
        rospy.loginfo(f"LLMBrainNode: Processing {len(order_details)} order_details and {len(unknown_items)} unknown_items.")
        for detail in order_details:
            raw_name = detail.get("name", "")
            qty = detail.get("count", 1)
            price = detail.get("unit_price_RM", 0.0)

            matched = find_menu_item(raw_name)
            if matched:
                rospy.loginfo(f"LLMBrainNode: Menu match found for '{raw_name}' -> '{matched['name']}'")
                self.current_bill_items.append({
                    "name": matched["name"],
                    "quantity": qty,
                    "price": price,
                    "calories": matched.get("calories", 0),
                    "sugar": matched.get("sugar", "N/A"),
                    "sodium": matched.get("sodium", "N/A")
                })
            else:
                rospy.loginfo(f"LLMBrainNode: No menu match for '{raw_name}', using YOLO-provided price.")
                self.current_bill_items.append({
                    "name": raw_name,
                    "quantity": qty,
                    "price": price,
                    "calories": 0,
                    "sugar": "N/A",
                    "sodium": "N/A"
                })

        # Process unknown_items using LLM matching like the older version
        if unknown_items:
            unmatched_raw_detections = []
            for unknown in unknown_items:
                unmatched_raw_detections.append({
                    "name": unknown.get("name", ""),
                    "quantity": unknown.get("count", 1)
                })

            rospy.loginfo(f"LLMBrainNode: Requesting LLM matching for {len(unmatched_raw_detections)} unknown items...")
            matched_result = self.client.match_price_list(self.menu_data, unmatched_raw_detections)
            
            # If the matching API returned an error (due to connectivity, auth, or rate limit), we abort!
            if "error" in matched_result:
                rospy.logerr(f"LLMBrainNode [Vision Callback]: Price matching failed: {matched_result['error']}.")
                # Notify user and abort checkout state rather than putting bad / empty matching data in
                err_msg = String()
                err_msg.data = "Checkout system error: Unable to match items on the tray. Please try again."
                self.response_pub.publish(err_msg)
                
                # Publish cancellation intent to reset other nodes and clear session
                cancel_msg = String()
                cancel_msg.data = "cancel_transaction"
                self.intent_pub.publish(cancel_msg)
                return

            llm_matched_items = matched_result.get("matched_items", [])
            for item in llm_matched_items:
                self.current_bill_items.append({
                    "name": item.get("name", ""),
                    "quantity": item.get("quantity", 1),
                    "price": item.get("price", 0.0),
                    "calories": item.get("calories", 0),
                    "sugar": item.get("sugar", "N/A"),
                    "sodium": item.get("sodium", "N/A")
                })
            
            # Handle any unmatched items reported by the LLM
            unmatched_list = matched_result.get("unmatched_items", [])
            if unmatched_list:
                rospy.logwarn(f"LLMBrainNode: LLM failed to match these items: {unmatched_list}")
                for raw_item in unmatched_list:
                    if isinstance(raw_item, dict):
                        name = raw_item.get("name") or raw_item.get("id") or ""
                        qty = raw_item.get("quantity") or raw_item.get("count") or 1
                    else:
                        name = str(raw_item)
                        qty = 1
                    
                    self.current_bill_items.append({
                        "name": f"Unrecognized: {name}",
                        "quantity": qty,
                        "price": 0.0,
                        "calories": 0,
                        "sugar": "N/A",
                        "sodium": "N/A"
                    })

        # Step 4: Perform Python-based subtotal calculations
        self.current_subtotal = 0.0
        for item in self.current_bill_items:
            qty = item.get("quantity", 1)
            unit_price = item.get("price", 0.0)
            
            total_price = round(unit_price * qty, 2)
            item["total_price"] = total_price
            self.current_subtotal += total_price

        self.current_subtotal = round(self.current_subtotal, 2)
        rospy.loginfo(f"LLMBrainNode: Final Calculated Subtotal (Python): RM {self.current_subtotal:.2f}")

        # Uncomment this block if you integrate a visual kiosk UI
        # bill_msg = String()
        # bill_msg.data = json.dumps({
        #     "items": self.current_bill_items,
        #     "subtotal": self.current_subtotal
        # })
        # self.bill_pub.publish(bill_msg)

        # Call LLM to generate nutritional advice
        advice = self.client.get_nutritional_advice(self.current_bill_items, self.current_subtotal)
        
        # Build the final kiosk output sentence
        combined_response = f"Your total is RM {self.current_subtotal:.2f}. {advice}"
        rospy.loginfo(f"LLMBrainNode: Publishing checkout response: '{combined_response}'")

        # Publish combined bill + advice to TTS
        out_msg = String()
        out_msg.data = combined_response
        self.response_pub.publish(out_msg)

        # Prime the chat history context
        self.chat_history = [
            {"role": "user", "content": "Start checking out my tray."},
            {"role": "assistant", "content": combined_response}
        ]

    def _reset_session(self):
        """
        Clears the conversational chat history and active bill variables.
        """
        self.chat_history = []
        self.current_bill_items = []
        self.current_subtotal = 0.0

if __name__ == '__main__':
    try:
        node = LLMBrainNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass

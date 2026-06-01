#!/usr/bin/env python3
import os
import json
import logging
from openai import OpenAI

class AzureAIFoundryClient:
    def __init__(self, endpoint=None, api_key=None, model_name=None, offline_mode=False):
        """
        Initializes the Microsoft Azure AI Foundry client using the OpenAI compatibility library.
        :param endpoint: The model chat completion API base URL.
        :param api_key: The API key for authorization.
        :param model_name: The deployment model name (e.g. gpt-oss-120b).
        :param offline_mode: If True, operates in simulation mode without sending web requests.
        """
        self.offline_mode = offline_mode
        self.model_name = model_name or os.environ.get("AZURE_OPENAI_MODEL") or "gpt-oss-120b"
        
        # Load API keys from arguments or AZURE_OPENAI_API_KEY environment variable
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.base_url = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        
        if not self.base_url:
            self.base_url = "https://ronotic-resource.openai.azure.com/openai/v1/"

        if not self.offline_mode:
            # In online mode, we strictly validate that the key exists
            if not self.api_key:
                raise ValueError(
                    "[FATAL ERROR] AZURE_OPENAI_API_KEY environment variable or parameter is missing! "
                    "Provide it in your .env file or run with offline_mode:=true."
                )
            if not self.base_url:
                raise ValueError(
                    "[FATAL ERROR] AZURE_OPENAI_ENDPOINT environment variable or parameter is missing!"
                )

            # Standardize base_url for the OpenAI client
            self.base_url = self.base_url.rstrip('/')
            if self.base_url.endswith('/chat/completions'):
                self.base_url = self.base_url[:-17].rstrip('/')
            elif self.base_url.endswith('/chat'):
                self.base_url = self.base_url[:-5].rstrip('/')
                
            logging.info(f"AzureAIFoundryClient: Initializing OpenAI SDK with base_url: {self.base_url}, model: {self.model_name}")
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                raise RuntimeError(f"[FATAL ERROR] Failed to initialize OpenAI client client library: {e}")

    def parse_speech_intent(self, user_speech):
        """
        Analyzes the user's speech transcript and classifies it into one of four keywords.
        Returns exactly one of: 'detect_object', 'chatting', 'proceed_payment', 'cancel_transaction'.
        """
        if self.offline_mode:
            speech_clean = user_speech.lower()
            
            # Simple keyword matching for offline testing
            confirms = ["proceed", "payment", "pay", "yes", "confirm", "charge", "ahead", "looks good", "ok", "fine", "correct"]
            cancels = ["cancel", "stop", "abort", "reset", "clear", "no", "dont", "don't"]
            checkouts = ["checkout", "check out", "start", "scan", "tray", "items", "how much"]

            if any(word in speech_clean for word in checkouts):
                return "detect_object"
            elif any(word in speech_clean for word in confirms):
                return "proceed_payment"
            elif any(word in speech_clean for word in cancels):
                return "cancel_transaction"
            else:
                return "chatting"

        # LLM Prompts for Intent Parsing
        system_prompt = (
            "You are a routing intent classifier for a smart cafeteria checkout kiosk.\n"
            "Analyze the user's speech transcript and classify it into EXACTLY ONE of the following keywords:\n"
            "1. 'detect_object': The user wants to start checking out, wants to pay, wants to scan their tray, or is asking how much their items cost.\n"
            "2. 'chatting': The user is asking a question (e.g. about nutrition, price, ingredients, swaps, greetings, etc.), or the input is conversational.\n"
            "3. 'proceed_payment': The user is ready to pay, says yes to the total, or confirms the transaction.\n"
            "4. 'cancel_transaction': The user wants to cancel the order, stop checkout, reset, or says no.\n\n"
            "Rules:\n"
            "- Output ONLY the exact keyword string (e.g., 'detect_object' or 'chatting').\n"
            "- Do NOT include any markdown, quotation marks, punctuation, or extra sentences."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User speech: '{user_speech}'"}
                ],
                temperature=0.0
            )
            intent = response.choices[0].message.content.strip().lower()
            
            # Clean up the response in case LLM outputs markdown or quotes
            for keyword in ["detect_object", "chatting", "proceed_payment", "cancel_transaction"]:
                if keyword in intent:
                    return keyword
            
            logging.error(f"AzureAIFoundryClient: Invalid intent returned by LLM: '{intent}'")
            return None
        except Exception as e:
            logging.error(f"AzureAIFoundryClient: Intent classification failed: {e}")
            return None

    def get_nutritional_advice(self, matched_items, subtotal):
        """
        Generates healthy/nutritional advice based on purchased items and subtotal.
        """
        if self.offline_mode:
            total_cals = 0
            has_sugary_drink = False
            has_fried = False
            
            for item in matched_items:
                name = item.get("name", "").lower()
                cals = item.get("calories", 0)
                qty = item.get("quantity", 1)
                total_cals += cals * qty
                
                if "coke" in name or "cola" in name or "soda" in name:
                    has_sugary_drink = True
                if "fried" in name or "nasi lemak" in name:
                    has_fried = True

            tips = []
            if total_cals > 600:
                tips.append("Your meal is quite high in calories today.")
            if has_sugary_drink:
                tips.append("Consider swapping the soda for mineral water next time to reduce sugar intake.")
            if has_fried:
                tips.append("Pairing rich dishes with a garden salad is a great way to add fiber and vitamins.")
            
            if not tips:
                return "Your meal choices look highly nutritious! Excellent choices!"
            
            return "Just a friendly wellness tip: " + " ".join(tips)

        # LLM Prompts
        system_prompt = (
            "You are a friendly, encouraging wellness AI nutritionist at a cafeteria self-checkout kiosk.\n"
            "Examine the selected tray items and the subtotal, and generate the final checkout response.\n"
            "Guidelines:\n"
            "1. Start the response with the total price, spelling out the currency in full English words (e.g., 'Your total is three ringgit seventy cents' or 'Your total is twelve ringgit'). Do NOT use 'RM' or numerical digits for the total price.\n"
            "2. Provide a short, personalized wellness/healthy advice tip (2 sentences maximum) based on the items.\n"
            "3. Be warm and positive. Suggest simple improvements (e.g. adding a salad next time, swapping a soda for water).\n"
            "4. Mention specific items they ordered.\n"
            "5. Keep the entire reply suitable for Text-to-Speech (TTS). Must be concise and easy to read aloud. Avoid complex sentences or punctuation that may hinder TTS quality."
        )

        user_prompt = f"Subtotal: RM {subtotal:.2f}\nItems:\n{json.dumps(matched_items, indent=2)}"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AzureAIFoundryClient: Advice generation failed: {e}")
            return "Enjoy your meal! Remember to stay hydrated and balance your plate with fresh greens."

    def generate_conversational_reply(self, chat_history):
        """
        Sends the entire chat history (including system prompt) to the LLM.
        """
        if self.offline_mode:
            # Simulated offline response generator
            last_user_message = ""
            for msg in reversed(chat_history):
                if msg["role"] == "user":
                    last_user_message = msg["content"].lower()
                    break
            
            if "milk" in last_user_message and "oat" in last_user_message:
                return "Swapping milk for oatmilk is great! Oatmilk is naturally dairy-free, lower in saturated fats, and contains beta-glucans which help lower cholesterol. However, check for added sugars!"
            elif "expensive" in last_user_message or "price" in last_user_message or "cost" in last_user_message:
                return "The price is calculated directly from our official menu database. Fried Chicken is RM 8.50 and Coca-Cola is RM 3.50, bringing your total to RM 12.00."
            elif "calorie" in last_user_message or "health" in last_user_message:
                return "Your current tray contains around 460 calories. Coca-Cola accounts for 140 calories, while Fried Chicken has 320 calories. Try adding a side salad next time!"
            else:
                return "I can help you adjust your order, answer nutritional questions, or proceed to payment. Let me know what you would like to do!"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=chat_history,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AzureAIFoundryClient: Conversation reply failed: {e}")
            return None

    def match_price_list(self, menu_data, raw_detected_items):
        """
        Matches YOLO detected items to the official menu items using LLM.
        """
        if self.offline_mode:
            # Simulate matching logic offline
            matched = []
            unmatched = []
            menu_items_map = {item["id"]: item for item in menu_data}
            
            for raw_item in raw_detected_items:
                if isinstance(raw_item, dict):
                    raw_id = raw_item.get("id") or raw_item.get("name", "")
                    qty = raw_item.get("quantity", 1)
                else:
                    raw_id = raw_item
                    qty = 1
                
                raw_clean = raw_id.lower().replace("_", " ").replace("-", " ")
                matched_any = False
                
                # Check for direct or fuzzy matches in name or id
                for item_id, item in menu_items_map.items():
                    name_clean = item["name"].lower()
                    if raw_clean in name_clean or name_clean in raw_clean or raw_clean in item_id:
                        matched.append({
                            "name": item["name"],
                            "quantity": qty,
                            "price": item["price"],
                            "calories": item["calories"],
                            "sugar": item["sugar"],
                            "sodium": item["sodium"]
                        })
                        matched_any = True
                        break
                
                if not matched_any:
                    unmatched.append(raw_id)

            return {
                "matched_items": matched,
                "unmatched_items": unmatched
            }

        # LLM Prompts
        system_prompt = (
            "You are an intelligent price matcher for a cafeteria self-checkout kiosk.\n"
            "You are provided with a menu database of items in JSON format. Match the list of raw detected items "
            "from the YOLO vision system to the official menu database items.\n"
            "Rules:\n"
            "1. Match each raw item (can be an ID or string or object) to the single most relevant official menu item (e.g. 'coke' matches 'Coca-Cola', 'chicken' matches 'Fried Chicken').\n"
            "2. Keep the quantity for each matched item as provided in the detections (default is 1).\n"
            "3. Look up and output the official name, quantity, unit price (under 'price'), calories, sugar, and sodium for each matched item.\n"
            "4. Unmatched items should be placed in the 'unmatched_items' list.\n"
            "5. Return ONLY a valid JSON object in the following format (do not output any markdown blocks or quotes):\n"
            "{\n"
            "  \"matched_items\": [\n"
            "    {\"name\": \"Official Name\", \"quantity\": 1, \"price\": 8.50, \"calories\": 320, \"sugar\": \"0g\", \"sodium\": \"600mg\"}\n"
            "  ],\n"
            "  \"unmatched_items\": [\"raw_item_name\"]\n"
            "}"
        )

        user_prompt = f"Menu Database:\n{json.dumps(menu_data, indent=2)}\n\nRaw Detected Items:\n{json.dumps(raw_detected_items)}"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                llm_response = response.choices[0].message.content.strip()
            except Exception as e:
                logging.warning(f"AzureAIFoundryClient: Calling LLM with json response_format failed ({e}). Retrying without response_format.")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1
                )
                llm_response = response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AzureAIFoundryClient: LLM call failed: {e}")
            llm_response = None

        if not llm_response:
            return {"error": "API failed", "matched_items": []}

        try:
            if llm_response.startswith("```json"):
                llm_response = llm_response.split("```json")[1].split("```")[0].strip()
            elif llm_response.startswith("```"):
                llm_response = llm_response.split("```")[1].split("```")[0].strip()
            return json.loads(llm_response)
        except Exception as e:
            logging.error(f"AzureAIFoundryClient: Failed to parse price match JSON: {e}. Raw: {llm_response}")
            return {"error": "Invalid JSON response from LLM", "matched_items": []}

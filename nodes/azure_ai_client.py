#!/usr/bin/env python3
import os
import json
import logging
from openai import OpenAI

class AzureAIFoundryClient:
    def __init__(self, endpoint=None, api_key=None, model_name=None):
        """
        Initializes the Microsoft Azure AI Foundry client using the OpenAI compatibility library.
        :param endpoint: The model chat completion API base URL.
        :param api_key: The API key for authorization.
        :param model_name: The deployment model name (e.g. gpt-oss-120b).
        """
        self.model_name = model_name or os.environ.get("AZURE_OPENAI_MODEL") or "gpt-oss-120b"
        
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.base_url = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        
        if not self.api_key:
            raise ValueError(
                "[FATAL ERROR] AZURE_OPENAI_API_KEY environment variable or parameter is missing! "
                "Provide it in your .env file."
            )
        if not self.base_url:
            raise ValueError(
                "[FATAL ERROR] AZURE_OPENAI_ENDPOINT environment variable or parameter is missing!"
            )

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

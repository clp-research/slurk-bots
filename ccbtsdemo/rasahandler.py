import logging
import random
import requests
import uuid

import asyncio
import time

class RasaHandler:
    def __init__(self, rasa_url, model_path):
        # Load the Rasa NLU model: model_path = "models/20240619-113705-chalky-hybrid.tar.gz"
        self.rasa_url = rasa_url
        self.model_path = model_path

        if not self.rasa_url:
            from rasa.core.agent import Agent
            from rasa.core.http_interpreter import RasaNLUHttpInterpreter
            from rasa.shared.utils.io import json_to_string

            self.agent = Agent.load(model_path)

    def call_rasa_with_retry(self, max_retries=5, delay=2):
        for attempt in range(max_retries):
            try:
                response = requests.post(f"{self.rasa_url}/model/parse", json={"text": "Hello"}, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error("Max retries reached. RASA server is not responding.")
                    raise e

    def test_rasa_server(self):
        try:
            response = self.call_rasa_with_retry()
            return True
        except:
            return False


    def parse(self, utterance):
        daresponse = {"utterance": utterance}

        if self.rasa_url:
            endpoint = f"{self.rasa_url}/model/parse"
            payload = {"text": utterance}

            try:
                result = requests.post(endpoint, json=payload, timeout=30)
                result = result.json()
            except requests.exceptions.RequestException as e:
                logging.error(f"Error connecting to RASA: {e}")

        #logging.debug(f"Received response from Rasa NLU: {result}")

        daresponse["intent"] = {'name': result["intent"]["name"].upper(), 'confidence': round(result["intent"]["confidence"], 2)}
        daresponse["entities"] = result["entities"]

        return daresponse
    
    def generate(self, utterance, previntent = None):
        daresponse = {"utterance": utterance}

        '''
        if self.rasa_url:
            endpoint = f"{self.rasa_url}/webhooks/rest/webhook"
            payload = {
                "sender": str(uuid.uuid4()),  # Generate a unique ID if not provided,
                "message": utterance
            }

            result = requests.post(endpoint, json=payload)
            result = result.json()
        else:
            result = asyncio.run(self.agent.handle_text(utterance))

        #logging.debug(f"Received response from Rasa NLU: {result}")

        if result:
            daresponse["output"] = result[0]["text"]
        else:
            logging.debug(f"Generating custom response: previntent = {previntent}")

            if previntent in ["TRANSLATE", "UNDO", "SAVE-SKILL", "REPEAT-SKILL", "GREET", "GOODBYE"]:
                daresponse["output"] = "Processing..."
            else:
                daresponse["output"] = "Sorry, I don't understand. Can you please repeat?"
        daresponse["rasa_result"] = result
        '''
        if previntent == "TRANSLATE":
            daresponse["output"] = random.choice(["Okay", "Processing translation...", "On it!"])
        elif previntent == "SAVE-SKILL":
            daresponse["output"] = random.choice(["Okay", "Saving skill...", "On it!"])
        elif previntent == "REPEAT-SKILL":
            daresponse["output"] = random.choice(["Okay", "Repeating skill...", "On it!"])
        elif previntent == "UNDO":
            daresponse["output"] = random.choice(["Okay", "Undoing...", "On it!"])
        elif previntent == "GREET":
            daresponse["output"] = random.choice(["Hello!", "Hi!", "Hey! What are we building today?", "Hi! What can I do for you today?"])
        elif previntent == "GOODBYE":
            daresponse["output"] = random.choice(["Goodbye!", "See you later!", "Bye! Have a great day!", "It was nice collaborating with you. Goodbye!"])
        else:
            daresponse["output"] = "Sorry, I don't understand. Can you please repeat"
        return daresponse

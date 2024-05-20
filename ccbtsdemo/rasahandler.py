import logging
import asyncio


from rasa.core.agent import Agent
from rasa.core.http_interpreter import RasaNLUHttpInterpreter
from rasa.shared.utils.io import json_to_string

from pathlib import Path


ROOT = Path(__file__).parent.resolve()
RELATED_FOLDER_PATH = Path(
    f"{ROOT}/data/models/"
)

class RasaHandler:
    def __init__(self):
        logging.debug(f"Loading Rasa NLU model from {RELATED_FOLDER_PATH}")
        self.agent = Agent.load(f"{RELATED_FOLDER_PATH}/20240514-061034-magenta-dither.tar.gz")
        logging.debug(f"Loaded Rasa NLU model from {RELATED_FOLDER_PATH}")

    def parse(self, utterance):
        daresponse = {"utterance": utterance}
        result = asyncio.run(self.agent.parse_message(utterance))
        logging.debug(f"Received response from Rasa NLU: {result['intent']}")
        daresponse["dialogue_act"] = result["intent"]["name"].upper()
        return daresponse

    
    def generate(self, utterance):
        daresponse = {"utterance": utterance}        
        result = asyncio.run(self.agent.handle_text(utterance))
        logging.debug(f"Received response from Rasa NLU: {result}")
        if result and result[0] and "text" in result[0]:
            daresponse["response"] = result[0]["text"]
        else:
            daresponse["response"] = "Sorry, I don't understand. Can you please repeat?"
        return daresponse

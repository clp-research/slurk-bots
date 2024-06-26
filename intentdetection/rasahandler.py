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


class RasaModelLoader:
    _model = None

    @classmethod
    def get_model(cls, model_path):
        if cls._model is None:
            cls._model = Agent.load(model_path)
        return cls._model

class RasaHandler:
    def __init__(self):
        logging.debug(f"Loading Rasa NLU model from {RELATED_FOLDER_PATH}")
        self.agent = Agent.load(f"{RELATED_FOLDER_PATH}/model.tar.gz")
        logging.debug(f"Loaded Rasa NLU model")

    def parse(self, utterance):
        daresponse = {"utterance": utterance}
        result = asyncio.run(self.agent.parse_message(utterance))
        #logging.debug(f"Received response from Rasa NLU: {result['intent']}")
        extracted_entities = []
        for entity in result["entities"]:
            entities = {}
            entities["name"] = entity["entity"]
            entities["value"] = entity["value"]
            extracted_entities.append(entities)

        daresponse["dialogue_act"] = {"name": result["intent"]["name"].upper(),
                                      "confidence": round(result["intent"]["confidence"], 2),
                                      "entities": extracted_entities}
        #daresponse["rasa_result"] = result
        return daresponse
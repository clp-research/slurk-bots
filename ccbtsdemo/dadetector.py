import re
import logging
import json

from .rasahandler import RasaHandler
from .getllmresponse import PromptLLM


class DADetector:
    def __init__(self, rasa_handler, llm_model):
        self.rhandler = rasa_handler
        self.pllm = PromptLLM()
        self.prompt = {}
        self.response = {}
        self.model = llm_model


    def reset(self, prompt_type=None):
        if not prompt_type:
            self.prompt = {}
            self.response = {}
            return
        self.prompt[prompt_type] = []
        self.response[prompt_type] = None

    def run(self, utterance):
        return self.rhandler.parse(utterance)
    
    def _cleanup_response(self, response, response_type):
        if not response or response_type != "json":
            return response
        
        if "```json" in response:
            response = response.replace("```json", "").replace("```", "").strip()

        elif "```" in response:
            response = response.replace("```", "").strip()        
            
        response = response.replace("\n", "")

        json_match = re.search(r'(\{.*\})', response, re.DOTALL)

        if json_match:
            extracted_text = json_match.group(0)
            response = json.loads(extracted_text)

        return response        

    
    def run_llm(self, utterance, prompt_type, error=None):

        if prompt_type not in self.prompt:
            self.prompt[prompt_type] = []
            self.response[prompt_type] = None

        reponse_type = None

        if prompt_type == "intent-detection":
            self.pllm.get_intent_prompt(utterance, self.prompt[prompt_type], self.response[prompt_type], error)
            reponse_type = "json"

        model_response = self.pllm.generate(self.model, self.prompt[prompt_type])

        self.response[prompt_type] = self._cleanup_response(model_response, reponse_type)

        daresponse = {"utterance": utterance}
        daresponse["intent"] = {'name': self.response[prompt_type]["Intent"].upper(), 'confidence': round(self.response[prompt_type]["Confidence"], 2)}
        daresponse["entities"] = self.response[prompt_type]["Slots"]

        return daresponse



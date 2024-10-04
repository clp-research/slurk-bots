import sys
import argparse
import importlib
import logging
import json
import re

from pathlib import Path

from .dadetector import DADetector
from .dtranslator import DialogueTranslator
from .csimulator import CodeSimulator
from .rgenerator import ResponseGenerator
from .rasahandler import RasaHandler

ROOT = Path(__file__).parent.resolve()
RELATED_FILE_PATH = Path(
    f"{ROOT}"
)

def setup_logging():
    # Configure the root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",  # "%(filename)s: %(message)s",  #'%(name)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Optionally, set levels for specific loggers
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("httpcore").setLevel(logging.ERROR)
    logging.getLogger("connect_tcp").setLevel(logging.ERROR)
    logging.getLogger("send_request_headers").setLevel(logging.ERROR)
    logging.getLogger("receive_response_headers").setLevel(logging.ERROR)
    logging.getLogger("receive_response_body").setLevel(logging.ERROR)
    logging.getLogger("response_closed").setLevel(logging.ERROR)
    logging.getLogger("matplotlib").setLevel(logging.ERROR)
    logging.getLogger("openai").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("PIL").setLevel(logging.ERROR)
    logging.getLogger("rasahandler").setLevel(logging.INFO)


class DialogueManager:
    def __init__(self):
        self.config = self.readfile(f"{RELATED_FILE_PATH}/config.json")
        self.gridsize = self.config["gridsize"]
        self.rhandler = RasaHandler(self.config["rasa_url"], self.config["rasa_model_path"])
        self.dad = DADetector(self.rhandler, self.config["llm_name"])
        self.dtranslator = DialogueTranslator(self.config["llm_name"])
        self.csimulator = CodeSimulator(self.gridsize["width"], self.gridsize["height"])
        self.rgen = ResponseGenerator(self.rhandler)

        self.realroboarm = self.config["use_ur5arm"]
        self.pbsimulation = self.config["use_pybullet_simulation"]

        # Conditionally import modules based on the argument
        if self.pbsimulation:
            #PBInterface = importlib.import_module(".pbrobotinterface").PBInterface
            #SimulGrounding = importlib.import_module(".robosimulgrounding").SimulGrounding
            from .pbrobotinterface import PBInterface
            from .robosimulgrounding import SimulGrounding

            self.pbrobot = PBInterface(self.config["pybullet"]["base_url"])
            self.pbrobot.initialize_simulation()
            self.pbrobot.loadshapes()
            self.simulground = SimulGrounding(self.gridsize["width"], self.gridsize["height"])            

        if self.realroboarm:
            from .actiongrounding import ActionGrounding
            #ActionGrounding = importlib.import_module(".actiongrounding").ActionGrounding
            self.aground = ActionGrounding()

        logging.debug("Dialogue Manager Initialized")

    def readfile(self, filename):
        with open(filename, "r") as file:
            return json.load(file)

    def _getentities(self, entities):
        entity_extract = {}
        logging.debug(f"Entities: {entities}")
        for entity in entities:
            if "entity" in entity:
                if entity["entity"] == "skill_name":
                    entity_extract["name"] = "skill_name"
                    entity_extract["value"] = entity["value"]
                    break
            elif entity == "skill-name":
                entity_extract["name"] = "skill_name"
                entity_extract["value"] = entity["skill-name"]
                break
        return entity_extract
    
    def _getentities_using_regex(self, instruction):
        #pattern = r'(k\d+b?\d*|[a-z]+\d+(?:[a-z]+\d+)*-[a-z]+|[a-z]+\d+(?:[a-z]+\d+)*|[a-z]+-[a-z]+)'
        pattern = r'(k\d+b?\d*|[a-z]+\d+(?:[a-z]+\d+)*_[a-z]+|[a-z]+\d+(?:[a-z]+\d+)*|[a-z]+_[a-z]+)'

        extracted = None
        matches = re.findall(pattern, instruction)
        if matches:
            extracted = ', '.join(matches)
            logging.debug(f"Extracted: {extracted}")
        else:
            logging.debug("No match found for entity extraction")
        return extracted   


    def _handle_no_entity(self, daresponse, prev_intent):
        logging.error(
            f"Failure in extracting the skill name, available entities are: {daresponse['entities']}"
        )
        rgenop = self.rgen.handleerror("No skill name provided.")

        return rgenop, None

    def _gen_abstract_function(self, entity_extract, skill_filename):
        skill_code = self.csimulator.getskill(skill_filename)
        logging.debug(skill_code)

        skill_instruction = (
            f"These are the instructions to build a {entity_extract['value']} object."
        )
        abstract_function = self.dtranslator.run(
            "abstract-skill", None, skill_instruction, skill_code
        )
        logging.debug(abstract_function)

        if "Function" in abstract_function:
            abstract_function = abstract_function.split("Function")[1]
            abstract_function = " ".join(abstract_function)
            logging.debug(abstract_function)

        abstract_func_filename = f"{entity_extract['value']}_abstract.py"
        self.csimulator.save_abstract_function(
            abstract_func_filename, abstract_function
        )
        self.dtranslator.reset("abstract-skill")
        return abstract_func_filename

    def _run_virtual_simulation(
        self, prompt_type, daresponse, prev_intent, skill_name, skill_code
    ):
        retry = 0
        simulerror = None

        while retry < 3:
            model_response = self.dtranslator.run(
                prompt_type, daresponse["utterance"], skill_name, skill_code, simulerror
            )
            logging.debug(f"Repeat Code: {model_response}")

            try:
                if prompt_type == "translate":
                    save_filename = self.csimulator.run(model_response)
                    result = {
                        "utterance": daresponse["utterance"],
                        "dialogue_act": prev_intent,
                        "output": save_filename,
                        "code": model_response,
                    }
                    return result  # save_filename

                else:
                    self.csimulator.repeat_run(skill_code, model_response)
                    self.dtranslator.reset(prompt_type)
                break
            except Exception as error:
                # TODO: Handle exceptions - reprompt the model with the errors
                logging.error(f"Error: {str(type(error)) + str(error)}")
                simulerror = str(type(error)) + str(error)

                retry += 1

        if retry == 3:
            rgenop = self.rgen.handleerror(simulerror)
            logging.error(rgenop)
            result = {
                "utterance": daresponse["utterance"],
                "dialogue_act": prev_intent,
                "output": rgenop,
                "code": None,
            }
            return result

    def _prepare_result(self, utterance, daresponse, botresponse):

        if daresponse["entities"] and isinstance(daresponse["entities"], dict):
            daresponse["entities"] = [daresponse["entities"]]

        result = {
            "utterance": utterance,
            "dialogue_act": daresponse["intent"],
            "detectionresponse": daresponse,
            "botresponse": botresponse,
            "entities": daresponse["entities"],
        }
        return result
    
    def reset(self):
        self.dad.reset()
        self.dtranslator.reset()
        self.csimulator.reset()

    def getsimulationtype(self):
        if self.pbsimulation:
            return "pybullet"
        elif self.realroboarm:
            return "realarm"
        else:
            return "virtual"
        
    def israsaready(self):
        counter = 0
        while counter < 2:
            try:
                response = self.rhandler.call_rasa_with_retry()
                return True
            except:
                counter += 1
        return False
    
    def setllmmodel(self, model):
        self.dtranslator.setllmmodel(model)
    
    def handleintent(self, daresponse):
        if daresponse["intent"]["confidence"] < self.config["intent_confidence"]:
            return "low-confidence", None

        intent_handlers = {
                    "TRANSLATE": self._handle_translate,
                    "UNDO": self._confirm_undo,
                    "GREET": self._handle_others,
                    "GOODBYE": self._handle_others,
                    "SAVE-SKILL": self._handle_save_skill,
                    "REPEAT-SKILL": self._handle_repeat_skill,
                    "CLEAR": self._handleclear,
                }
        handler = intent_handlers.get(daresponse["intent"]["name"])
        if handler:
            return handler(daresponse)        
        else:
            return None, None
    

    def _handle_translate(self, daresponse):
        prev_intent = daresponse["intent"]
        retry = 0
        simulerror = None
        while retry < self.config["llm_retry_translate_error"]:
            if retry:
                logging.error(f"Error in Instruction Translate: {simulerror}, Retrying")

            dtresponse = self.dtranslator.run(
                "translate", daresponse["utterance"], None, None, simulerror
            )
            logging.debug(f"Translated Code:\n{dtresponse}")
            if dtresponse:
                if "for" in dtresponse:
                    dtresponse = [dtresponse.strip()]
                else:
                    dtresponse = dtresponse.strip().split("\n")
                try:
                    save_filename = self.csimulator.run(dtresponse)
                    return save_filename, dtresponse

                except Exception as error:
                    # TODO: Handle exceptions - reprompt the model with the errors
                    logging.error(f"Error: {error}, {type(error)}, {str(error)}")
                    simulerror = str(type(error)).replace("<", "&lt;").replace(">", "&gt;") + " " + str(error).replace("<", "&lt;").replace(">", "&gt;")

                    retry += 1

        rgenop = f"Failure in executing the translated code.<br>{simulerror}<br>Please try again"#self.rgen.handleerror(simulerror)
        logging.error(
            f"Error in executing the LLM generated code"#: Response from RGen: {rgenop}"
        )
        return rgenop, dtresponse

    def _confirm_undo(self, daresponse):
        #return self.csimulator.undo()
        #Get the confirmation from the user before doing undo
        return "Undoing the last action", None
    
    def handle_undo(self):
        return self.csimulator.undo()
        

    def _handle_save_skill(self, daresponse):
        prev_intent = daresponse["intent"]
        entity_extract = self._getentities(daresponse["entities"])
        # if not entity_value:
        # DM should check if it is available from the context, if not generate a response asking for the skill name
        if not entity_extract:
            extracted = self._getentities_using_regex(daresponse["utterance"])
            if extracted:
                entity_extract = {"value": extracted}
            else:
                return self._handle_no_entity(daresponse, prev_intent)

        skill_filename = f"{entity_extract['value']}.py"
        logging.debug(f"Extracted the skillname: {skill_filename}")
        save_status = self.csimulator.save(skill_filename)
        if save_status:
            # Check how to abstract this skill
            abstract_func_filename = self._gen_abstract_function(
                entity_extract, skill_filename
            )
            # If we return abstract_func_filename -> it may unnecessarily expose the internal file structure
            return skill_filename, None
        else:
            return "No active code available for saving. Try later", None

    def _handle_repeat_skill(self, daresponse):
        prev_intent = daresponse["intent"]

        entity_extract = self._getentities(daresponse["entities"])
        if not entity_extract:
            extracted = self._getentities_using_regex(daresponse["utterance"])
            if extracted:
                entity_extract = {"value": extracted}
            else:            
                return self._handle_no_entity(daresponse, prev_intent)

        skill_filename = f"{entity_extract['value']}_abstract.py"
        logging.debug(f"Retrieving skill with the filename: {skill_filename}")
        skill_code = self.csimulator.getskill(f"{skill_filename}")
        logging.debug(f"Retrieved Skill Code: {skill_code}")

        if skill_code is None:
            return f"No skill found with the name: {entity_extract['value']}",None

        retry = 0
        simulerror = None
        while retry < self.config["llm_retry_repeat_error"]:
            repeat_code = self.dtranslator.run(
                "repeat-skill",
                daresponse["utterance"],
                entity_extract["value"],
                skill_code,
                simulerror,
            )
            logging.debug(f"Repeat Code: {repeat_code}")

            try:
                save_filename = self.csimulator.repeat_run(skill_code, repeat_code)
                self.dtranslator.reset("repeat-skill")
                return save_filename, None
            except Exception as error:
                # TODO: Handle exceptions - reprompt the model with the errors
                logging.error(f"Error: {str(type(error)) + str(error)}")
                simulerror = str(type(error)).replace("<", "&lt;").replace(">", "&gt;") + " " + str(error).replace("<", "&lt;").replace(">", "&gt;")

                retry += 1

        self.dtranslator.reset("repeat-skill")
        rgenop = f"Failure in executing the translated code.<br>{simulerror}<br>Please try again."#self.rgen.handleerror(simulerror)
        logging.error(rgenop)
        return rgenop, skill_code

    def _handle_others(self, daresponse):
        genoutput = self.rgen.generate(daresponse["utterance"])
        # logging.debug(genoutput["output"])
        return genoutput["output"], None

    def _handleclear(self, daresponse):

        return "cleared the grid", None

    def run(self, utterance):
        if utterance.lower() == "clear":
            self.dad.reset()
            self.dtranslator.reset()
            self.csimulator.reset()
            daresponse = {"intent": {"name": "CLEAR", "confidence": 1.0}, "entities": None}
            return self._prepare_result(utterance, daresponse, "cleared the grid")
        '''
        if utterance.lower() == "show in simulation":
            daresponse = {"intent": {"name": "showrobosimulation", "confidence": 1.0}, "entities": None}}
            self.pbrobot.perform_pick_and_place()
            return self._prepare_result(utterance, daresponse, "updated the simulation")
        
        '''
        if "show me" in utterance.lower():
            code_list = self.csimulator.get_current_world_code()
            logging.debug(f"Got the current world code: {code_list}")
            daresponse = {"intent": {"name": None, "codenfidence": 1.0}, "entities": None}
            if self.pbsimulation:
                daresponse["intent"]["name"] = "SHOW_PBSIMULATION"
                self.pbrobot.perform_pick_and_place(code_list)
            elif self.realroboarm:
                daresponse["intent"]["name"] = "SHOW_ROBOREAL"
                self.aground.perform_pick_and_place(code_list)
            else:
                daresponse["intent"]["name"] = "SHOW_VSIMULATION"

            return self._prepare_result(utterance, daresponse, "Updated the simulation")
        
        if any(x in utterance.lower() for x in ["remove", "undo", "revert"]):
            daresponse = {"intent": {"name": "UNDO", "confidence": 1.0}, "entities": None}
            return self._prepare_result(utterance, daresponse, "Received the undo command")

        daresponse = self.dad.run(utterance)
        logging.debug(f"DA Response: {daresponse}")

        checkllmresponse = False
        if daresponse["intent"]["confidence"] < self.config["intent_confidence"]:
            logging.info(
                f"Confidence is low: {daresponse['intent']['confidence']} for intent detection, Checking with LLM"
            )

            checkllmresponse = True

        if not checkllmresponse and daresponse["intent"]["name"] in ["SAVE-SKILL", "REPEAT-SKILL"] and not daresponse["entities"]:
            logging.info(
                f"No entities extracted using Rasa Model, Checking with LLM"
            )

            checkllmresponse = True

        if checkllmresponse:
            daresponse = self.dad.run_llm(utterance, "intent-detection")
            logging.debug(f"LLM Response: {daresponse}")
            self.dad.reset("intent-detection")

            if daresponse["intent"]["confidence"] < self.config["intent_confidence"]:
                logging.debug(
                    f"Confidence is still low: {daresponse['intent']['confidence']} with LLM, Reprompting the user"
                )

                return self._prepare_result(utterance, daresponse, "Sorry, I don't understand. Can you please repeat?"
                )

        genresponse = self.rgen.generate(utterance, daresponse["intent"]["name"])
        logging.info(f"Genresponse: {genresponse}")

        return self._prepare_result(utterance, daresponse, genresponse["output"],
        )
    
    def showpbsimulation(self, code):
        if self.pbsimulation:
            self.pbrobot.perform_pick_and_place(code)
        else:
            logging.error("Pybullet Simualtion is not active - Ignoring the request")

    def showrealarm(self, code):
        if self.realroboarm:
            self.aground.perform_pick_and_place(code)
        else:
            logging.error("Real Roboarm is not active - Ignoring the request")

    def process(self):
        while True:
            utterance = input("You: ")
            if utterance.lower() == "exit":
                break

            result = self.run(utterance)
            if result:
                logging.debug(
                    f"Intent Output: {result['dialogue_act'], result['entities']}"
                )

                if result["dialogue_act"]["name"].lower() in ["translate"]:
                    output = f"Running code: {result['code']}"

                    if self.pbsimulation:
                        target_positions = self.simulground.get_positions(result["code"])
                        logging.debug(f"Target positions: {target_positions}")
                        self.ur5arm.pick_and_place(target_positions)

                elif result["dialogue_act"]["name"].lower() in ["undo"]:
                    if result["code"]:
                        output = f"Undoing code: {result['code']}"
                    else:
                        output = "Grid is empty. Nothing to UNDO"

                else:
                    output = result["output"]
            else:
                output = None
            logging.info(f"Bot: {output}")


if __name__ == "__main__":
    #setup_logging()
    dm = DialogueManager()
    dm.process()

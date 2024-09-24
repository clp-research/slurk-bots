import sys
import argparse
import importlib
import logging
import json

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
        for entity in entities:
            if entity["entity"] == "skill_name":
                entity_extract["name"] = "skill_name"
                entity_extract["value"] = entity["value"]
                break

        return entity_extract

    def _handle_no_entity(self, daresponse, prev_intent):
        logging.error(
            f"Failure in extracting the skill name, available entities are: {daresponse['entities']}"
        )
        result = {
            "utterance": daresponse["utterance"],
            "dialogue_act": prev_intent,
            "output": self.rgen.handleerror("No skill name provided."),
        }
        return result

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

    def _prepare_result(self, utterance, da_act, output, code, dllmresponse, entities=None):
        result = {
            "utterance": utterance,
            "dialogue_act": da_act,
            "output": output,
            "code": code,
            "llmresponse": dllmresponse,
            "entities": entities,
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
            logging.debug(f"Translate Code: {dtresponse}")
            if dtresponse:
                dtresponse = dtresponse.strip().split("\n")
                try:
                    save_filename = self.csimulator.run(dtresponse)
                    return self._prepare_result(
                        daresponse["utterance"],
                        prev_intent,
                        save_filename,
                        dtresponse,
                        daresponse,
                    )

                except Exception as error:
                    # TODO: Handle exceptions - reprompt the model with the errors
                    logging.error(f"Error: {error}, {type(error)}, {str(error)}")
                    simulerror = str(type(error)) + str(error)

                    retry += 1

        rgenop = "Failure in executing the LLM generated code. Please try again."#self.rgen.handleerror(simulerror)
        logging.error(
            f"Error in executing the LLM generated code (for 3 times)"#: Response from RGen: {rgenop}"
        )
        return self._prepare_result(
            daresponse["utterance"], prev_intent, rgenop, None, daresponse
        )

    def _handle_undo(self, daresponse):
        prev_intent = daresponse["intent"]
        output_filename, undo_code = self.csimulator.undo()
        return self._prepare_result(
            daresponse["utterance"],
            prev_intent,
            output_filename,
            undo_code,
            daresponse,
        )

    def _handle_save_skill(self, daresponse):
        prev_intent = daresponse["intent"]
        entity_extract = self._getentities(daresponse["entities"])
        # if not entity_value:
        # DM should check if it is available from the context, if not generate a response asking for the skill name
        if not entity_extract:
            return self._handle_no_entity(daresponse, prev_intent)

        skill_filename = f"{entity_extract['value']}.py"
        logging.debug(f"Extracted the skillname: {skill_filename}")
        save_status = self.csimulator.save(skill_filename)
        if save_status:
            # Check how to abstract this skill
            abstract_func_filename = self._gen_abstract_function(
                entity_extract, skill_filename
            )

            return self._prepare_result(
                daresponse["utterance"],
                prev_intent,
                f"Saved the code in: {abstract_func_filename}",
                None,
                daresponse,
                entity_extract,
            )
        else:
            return self._prepare_result(
                daresponse["utterance"],
                prev_intent,
                "No code to save",
                None,
                daresponse,
            )

    def _handle_repeat_skill(self, daresponse):
        prev_intent = daresponse["intent"]

        entity_extract = self._getentities(daresponse["entities"])
        if not entity_extract:
            return self._handle_no_entity(daresponse, prev_intent)

        skill_filename = f"{entity_extract['value']}_abstract.py"
        logging.debug(f"Retrieving skill with the filename: {skill_filename}")
        skill_code = self.csimulator.getskill(f"{skill_filename}")
        logging.debug(f"Retrieved Skill Code: {skill_code}")

        if skill_code is None:
            return self._prepare_result(
                daresponse["utterance"],
                prev_intent,
                f"No skill found with the name: {entity_extract['value']}",
                None,
                daresponse,
            )

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
                self.csimulator.repeat_run(skill_code, repeat_code)
                self.dtranslator.reset("repeat-skill")
                return self._prepare_result(
                    daresponse["utterance"],
                    prev_intent,
                    f"Repeated the skill: {entity_extract['value']}",
                    None,
                    daresponse,
                )
            except Exception as error:
                # TODO: Handle exceptions - reprompt the model with the errors
                logging.error(f"Error: {str(type(error)) + str(error)}")
                simulerror = str(type(error)) + str(error)

                retry += 1

        self.dtranslator.reset("repeat-skill")
        rgenop = "Failure in executing the LLM generated code. Please try again."#self.rgen.handleerror(simulerror)
        logging.error(rgenop)
        return self._prepare_result(
            daresponse["utterance"], prev_intent, rgenop, None, daresponse
        )

    def _handle_others(self, daresponse):
        prev_intent = daresponse["intent"]
        genoutput = self.rgen.generate(daresponse["utterance"])
        # logging.debug(genoutput["output"])
        return self._prepare_result(
            daresponse["utterance"],
            prev_intent,
            genoutput["output"],
            None,
            daresponse,
        )

    def _handle_ground(self, daresponse):
        prev_intent = daresponse["intent"]
        logging.debug("Moving the action to roboarm!")
        result = {
            "utterance": daresponse["utterance"],
            "dialogue_act": prev_intent,
            "output": "Moving the action to roboarm!",
            "code": None,
            "llmresponse": daresponse,
        }

    def run(self, utterance):
        if utterance.lower() == "clear":
            self.dad.reset()
            self.dtranslator.reset()
            self.csimulator.reset()
            return self._prepare_result(utterance, {"name": "clear", "confidence": 1.0}, "cleared the grid", None, None)
        '''
        if utterance.lower() == "show in simulation":
            daresponse = {"rasa_result": { "intent": "robosimulation", "confidence": 1.0}}
            self.pbrobot.perform_pick_and_place()
            return self._prepare_result(utterance, daresponse["rasa_result"]["intent"], "showed the simulation", None, None)
        
        '''
        if utterance.lower() == "show me":
            code_list = self.csimulator.get_current_world_code()
            logging.debug(f"Got the current world code: {code_list}")

            if self.pbsimulation:
                daresponse = {"rasa_result": { "intent": "pbsimulation", "confidence": 1.0}}
                self.pbrobot.perform_pick_and_place(code_list)
            elif self.realroboarm:
                daresponse = {"rasa_result": { "intent": "roboreal", "confidence": 1.0}}
                self.aground.perform_pick_and_place(code_list)
            else:
                daresponse = {"rasa_result": { "intent": "vsimulation", "confidence": 1.0}}
                #TODO: Here the 2.5 Grid should be shown

            return self._prepare_result(utterance, daresponse["rasa_result"]["intent"], "showed the simulation", None, None)

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
                return self._prepare_result(
                    daresponse["utterance"],
                    daresponse["intent"],
                    self.rgen.handleerror(),
                    None,
                    daresponse,
                )

        genresponse = self.rgen.generate(utterance, daresponse["intent"]["name"])
        logging.info(f"Genresponse: {genresponse}")
        if genresponse["output"] == "Sorry, I don't understand. Can you please repeat?":
            return self._prepare_result(
                daresponse["utterance"],
                daresponse["intent"],
                "Sorry, I don't understand. Can you please repeat?",
                None,
                daresponse,
            )

        intent_handlers = {
            "TRANSLATE": self._handle_translate,
            "UNDO": self._handle_undo,
            "GREET": self._handle_others,
            "ACKNOWLEDGEMENT": self._handle_others,
            "GOODBYE": self._handle_others,
            "SAVE-SKILL": self._handle_save_skill,
            "REPEAT-SKILL": self._handle_repeat_skill,
            "GROUND": self._handle_ground,
        }

        handler = intent_handlers.get(daresponse["intent"]["name"])
        if handler:
            return handler(daresponse)

        return self._prepare_result(
            daresponse["utterance"],
            daresponse["intent"],
            "No handler found for the intent.",
            None,
            daresponse,
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

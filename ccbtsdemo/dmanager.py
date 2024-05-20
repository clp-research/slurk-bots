import logging
import json

from .dadetector import DADetector
from .dtranslator import DialogueTranslator
from .csimulator import CodeSimulator
from .rgenerator import ResponseGenerator

class DialogueManager:
    def __init__(self, gridsize):
        #self.config = self.readfile("config.json")
        self.gridsize = gridsize#self.config["gridsize"]
        self.dad = DADetector()
        self.dtranslator = DialogueTranslator()
        self.csimulator = CodeSimulator(self.gridsize["width"], self.gridsize["height"])
        self.rgen = ResponseGenerator()

    def readfile(self, filename):
        with open(filename, "r") as file:
            return json.load(file)
        
    def reset(self):
        self.csimulator.reset()


    def run(self, utterance):
        daresponse = self.dad.run(utterance)
        logging.debug(f"DA Response: {daresponse}")
        if daresponse["dialogue_act"] == "TRANSLATE":
            retry = 0
            simulerror = None
            while retry < 3:
                if retry:
                    logging.debug(f"Retrying with error: {simulerror}")
                dtresponse = self.dtranslator.run(daresponse["utterance"], simulerror)
                if dtresponse:
                    dtresponse = dtresponse.strip().split("\n")
                    try:
                        save_filename = self.csimulator.run(dtresponse)
                        return save_filename
                    except Exception as error:
                        #TODO: Handle exceptions - reprompt the model with the errors
                        logging.debug(f"Error: {error}, {type(error)}, {str(error)}")
                        simulerror = str(type(error)) + str(error)

                        retry += 1
            if retry == 3:
                rgenop = self.rgen.handleerror(simulerror)
                #print(rgenop)
                logging.debug(f"Response from RGen: {rgenop}")
                return rgenop

            

        elif daresponse["dialogue_act"] == "UNDO":
            return self.csimulator.undo()

        elif daresponse["dialogue_act"] in ["GREET", "ACKNOWLEDGEMENT", "GOODBYE"]:
            response = self.rgen.generate(daresponse["utterance"])
            logging.debug(response["response"])
            return response["response"]


        elif daresponse["dialogue_act"] == "SAVE_SKILL":
            return self.csimulator.save("skill.py")
        
    def process(self):
        while True:
            utterance = input("You: ")
            if utterance.lower() == "exit":
                break
            self.run(utterance)

        


if __name__ == "__main__":
    dm = DialogueManager()
    dm.process()